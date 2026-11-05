"""Draw every frame of a video and encode it with ffmpeg."""

from __future__ import annotations

import importlib
import json
import math
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from pathlib import Path

import cairo

from .characters import Character, Pose, make_character
from .config import Project
from .drawing import (
    EXTRABOLD,
    HEIGHT,
    PALETTE,
    PANEL,
    PANEL_RADIUS,
    PI,
    WHITE,
    WIDTH,
    AlphaGroup,
    Transform,
    circle,
    clamp,
    ease_in_out,
    ellipse,
    fill,
    hex_color,
    polygon,
    pop,
    progress,
    rounded_rect,
    seeded_random,
    stroke,
    text,
    wrap_text,
)
from .errors import CapsuleError
from .media import Media
from .speakers import Speaker
from .subtitles import build_subtitles, draw_subtitles, write_srt
from .timeline import Line, Timeline

FPS = 25
SOLO_PANEL_SHIFT = 220  # the panel moves away from a single presenter (px)
SCENE_FADE = 0.5  # cross-fade between two illustrations (s)

Scene = Callable[[cairo.Context, float, Timeline], None]
SceneList = list[tuple[float, Scene]]


# ------------------------------------------------------------------ static layers
def make_background(panel_shift: float) -> cairo.ImageSurface:
    """Wall with soft blobs and a dot grid, and the empty white panel."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    ctx = cairo.Context(surface)
    ctx.rectangle(0, 0, WIDTH, HEIGHT)
    fill(ctx, PALETTE["bg"])
    for x, y, r, color in (
        (210, 190, 300, PALETTE["teal"]),
        (1730, 240, 320, PALETTE["coral"]),
        (960, 1000, 520, PALETTE["ink"]),
    ):
        circle(ctx, x, y, r)
        fill(ctx, color, 0.06)
    px = PANEL.x + panel_shift
    for gx in range(40, WIDTH, 48):
        for gy in range(40, 860, 48):
            if not (px - 20 < gx < px + PANEL.w + 20 and PANEL.y - 20 < gy < PANEL.y + PANEL.h + 20):
                circle(ctx, gx, gy, 1.8)
                fill(ctx, PALETTE["ink"], 0.07)
    rounded_rect(ctx, px + 4, PANEL.y + 14, PANEL.w, PANEL.h, PANEL_RADIUS)  # shadow
    fill(ctx, PALETTE["navy"], 0.07)
    rounded_rect(ctx, px, PANEL.y, PANEL.w, PANEL.h, PANEL_RADIUS)
    fill(ctx, PALETTE["card"])
    rounded_rect(ctx, px, PANEL.y, PANEL.w, PANEL.h, PANEL_RADIUS)
    stroke(ctx, PALETTE["line"], 1, 2)
    return surface


def make_desk() -> cairo.ImageSurface:
    """Desk in the foreground, with a plant and a mug."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    ctx = cairo.Context(surface)
    for angle, length in ((-0.5, 70), (-0.2, 95), (0.15, 85), (0.45, 65), (-0.05, 110)):  # plant
        ctx.save()
        ctx.translate(80, 820)
        ctx.rotate(angle)
        ellipse(ctx, 0, -length / 2, 16, length / 2)
        fill(ctx, hex_color("#4E8F5A"))
        ctx.restore()
    polygon(ctx, [(48, 812), (112, 812), (104, 856), (56, 856)])
    fill(ctx, hex_color("#C9734F"))
    rounded_rect(ctx, 44, 806, 72, 12, 4)
    fill(ctx, hex_color("#B5623F"))
    rounded_rect(ctx, 1822, 806, 44, 50, 8)  # mug
    fill(ctx, PALETTE["coral"])
    ctx.new_sub_path()
    ctx.arc(1868, 830, 13, -PI / 2, PI / 2)
    stroke(ctx, PALETTE["coral"], 1, 6)
    for i in range(2):  # steam
        x = 1836 + i * 14
        ctx.move_to(x, 798)
        ctx.curve_to(x - 6, 785, x + 6, 780, x, 768)
        stroke(ctx, PALETTE["grey"], 0.5, 3)
    rounded_rect(ctx, -20, 846, WIDTH + 40, 36, 10)  # desk top
    fill(ctx, PALETTE["navy2"])
    ctx.rectangle(0, 872, WIDTH, HEIGHT - 872)
    fill(ctx, PALETTE["navy"])
    ctx.rectangle(0, 872, WIDTH, 4)
    fill(ctx, WHITE, 0.06)
    return surface


