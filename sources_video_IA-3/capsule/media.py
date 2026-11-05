"""Images and video clips shown in the white panel, as declared in the [media ...] sections of a project."""

from __future__ import annotations

import subprocess
from pathlib import Path

import cairo
import numpy as np

from .config import MediaSpec
from .drawing import PALETTE, PANEL, PANEL_RADIUS, SEMIBOLD, Rect, fill, progress, rounded_rect, text
from .errors import CapsuleError
from .timeline import Timeline

FADE = 0.4  # fade in / out duration (s)
PADDING = 28  # margin inside the panel
GUTTER = 8  # half the space between two half-panel zones
CAPTION_HEIGHT = 54
DEFAULT_DURATION = 5.0  # when only an absolute start is given
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".gif"}


def zone_box(zone: str) -> Rect:
    """Area of a zone, in panel coordinates (before the solo shift)."""
    x, y = PANEL.x + PADDING, PANEL.y + PADDING
    w, h = PANEL.w - 2 * PADDING, PANEL.h - 2 * PADDING
    return {
        "panneau": Rect(x, y, w, h),
        "haut": Rect(x, y, w, h / 2 - GUTTER),
        "bas": Rect(x, y + h / 2 + GUTTER, w, h / 2 - GUTTER),
        "gauche": Rect(x, y, w / 2 - GUTTER, h),
        "droite": Rect(x + w / 2 + GUTTER, y, w / 2 - GUTTER, h),
    }[zone]


def _fit_filter(w: int, h: int) -> str:
    """ffmpeg filter: scale into w x h without distortion, centred on a transparent background."""
    return (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,format=bgra,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black@0"
    )


def _surface(buffer: bytearray, w: int, h: int) -> cairo.ImageSurface:
    return cairo.ImageSurface.create_for_data(buffer, cairo.FORMAT_ARGB32, w, h, w * 4)


class Picture:
    """A still image, decoded once."""

    def __init__(self, path: Path, w: int, h: int):
        command = [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            _fit_filter(w, h),
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgra",
            "-",
        ]
        result = subprocess.run(command, capture_output=True, check=False)
        if result.returncode != 0 or len(result.stdout) < w * h * 4:
            raise CapsuleError(
                f"Impossible de lire l’image {path} :\n{result.stderr.decode(errors='replace')}"
            )
        pixels = np.frombuffer(result.stdout[: w * h * 4], np.uint8).reshape(h, w, 4).astype(np.uint16)
        pixels[..., :3] = pixels[..., :3] * pixels[..., 3:] // 255  # cairo expects premultiplied alpha
        self.buffer = bytearray(pixels.astype(np.uint8).tobytes())
        self.surface = _surface(self.buffer, w, h)

    def frame_at(self, t: float) -> cairo.ImageSurface:
        return self.surface

    def close(self) -> None:
        pass


class Clip:
    """A video clip streamed from ffmpeg; it restarts with a seek when frames are requested out of order."""

    MAX_SKIP = 50  # frames we read through rather than seek

    def __init__(self, path: Path, w: int, h: int, fps: int, loop: bool):
        self.path, self.w, self.h, self.fps, self.loop = path, w, h, fps, loop
        self.process: subprocess.Popen | None = None
        self.next_frame = 0
        self.length: int | None = None  # number of frames, known once the end is reached
        self.buffer = bytearray(w * h * 4)
        self.surface = _surface(self.buffer, w, h)

    def _start(self, frame: int) -> None:
        self.close()
        command = [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{frame / self.fps:.3f}",
            "-i",
            str(self.path),
            "-an",
            "-vf",
            f"{_fit_filter(self.w, self.h)},fps={self.fps}",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgra",
            "-",
        ]
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.next_frame = frame

    def frame_at(self, t: float) -> cairo.ImageSurface:
        """Frame at t seconds from the start of the clip (looped, or frozen on the last frame)."""
        frame = max(0, int(round(t * self.fps)))
        if self.length is not None:
            frame = frame % self.length if self.loop else min(frame, self.length - 1)
        if self.process is None or not (self.next_frame - 1 <= frame <= self.next_frame + self.MAX_SKIP):
            self._start(frame)
        if frame == self.next_frame - 1:
            return self.surface  # same frame as last time
        size = self.w * self.h * 4
        while self.next_frame <= frame:
            data = self.process.stdout.read(size)
            if len(data) < size:  # end of the clip
                if self.length is None:
                    self.length = max(1, self.next_frame)
                    if self.loop:
                        return self.frame_at(t)
                return self.surface
            self.next_frame += 1
            if self.next_frame > frame:
                self.buffer[:] = data
                self.surface.mark_dirty()
        return self.surface

    def close(self) -> None:
        if self.process:
            self.process.kill()
            self.process.wait()
            self.process = None


class Media:
    """One media item placed on the timeline."""

    def __init__(self, spec: MediaSpec, timeline: Timeline, fps: int):
        self.spec = spec
        self.start, self.end = self._time_span(spec, timeline)
        box = zone_box(spec.zone)
        if spec.caption:
            box = box._replace(h=box.h - CAPTION_HEIGHT)
        self.box = box
        w, h = int(box.w), int(box.h)
        if spec.file.suffix.lower() in VIDEO_EXTENSIONS:
            self.source = Clip(spec.file, w, h, fps, spec.loop)
        else:
            self.source = Picture(spec.file, w, h)

    @staticmethod
    def _time_span(spec: MediaSpec, timeline: Timeline) -> tuple[float, float]:
        if spec.paragraph is None:
            return spec.start, spec.start + (spec.duration or DEFAULT_DURATION)
        i = spec.paragraph
        if i > len(timeline.lines):
            raise CapsuleError(
                f"[{spec.section}] paragraphe = {i}, mais le texte n’a que {len(timeline.lines)} paragraphes"
            )
        try:
            start = timeline.cue(i, spec.from_words) if spec.from_words else timeline.start(i)
        except CapsuleError as error:
            raise CapsuleError(f"[{spec.section}] {error}") from None
        end = start + spec.duration if spec.duration else timeline.end(i)
        return start, end

    def alpha(self, t: float) -> float:
        return min(progress(t, self.start - FADE / 2, FADE), 1 - progress(t, self.end - FADE / 2, FADE))

    def draw(self, ctx: cairo.Context, t: float) -> None:
        """Draw in panel coordinates (the caller applies the solo shift and the panel clip)."""
        alpha = self.alpha(t)
        if alpha <= 0.001:
            return
        if self.spec.hide_illustration:
            rounded_rect(ctx, *PANEL, PANEL_RADIUS)
            fill(ctx, PALETTE["card"], alpha)
        x, y, w, h = self.box
        ctx.save()
        rounded_rect(ctx, x, y, w, h, 18)
        ctx.clip()
        ctx.set_source_surface(self.source.frame_at(t - self.start), x, y)
        ctx.paint_with_alpha(alpha)
        ctx.restore()
        if self.spec.caption:
            caption_y = y + h + CAPTION_HEIGHT / 2 + 4
            text(
                ctx,
                self.spec.caption,
                x + w / 2,
                caption_y,
                24,
                PALETTE["navy"],
                SEMIBOLD,
                alpha=alpha,
                max_width=w,
            )

    def close(self) -> None:
        self.source.close()
