"""Subtitles: each line of the text is cut into chunks of at most two screen lines."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import cairo

from .drawing import MEDIUM, WHITE, WIDTH, hex_color, progress, text, wrap_text
from .speakers import Speaker
from .timeline import Timeline

FONT_SIZE = 40
MAX_WIDTH = 1340
MAX_LINES = 2
LINE_HEIGHT = 56
CENTER_Y = 978
DEFAULT_COLOR = hex_color("#FFE1A0")
COLORS = {Speaker.PERSON_2: WHITE}  # the two voices of a dialogue get different colours


@dataclass
class Subtitle:
    speaker: Speaker
    text: str
    lines: list[str]
    start: float
    end: float


def _wrap(ctx: cairo.Context, s: str) -> list[str]:
    return wrap_text(ctx, s, FONT_SIZE, MEDIUM, MAX_WIDTH)


def _fits(ctx: cairo.Context, s: str) -> bool:
    return len(_wrap(ctx, s)) <= MAX_LINES


def split_into_chunks(ctx: cairo.Context, content: str) -> list[str]:
    """Cut a paragraph at punctuation (or between words if needed) into chunks that fit on two lines."""
    parts = re.split(r"(?<=[.!?…:;,])\s+", content)
    chunks, current = [], ""
    for part in parts:
        candidate = (current + " " + part).strip()
        ends_sentence = current and current[-1] in ".!?…" and len(current) > 22
        if _fits(ctx, candidate) and not ends_sentence:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if _fits(ctx, part):
            current = part
        else:
            current = ""
            for word in part.split():
                candidate = (current + " " + word).strip()
                if _fits(ctx, candidate):
                    current = candidate
                else:
                    chunks.append(current)
                    current = word
    if current:
        chunks.append(current)
    return chunks


def build_subtitles(timeline: Timeline) -> list[Subtitle]:
    """Subtitles of every line; each chunk lasts in proportion to its length."""
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10))
    subtitles = []
    for line in timeline.lines:
        chunks = split_into_chunks(ctx, line.text)
        total = sum(len(c) for c in chunks)
        t = line.start
        for chunk in chunks:
            duration = line.duration * len(chunk) / total
            subtitles.append(Subtitle(line.speaker, chunk, _wrap(ctx, chunk), t, t + duration))
            t += duration
    return subtitles


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_srt(subtitles: list[Subtitle], path: Path) -> None:
    with open(path, "w", encoding="utf8") as f:
        for i, sub in enumerate(subtitles, 1):
            end = sub.end + 0.05
            if i < len(subtitles):
                end = min(end, subtitles[i].start - 0.02)
            f.write(f"{i}\n{srt_time(sub.start)} --> {srt_time(end)}\n" + "\n".join(sub.lines) + "\n\n")


def draw_subtitles(ctx: cairo.Context, subtitles: list[Subtitle], t: float) -> None:
    for sub in subtitles:
        if sub.start - 0.05 <= t <= sub.end + 0.12:
            alpha = min(progress(t, sub.start - 0.05, 0.1), 1 - progress(t, sub.end + 0.02, 0.1))
            color = COLORS.get(sub.speaker, DEFAULT_COLOR)
            n = len(sub.lines)
            for j, screen_line in enumerate(sub.lines):
                y = CENTER_Y + (j - (n - 1) / 2) * LINE_HEIGHT
                text(ctx, screen_line, WIDTH / 2, y, FONT_SIZE, color, MEDIUM, alpha=alpha)
            return