# ------------------------------------------------------------------ illustrations
def title_scenes(title: str) -> Callable[[Timeline], SceneList]:
    """Scene list used without an illustration module: optional title card, then a blank panel."""

    def title_card(ctx: cairo.Context, t: float, timeline: Timeline) -> None:
        if not title:
            return
        lines = wrap_text(ctx, title, 52, EXTRABOLD, PANEL.w - 100)
        for j, line in enumerate(lines):
            y = PANEL.center_y + (j - (len(lines) - 1) / 2) * 70
            with Transform(ctx, PANEL.center_x, y, pop(t, 0.4 + 0.2 * j)):
                text(ctx, line, 0, 0, 52, PALETTE["navy"], EXTRABOLD)

    def blank(ctx: cairo.Context, t: float, timeline: Timeline) -> None:
        pass

    return lambda timeline: [
        (0.0, title_card),
        (timeline.start(1) - 0.3, blank),
        (timeline.end_start, title_card),
    ]


def load_scenes(project: Project, timeline: Timeline) -> SceneList:
    if not project.illustrations:
        return title_scenes(project.title)(timeline)
    module = importlib.import_module(f"{__package__}.scenes.{project.illustrations}")
    try:
        return module.scene_list(timeline)
    except (CapsuleError, IndexError) as error:
        raise CapsuleError(
            f"Les illustrations « {project.illustrations} » ne correspondent pas à ce texte ({error}). "
            f"Mettre « illustrations = aucune » dans le fichier de projet, ou adapter "
            f"capsule/scenes/{project.illustrations}.py."
        ) from None


