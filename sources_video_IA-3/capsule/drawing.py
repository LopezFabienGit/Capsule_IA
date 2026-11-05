"""Drawing toolkit shared by the renderer, the characters and the illustrations.

Colours are (r, g, b) tuples in 0..1. Every drawing helper takes a cairo context first.
"""

from __future__ import annotations

import math
import random
from typing import NamedTuple

import cairo

WIDTH, HEIGHT = 1920, 1080
PI = math.pi


class Rect(NamedTuple):
    x: float
    y: float
    w: float
    h: float

    @property
    def center_x(self) -> float:
        return self.x + self.w / 2

    @property
    def center_y(self) -> float:
        return self.y + self.h / 2


PANEL = Rect(560, 72, 800, 740)  # white illustration panel (before the solo-mode shift)
PANEL_RADIUS = 28

Color = tuple[float, float, float]


def hex_color(code: str) -> Color:
    code = code.lstrip("#")
    return tuple(int(code[i : i + 2], 16) / 255 for i in (0, 2, 4))


PALETTE = {
    "bg": hex_color("#F4EFE6"),
    "navy": hex_color("#1E2A44"),
    "navy2": hex_color("#2E3E63"),
    "ink": hex_color("#33476E"),
    "teal": hex_color("#1C8C86"),
    "coral": hex_color("#E8664A"),
    "card": hex_color("#FFFDF8"),
    "line": hex_color("#E5DED1"),
    "grey": hex_color("#9AA3B5"),
    "lgrey": hex_color("#D5DAE3"),
    "white": (1, 1, 1),
    "gold": hex_color("#F2B134"),
    "red": hex_color("#D9475C"),
    "orange": hex_color("#F29A38"),
    "green": hex_color("#4FA86B"),
    "plum": hex_color("#7A4FA0"),
    "mustard": hex_color("#E2A72E"),
}
WHITE = PALETTE["white"]


# ---------------------------------------------------------------- easing and interpolation
def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def progress(t: float, t0: float, duration: float) -> float:
    """0 before t0, 1 after t0 + duration, linear in between."""
    if duration > 0:
        return clamp((t - t0) / duration)
    return 1.0 if t >= t0 else 0.0


def ease_in_out(x: float) -> float:
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x: float) -> float:
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back_out(x: float) -> float:
    """Ease-out that overshoots slightly before settling (a 'pop')."""
    x = clamp(x)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def appear(t: float, t0: float, duration: float = 0.45) -> float:
    """Smooth 0 -> 1 fade starting at t0."""
    return ease_out(progress(t, t0, duration))


def pop(t: float, t0: float, duration: float = 0.55) -> float:
    """0 -> 1 scale with a small overshoot starting at t0."""
    return ease_back_out(progress(t, t0, duration))


def lerp(a: float, b: float, k: float) -> float:
    return a + (b - a) * k


def mix_colors(c1: Color, c2: Color, k: float) -> Color:
    return tuple(lerp(a, b, k) for a, b in zip(c1, c2, strict=True))


def darker(color: Color, k: float = 0.75) -> Color:
    return tuple(x * k for x in color)


def lighter(color: Color, k: float = 0.5) -> Color:
    return mix_colors(color, WHITE, k)


def seeded_random(seed: int) -> float:
    """Deterministic pseudo-random number in [0, 1) for a given seed."""
    return random.Random(seed).random()


# ---------------------------------------------------------------- primitives
def set_color(ctx: cairo.Context, color: Color, alpha: float = 1.0) -> None:
    ctx.set_source_rgba(color[0], color[1], color[2], alpha)


def rounded_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float) -> None:
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -PI / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, PI / 2)
    ctx.arc(x + r, y + h - r, r, PI / 2, PI)
    ctx.arc(x + r, y + r, r, PI, 1.5 * PI)
    ctx.close_path()


def fill(ctx: cairo.Context, color: Color, alpha: float = 1.0) -> None:
    set_color(ctx, color, alpha)
    ctx.fill()


def stroke(
    ctx: cairo.Context, color: Color, alpha: float = 1.0, width: float = 4, cap=cairo.LINE_CAP_ROUND
) -> None:
    set_color(ctx, color, alpha)
    ctx.set_line_width(width)
    ctx.set_line_cap(cap)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()


def circle(ctx: cairo.Context, x: float, y: float, r: float) -> None:
    ctx.new_sub_path()
    ctx.arc(x, y, r, 0, 2 * PI)


def ellipse(ctx: cairo.Context, x: float, y: float, rx: float, ry: float) -> None:
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(rx, ry)
    ctx.new_sub_path()
    ctx.arc(0, 0, 1, 0, 2 * PI)
    ctx.restore()


