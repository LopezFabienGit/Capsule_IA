"""Unit tests; run with:  python3 -m unittest discover tests"""

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

import cairo
import numpy as np

from capsule import alignment
from capsule.config import load_project
from capsule.drawing import HEIGHT, WIDTH, progress, wrap_text
from capsule.errors import CapsuleError
from capsule.media import zone_box
from capsule.renderer import Renderer
from capsule.speakers import Speaker
from capsule.subtitles import build_subtitles, srt_time
from capsule.timeline import Timeline


class ProjectTestCase(unittest.TestCase):
    """Creates a temporary folder with a text and a project file."""

    TEXT = (
        "Person_2 : Bonjour, ceci est un test.\n"
        "\n"
        "Person_1 : Et voici la réponse, assez longue pour être coupée ?\n"
    )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "texte.txt").write_text(self.TEXT, encoding="utf8")

    def tearDown(self):
        self.tmp.cleanup()

    def project(self, video_options: str = "", extra: str = ""):
        content = f"[video]\ndialogue = texte.txt\n{textwrap.dedent(video_options)}\n{textwrap.dedent(extra)}"
        path = self.dir / "projet.ini"
        path.write_text(content, encoding="utf8")
        return load_project(path)


class ConfigTest(ProjectTestCase):
    def test_defaults(self):
        project = self.project()
        self.assertEqual(project.name, "projet")
        self.assertFalse(project.solo)
        self.assertIsNone(project.audio)
        self.assertIsNone(project.illustrations)
        self.assertTrue(project.subtitles)
        self.assertEqual(project.video_path.name, "projet.mp4")

    def test_solo_goat(self):
        project = self.project("mode = solo\npresentateur = Chevre\nposition = droite")
        self.assertTrue(project.solo)
        self.assertEqual(project.presenter, Speaker.GOAT)
        self.assertFalse(project.presenter_on_left)

    def test_invalid_values_are_reported(self):
        for options in ("mode = trio", "sous_titres = peut-être", "presentateur = Bob", "audio = absent.mp3"):
            with self.subTest(options=options), self.assertRaises(CapsuleError):
                self.project(options)

    def test_media_section(self):
        (self.dir / "image.png").write_bytes(b"")
        project = self.project("", "[media a]\nfichier = image.png\nparagraphe = 2\nduree = 3,5\nzone = bas")
        (media,) = project.media
        self.assertEqual((media.paragraph, media.duration, media.zone), (2, 3.5, "bas"))

    def test_media_needs_a_time(self):
        (self.dir / "image.png").write_bytes(b"")
        with self.assertRaises(CapsuleError):
            self.project("", "[media a]\nfichier = image.png")


class TimelineTest(ProjectTestCase):
    def test_blank_lines_are_ignored_and_speakers_read(self):
        timeline = Timeline(self.project())
        self.assertEqual([line.speaker for line in timeline.lines], [Speaker.PERSON_2, Speaker.PERSON_1])
        self.assertLess(timeline.end(1), timeline.start(2))

    def test_duo_requires_labels(self):
        (self.dir / "texte.txt").write_text("Sans étiquette\n", encoding="utf8")
        with self.assertRaises(CapsuleError):
            Timeline(self.project())

    def test_solo_gives_every_line_to_the_presenter(self):
        (self.dir / "texte.txt").write_text("Une ligne\nUne autre\n", encoding="utf8")
        timeline = Timeline(self.project("mode = solo\npresentateur = Person_1"))
        self.assertEqual({line.speaker for line in timeline.lines}, {Speaker.PERSON_1})

    def test_cue(self):
        timeline = Timeline(self.project())
        self.assertAlmostEqual(timeline.cue(1, "Bonjour"), timeline.start(1))
        self.assertGreater(timeline.cue(1, "test"), timeline.start(1))
        with self.assertRaises(CapsuleError):
            timeline.cue(1, "absent")

    def test_saved_timing_must_match_the_text(self):
        timing = self.dir / "timing.json"
        timing.write_text(json.dumps({"audio_offset": 1.0, "lines": [[3.2, 5.0]]}))
        with self.assertRaises(CapsuleError):
            Timeline(self.project(), timing)


class SubtitleTest(ProjectTestCase):
    def test_srt_time(self):
        self.assertEqual(srt_time(3725.5), "01:02:05,500")

    def test_chunks_cover_the_text_in_order(self):
        timeline = Timeline(self.project())
        subtitles = build_subtitles(timeline)
        for line in timeline.lines:
            chunks = [s for s in subtitles if s.start >= line.start - 1e-9 and s.end <= line.end + 1e-9]
            self.assertEqual(" ".join(s.text for s in chunks), line.text)
            self.assertTrue(all(len(s.lines) <= 2 for s in chunks))


class DrawingTest(unittest.TestCase):
    def test_progress(self):
        self.assertEqual(progress(0, 1, 2), 0)
        self.assertEqual(progress(2, 1, 2), 0.5)
        self.assertEqual(progress(5, 1, 2), 1)

    def test_wrap_text(self):
        ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10))
        lines = wrap_text(ctx, "un deux trois quatre cinq six", 40, "medium", 200)
        self.assertGreater(len(lines), 1)
        self.assertEqual(" ".join(lines), "un deux trois quatre cinq six")

    def test_half_zones_fit_in_the_panel(self):
        full = zone_box("panneau")
        for zone in ("haut", "bas", "gauche", "droite"):
            box = zone_box(zone)
            self.assertGreaterEqual(box.x, full.x)
            self.assertLessEqual(box.x + box.w, full.x + full.w + 1e-9)
            self.assertLessEqual(box.y + box.h, full.y + full.h + 1e-9)


class AlignmentTest(ProjectTestCase):
    def test_finds_paragraphs_in_a_synthetic_recording(self):
        """Tones separated by silences, one per paragraph, must be found back in order."""
        project = self.project("mode = solo")
        estimate = Timeline(project)
        rate = alignment.SAMPLE_RATE
        silence = np.zeros(rate // 2, np.float32)
        parts, spans, t = [silence], [], 0.5
        for line in estimate.lines:
            n = int(line.duration * rate)
            parts += [0.3 * np.sin(2 * np.pi * 180 * np.arange(n) / rate).astype(np.float32), silence]
            spans.append((t, t + line.duration))
            t += line.duration + 0.5
        samples = np.concatenate(parts)
        original = alignment.load_audio
        alignment.load_audio = lambda path: samples
        try:
            result = alignment.align(project, Path("synthetique.wav"))
        finally:
            alignment.load_audio = original
        for (start, end), (expected_start, expected_end) in zip(result.lines, spans, strict=True):
            self.assertAlmostEqual(start - result.audio_offset, expected_start, delta=0.05)
            self.assertAlmostEqual(end - result.audio_offset, expected_end, delta=0.05)
        self.assertIn(Speaker.PERSON_2, result.envelopes)


class RendererTest(ProjectTestCase):
    def test_draws_a_frame_in_each_mode(self):
        for options in (
            "mode = duo",
            "mode = solo\npresentateur = Chevre",
            "titre = Un titre\nsous_titres = non",
        ):
            with self.subTest(options=options), Renderer(self.project(options)) as renderer:
                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
                renderer.draw_frame(surface, renderer.timeline.start(1) + 0.5)
                pixels = np.frombuffer(surface.get_data(), np.uint8)
                self.assertGreater(pixels.std(), 10)  # something was drawn


if __name__ == "__main__":
    unittest.main()