# ------------------------------------------------------------------ renderer
class Renderer:
    """Everything needed to draw the frames of one project."""

    def __init__(self, project: Project, timing_path: Path | None = None, envelope_path: Path | None = None):
        self.project = project
        self.timeline = Timeline(project, timing_path)
        self.scenes = load_scenes(project, self.timeline)
        if project.solo:
            left = project.presenter_on_left
            self.panel_shift = SOLO_PANEL_SHIFT if left else -SOLO_PANEL_SHIFT
            self.characters = [make_character(project.presenter, 400 if left else 1520, -1 if left else 1)]
        else:

            self.panel_shift = 0
            self.characters = [
                make_character(Speaker.PERSON_2, 330, -1),
                make_character(Speaker.PERSON_1, 1590, 1),
            ]
        self.envelopes = json.loads(envelope_path.read_text()) if envelope_path else None
        self.background, self.desk = make_background(self.panel_shift), make_desk()
        self.subtitles = build_subtitles(self.timeline)
        self.media = [Media(spec, self.timeline, FPS) for spec in project.media]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self) -> None:
        for item in self.media:
            item.close()

    # -------------------------------------------------------------- animation
    def _envelope(self, character: Character, t: float) -> float:
        values = self.envelopes.get(character.speaker.value, ())
        i = int((t - self.timeline.audio_offset) * self.envelopes["fps"])
        return values[i] if 0 <= i < len(values) else 0.0

    @staticmethod
    def _estimated_mouth(t: float, line: Line) -> float:
        """Mouth opening without a recording: random syllables, closed around punctuation."""
        lt, d = t - line.start, line.duration
        envelope = clamp(lt / 0.06) * clamp((d - lt) / 0.1)
        syllables_per_second = 5.8
        k = int(lt * syllables_per_second)
        phase = lt * syllables_per_second - k
        amount = 0.3 + 0.7 * seeded_random(line.index * 1000 + k)
        position = int(lt / d * len(line.text))
        if any(ch in ".,!?;:…" for ch in line.text[max(0, position - 1) : position + 2]):
            amount *= 0.15
        return envelope * amount * math.sin(PI * phase)

    def pose(self, character: Character, t: float) -> Pose:
        timeline = self.timeline
        activity, current, last = 0.0, None, None  # how much the character is speaking around t
        for line in timeline.lines:
            if line.speaker != character.speaker:
                continue
            a = min(progress(t, line.start - 0.25, 0.25), 1 - progress(t, line.end, 0.35))
            if a > activity:
                activity, last = a, line
            if line.start <= t <= line.end:
                current = line
        if self.envelopes is not None:
            mouth = clamp(self._envelope(character, t) * 1.15)
        else:
            mouth = self._estimated_mouth(t, current) if current else 0.0
        phase = character.phase
        in_dialogue = timeline.start(1) - 0.5 <= t <= timeline.end_start
        nod = character.nod(t) * (1 - activity) * (1 if in_dialogue else 0)
        dy = 3 * math.sin(2 * PI * 1.1 * t + phase) * activity + 7 * nod
        angle = (
            0.03 * math.sin(2 * PI * 0.55 * t + phase) + 0.012 * math.sin(2 * PI * 1.3 * t + 2 * phase)
        ) * activity
        angle += 0.014 * math.sin(2 * PI * 0.22 * t + phase) * (1 - activity)
        gesture = 0.0
        if last is not None and seeded_random(last.index * 77 + 5) > 0.35:
            gesture = (
                activity
                * progress(t, last.start + 0.3, 0.5)
                * (1 - progress(t, last.end - 0.6, 0.5))
                * (0.65 + 0.35 * math.sin(2 * PI * 0.4 * t + phase))
            )
        brow = 6 * activity if current is not None and current.text.rstrip().endswith("?") else 0.0
        smile = 1.0 if t > timeline.end(len(timeline.lines)) + 0.1 or t < 1.0 else 0.35
        first = timeline.start(1)
        if t < first - 0.6:
            look = 0.0
        elif t < first:
            look = progress(t, first - 0.6, 0.4)
        else:
            look = 1.0
        if t > timeline.end_start + 0.3:
            look = 1 - progress(t, timeline.end_start + 0.3, 0.4)
        return Pose(
            t=t,
            glow=activity,
            mouth=mouth,
            dy=dy,
            angle=angle,
            blink=character.blink(t),
            brow=brow,
            smile=smile,
            gesture=gesture,
            look=look,
        )

    # -------------------------------------------------------------- frame
    def _draw_scenes(self, ctx: cairo.Context, t: float) -> None:
        index = 0
        for i, (start, _) in enumerate(self.scenes):
            if t >= start:
                index = i
        start, scene = self.scenes[index]
        k = ease_in_out(progress(t, start, SCENE_FADE))
        if k < 1 and index > 0:
            with AlphaGroup(ctx, 1 - k):
                self.scenes[index - 1][1](ctx, t, self.timeline)
            with AlphaGroup(ctx, k):
                scene(ctx, t, self.timeline)
        else:
            scene(ctx, t, self.timeline)

    def _in_panel(self, ctx: cairo.Context, draw: Callable[[], None]) -> None:
        """Run draw in panel coordinates, clipped to the panel."""
        ctx.save()
        ctx.translate(self.panel_shift, 0)
        rounded_rect(ctx, *PANEL, PANEL_RADIUS)
        ctx.clip()
        draw()
        ctx.restore()

    def draw_frame(self, surface: cairo.ImageSurface, t: float) -> None:
        ctx = cairo.Context(surface)
        ctx.set_source_surface(self.background, 0, 0)
        ctx.paint()
        poses = [self.pose(c, t) for c in self.characters]
        for layer in ("draw_back", "draw_body", "draw_head"):
            for character, pose in zip(self.characters, poses, strict=True):
                getattr(character, layer)(ctx, pose)
        ctx.set_source_surface(self.desk, 0, 0)
        ctx.paint()
        for character, pose in zip(self.characters, poses, strict=True):
            character.draw_arms(ctx, pose)
        self._in_panel(ctx, lambda: self._draw_scenes(ctx, t))
        if self.media:
            self._in_panel(ctx, lambda: [item.draw(ctx, t) for item in self.media])
        if self.project.subtitles:
            draw_subtitles(ctx, self.subtitles, t)
        fade = max(1 - progress(t, 0, 0.6), progress(t, self.timeline.duration - 1.0, 1.0))
        if fade > 0.001:
            ctx.rectangle(0, 0, WIDTH, HEIGHT)
            fill(ctx, (0, 0, 0), fade)
        surface.flush()

    # -------------------------------------------------------------- outputs
    def write_srt(self, path: Path) -> None:
        write_srt(self.subtitles, path)

    def write_stills(self, times: Iterable[float], directory: Path) -> list[Path]:
        directory.mkdir(parents=True, exist_ok=True)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
        paths = []
        for t in times:
            self.draw_frame(surface, t)
            paths.append(directory / f"{self.project.name}_{t:07.2f}.png")
            surface.write_to_png(str(paths[-1]))
        return paths

    def encode(self, out: Path, audio: Path | None = None, t0: float = 0.0, t1: float | None = None) -> None:
        """Encode the frames between t0 and t1 (default: whole video) to an H.264 mp4, with the voice."""
        t1 = self.timeline.duration if t1 is None else min(t1, self.timeline.duration)
        first, last = int(round(t0 * FPS)), int(round(t1 * FPS))
        command = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgra",
            "-s",
            f"{WIDTH}x{HEIGHT}",
            "-r",
            str(FPS),
            "-i",
            "-",
        ]
        if audio:
            shift = self.timeline.audio_offset - t0  # where the recording starts in this segment
            chain = (
                f"adelay=delays={int(round(shift * 1000))}:all=1"
                if shift >= 0
                else f"atrim=start={-shift:.3f},asetpts=PTS-STARTPTS"
            )
            if self.project.normalize_audio:
                chain = "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000," + chain
            command += [
                "-i",
                str(audio),
                "-filter_complex",
                f"[1:a]{chain},apad[a]",
                "-map",
                "0:v",
                "-map",
                "[a]",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "48000",
                "-shortest",
            ]
        command += [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out),
        ]
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
        started = time.time()
        for n in range(first, last):
            self.draw_frame(surface, n / FPS)
            encoder.stdin.write(surface.get_data())
            if (n - first) % 250 == 0:
                print(
                    f"image {n - first}/{last - first}  {time.time() - started:.0f} s",
                    file=sys.stderr,
                    flush=True,
                )
        encoder.stdin.close()
        encoder.wait()
        if encoder.returncode != 0:
            raise CapsuleError("ffmpeg a échoué pendant l’encodage")
        print(f"rendu terminé en {time.time() - started:.0f} s", file=sys.stderr)