def polygon(ctx: cairo.Context, points: list[tuple[float, float]]) -> None:
    ctx.move_to(*points[0])
    for p in points[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def arrow(ctx, x1, y1, x2, y2, color: Color, alpha: float = 1.0, width: float = 6, head: float = 16) -> None:
    ang = math.atan2(y2 - y1, x2 - x1)
    ctx.move_to(x1, y1)
    ctx.line_to(x2 - math.cos(ang) * head * 0.6, y2 - math.sin(ang) * head * 0.6)
    stroke(ctx, color, alpha, width)
    polygon(
        ctx,
        [
            (x2, y2),
            (x2 - head * math.cos(ang - 0.45), y2 - head * math.sin(ang - 0.45)),
            (x2 - head * math.cos(ang + 0.45), y2 - head * math.sin(ang + 0.45)),
        ],
    )
    fill(ctx, color, alpha)


# ---------------------------------------------------------------- text
REGULAR, MEDIUM, SEMIBOLD, BOLD, EXTRABOLD = "regular", "medium", "semibold", "bold", "extrabold"
FONT_FACES = {
    REGULAR: "Poppins",
    MEDIUM: "Poppins Medium",
    SEMIBOLD: "Poppins SemiBold",
    BOLD: "Poppins",
    EXTRABOLD: "Poppins ExtraBold",
}


def set_font(ctx: cairo.Context, weight: str, size: float) -> None:
    cairo_weight = cairo.FONT_WEIGHT_BOLD if weight == BOLD else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(FONT_FACES[weight], cairo.FONT_SLANT_NORMAL, cairo_weight)
    ctx.set_font_size(size)


def text_width(ctx: cairo.Context, s: str, size: float, weight: str = SEMIBOLD) -> float:
    set_font(ctx, weight, size)
    return ctx.text_extents(s).x_advance


def text(
    ctx: cairo.Context,
    s: str,
    x: float,
    y: float,
    size: float,
    color: Color,
    weight: str = SEMIBOLD,
    align: str = "center",
    alpha: float = 1.0,
    max_width: float | None = None,
) -> float:
    """Draw one line of text vertically centred on y; returns its width.

    align is 'left', 'center' or 'right'; with max_width the size shrinks until the text fits.
    """
    if max_width:
        while size > 10 and text_width(ctx, s, size, weight) > max_width:
            size -= 1
    set_font(ctx, weight, size)
    advance = ctx.text_extents(s).x_advance
    x0 = {"center": x - advance / 2, "right": x - advance, "left": x}[align]
    ctx.move_to(x0, y + size * 0.36)
    set_color(ctx, color, alpha)
    ctx.show_text(s)
    return advance


def pill(
    ctx: cairo.Context,
    s: str,
    x: float,
    y: float,
    size: float,
    bg: Color,
    fg: Color,
    weight: str = SEMIBOLD,
    alpha: float = 1.0,
    pad_x: float | None = None,
    height: float | None = None,
    bg_alpha: float = 1.0,
) -> float:
    """Text in a rounded capsule centred on (x, y); returns the capsule width."""
    tw = text_width(ctx, s, size, weight)
    pad_x = pad_x if pad_x is not None else size * 0.8
    height = height or size * 2.0
    rounded_rect(ctx, x - tw / 2 - pad_x, y - height / 2, tw + 2 * pad_x, height, height / 2)
    fill(ctx, bg, alpha * bg_alpha)
    text(ctx, s, x, y, size, fg, weight, alpha=alpha)
    return tw + 2 * pad_x


def wrap_text(ctx: cairo.Context, s: str, size: float, weight: str, max_width: float) -> list[str]:
    """Greedy word wrap: the lines of s that fit in max_width."""
    lines, current = [], ""
    for word in s.split():
        candidate = (current + " " + word).strip()
        if text_width(ctx, candidate, size, weight) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------- context helpers
class AlphaGroup:
    """Draw into an offscreen group, then paint it with an overall alpha (only when needed)."""

    def __init__(self, ctx: cairo.Context, alpha: float):
        self.ctx, self.alpha = ctx, alpha

    def __enter__(self):
        if self.alpha < 0.999:
            self.ctx.push_group()
        return self

    def __exit__(self, *exc):
        if self.alpha < 0.999:
            self.ctx.pop_group_to_source()
            self.ctx.paint_with_alpha(max(0.0, self.alpha))


class Transform:
    """Translate to (x, y), then rotate and scale around that point."""

    def __init__(self, ctx: cairo.Context, x: float, y: float, scale: float = 1.0, rotation: float = 0.0):
        self.ctx, self.x, self.y, self.scale, self.rotation = ctx, x, y, scale, rotation

    def __enter__(self):
        self.ctx.save()
        self.ctx.translate(self.x, self.y)
        if self.rotation:
            self.ctx.rotate(self.rotation)
        scale = max(self.scale, 1e-3)
        if scale != 1.0:
            self.ctx.scale(scale, scale)

    def __exit__(self, *exc):
        self.ctx.restore()
