"""Small flat icons drawn in a 100 x 100 box centred on the origin.

Use icon(ctx, name, x, y, size, color) ; the available names are the keys of ICONS.
"""

import math

import cairo

from .drawing import (
    EXTRABOLD,
    PALETTE,
    PI,
    WHITE,
    circle,
    darker,
    ellipse,
    fill,
    lighter,
    polygon,
    rounded_rect,
    stroke,
    text,
)

ICONS = {}


def _icon(name):
    """Register the decorated function as the icon called name."""

    def register(draw):
        ICONS[name] = draw
        return draw

    return register


@_icon("tv")
def _tv(ctx, color, alpha):
    rounded_rect(ctx, -46, -36, 92, 62, 9)
    fill(ctx, color, alpha)
    rounded_rect(ctx, -40, -30, 80, 50, 5)
    fill(ctx, WHITE, alpha * 0.92)
    polygon(ctx, [(-7, -15), (12, -5), (-7, 5)])
    fill(ctx, color, alpha)
    rounded_rect(ctx, -5, 25, 10, 11, 2)
    fill(ctx, color, alpha)
    rounded_rect(ctx, -22, 34, 44, 7, 3.5)
    fill(ctx, color, alpha)


@_icon("phone")
def _phone(ctx, color, alpha):
    rounded_rect(ctx, -27, -48, 54, 96, 11)
    fill(ctx, color, alpha)
    rounded_rect(ctx, -22, -40, 44, 74, 6)
    fill(ctx, WHITE, alpha * 0.92)
    polygon(ctx, [(-6, -12), (10, -3), (-6, 6)])
    fill(ctx, color, alpha)
    circle(ctx, 0, 41, 3.5)
    fill(ctx, WHITE, alpha)


@_icon("book")
def _book(ctx, color, alpha):
    rounded_rect(ctx, -30, -42, 62, 84, 6)
    fill(ctx, color, alpha)
    ctx.rectangle(-30, -42, 13, 84)
    fill(ctx, darker(color), alpha)
    ctx.rectangle(25, -37, 5, 74)
    fill(ctx, WHITE, alpha * 0.85)
    rounded_rect(ctx, -8, -26, 28, 6, 3)
    fill(ctx, WHITE, alpha)
    rounded_rect(ctx, -8, -15, 18, 5, 2.5)
    fill(ctx, WHITE, alpha * 0.8)


@_icon("pin")
def _pin(ctx, color, alpha):
    ctx.move_to(0, 46)
    ctx.curve_to(-14, 22, -32, 6, -32, -14)
    ctx.arc(0, -14, 32, PI, 2 * PI)
    ctx.curve_to(32, 6, 14, 22, 0, 46)
    ctx.close_path()
    fill(ctx, color, alpha)
    circle(ctx, 0, -14, 12)
    fill(ctx, WHITE, alpha)


@_icon("chat")
def _chat(ctx, color, alpha):
    rounded_rect(ctx, -46, -38, 92, 62, 16)
    fill(ctx, color, alpha)
    polygon(ctx, [(-28, 20), (-36, 42), (-8, 20)])
    fill(ctx, color, alpha)
    for x in (-20, 0, 20):
        circle(ctx, x, -7, 6)
        fill(ctx, WHITE, alpha)


@_icon("bolt")
def _bolt(ctx, color, alpha):
    polygon(ctx, [(10, -48), (-26, 6), (-3, 6), (-12, 48), (26, -8), (3, -8), (14, -48)])
    fill(ctx, color, alpha)


@_icon("gear")
def _gear(ctx, color, alpha):
    n = 8
    pts = []
    for i in range(n):
        g = i * 2 * PI / n
        for da, r in ((-0.26, 32), (-0.15, 46), (0.15, 46), (0.26, 32)):
            pts.append((r * math.cos(g + da), r * math.sin(g + da)))
    polygon(ctx, pts)
    fill(ctx, color, alpha)
    circle(ctx, 0, 0, 34)
    fill(ctx, color, alpha)
    circle(ctx, 0, 0, 13)
    fill(ctx, WHITE, alpha)


@_icon("house")
def _house(ctx, color, alpha):
    polygon(ctx, [(-46, -2), (0, -42), (46, -2)])
    fill(ctx, color, alpha)
    ctx.rectangle(-34, -6, 68, 48)
    fill(ctx, color, alpha)
    rounded_rect(ctx, -9, 14, 18, 28, 3)
    fill(ctx, WHITE, alpha)
    circle(ctx, 30, -30, 17)
    fill(ctx, PALETTE["gold"], alpha)
    text(ctx, "€", 30, -31, 22, WHITE, EXTRABOLD, alpha=alpha)


@_icon("detect")
def _detect(ctx, color, alpha):
    rounded_rect(ctx, -46, -40, 92, 80, 9)
    fill(ctx, color, alpha * 0.14)
    rounded_rect(ctx, -46, -40, 92, 80, 9)
    stroke(ctx, color, alpha, 3)
    polygon(ctx, [(-16, -6), (-12, -24), (-2, -10)])
    fill(ctx, PALETTE["navy"], alpha)
    polygon(ctx, [(16, -6), (12, -24), (2, -10)])
    fill(ctx, PALETTE["navy"], alpha)
    circle(ctx, 0, 6, 17)
    fill(ctx, PALETTE["navy"], alpha)
    circle(ctx, -6, 3, 3)
    fill(ctx, WHITE, alpha)
    circle(ctx, 6, 3, 3)
    fill(ctx, WHITE, alpha)
    ctx.set_dash([7, 5])
    ctx.rectangle(-28, -30, 56, 58)
    stroke(ctx, color, alpha, 3, cairo.LINE_CAP_BUTT)
    ctx.set_dash([])
    rounded_rect(ctx, -28, -40, 34, 12, 3)
    fill(ctx, color, alpha)


@_icon("card")
def _card(ctx, color, alpha):
    rounded_rect(ctx, -44, -28, 88, 58, 9)
    fill(ctx, color, alpha)
    ctx.rectangle(-44, -14, 88, 10)
    fill(ctx, darker(color, 0.6), alpha)
    rounded_rect(ctx, -34, 6, 16, 12, 3)
    fill(ctx, PALETTE["gold"], alpha)
    polygon(ctx, [(30, -50), (52, -12), (8, -12)])
    fill(ctx, PALETTE["orange"], alpha)
    text(ctx, "!", 30, -24, 24, WHITE, EXTRABOLD, alpha=alpha)


@_icon("film")
def _film(ctx, color, alpha):
    rounded_rect(ctx, -40, -14, 80, 54, 6)
    fill(ctx, color, alpha)
    ctx.save()
    ctx.translate(-40, -16)
    ctx.rotate(-0.3)
    ctx.rectangle(0, -16, 80, 16)
    fill(ctx, color, alpha)
    for x in (8, 32, 56):
        polygon(ctx, [(x, -16), (x + 12, -16), (x + 4, 0), (x - 8, 0)])
        fill(ctx, WHITE, alpha * 0.9)
    ctx.restore()
    rounded_rect(ctx, -28, 2, 40, 6, 3)
    fill(ctx, WHITE, alpha * 0.8)


@_icon("shield")
def _shield(ctx, color, alpha):
    ctx.move_to(0, -46)
    ctx.line_to(38, -32)
    ctx.curve_to(38, 10, 22, 32, 0, 46)
    ctx.curve_to(-22, 32, -38, 10, -38, -32)
    ctx.close_path()
    fill(ctx, color, alpha)
    ctx.move_to(-15, 0)
    ctx.line_to(-4, 12)
    ctx.line_to(17, -12)
    stroke(ctx, WHITE, alpha, 8)


@_icon("car")
def _car(ctx, color, alpha):
    polygon(ctx, [(-28, -4), (-16, -28), (18, -28), (32, -4)])
    fill(ctx, color, alpha)
    rounded_rect(ctx, -46, -8, 92, 30, 10)
    fill(ctx, color, alpha)
    polygon(ctx, [(-20, -8), (-12, -22), (-2, -22), (-2, -8)])
    fill(ctx, WHITE, alpha * 0.85)
    polygon(ctx, [(4, -8), (4, -22), (14, -22), (24, -8)])
    fill(ctx, WHITE, alpha * 0.85)
    for x in (-26, 26):
        circle(ctx, x, 22, 11)
        fill(ctx, PALETTE["navy"], alpha)
        circle(ctx, x, 22, 4)
        fill(ctx, WHITE, alpha)


@_icon("doc")
def _doc(ctx, color, alpha):
    polygon(ctx, [(-32, -44), (16, -44), (34, -26), (34, 44), (-32, 44)])
    fill(ctx, color, alpha)
    polygon(ctx, [(16, -44), (16, -26), (34, -26)])
    fill(ctx, WHITE, alpha * 0.5)
    for i, w in enumerate((40, 48, 44, 30, 40)):
        rounded_rect(ctx, -22, -16 + i * 11, w, 5, 2.5)
        fill(ctx, WHITE, alpha * 0.9)


@_icon("image")
def _image(ctx, color, alpha):
    rounded_rect(ctx, -46, -38, 92, 76, 9)
    fill(ctx, color, alpha)
    rounded_rect(ctx, -40, -32, 80, 64, 5)
    fill(ctx, WHITE, alpha)
    circle(ctx, 18, -14, 8)
    fill(ctx, color, alpha)
    polygon(ctx, [(-40, 32), (-12, -6), (4, 12), (16, 0), (40, 32)])
    fill(ctx, color, alpha)


@_icon("speaker")
def _speaker(ctx, color, alpha):
    ctx.rectangle(-38, -12, 16, 24)
    fill(ctx, color, alpha)
    polygon(ctx, [(-22, -12), (2, -32), (2, 32), (-22, 12)])
    fill(ctx, color, alpha)
    ctx.new_sub_path()
    ctx.arc(4, 0, 18, -0.8, 0.8)
    stroke(ctx, color, alpha, 6)
    ctx.new_sub_path()
    ctx.arc(4, 0, 32, -0.8, 0.8)
    stroke(ctx, color, alpha, 6)


@_icon("music")
def _music(ctx, color, alpha):
    ellipse(ctx, -20, 28, 14, 10)
    fill(ctx, color, alpha)
    ellipse(ctx, 24, 20, 14, 10)
    fill(ctx, color, alpha)
    ctx.rectangle(-10, -32, 7, 60)
    fill(ctx, color, alpha)
    ctx.rectangle(34, -40, 7, 60)
    fill(ctx, color, alpha)
    polygon(ctx, [(-10, -32), (41, -42), (41, -28), (-10, -18)])
    fill(ctx, color, alpha)


@_icon("video")
def _video(ctx, color, alpha):
    rounded_rect(ctx, -46, -28, 66, 56, 10)
    fill(ctx, color, alpha)
    polygon(ctx, [(22, -10), (46, -26), (46, 26), (22, 10)])
    fill(ctx, color, alpha)
    polygon(ctx, [(-22, -12), (2, 0), (-22, 12)])
    fill(ctx, WHITE, alpha)


@_icon("code")
def _code(ctx, color, alpha):
    ctx.move_to(-14, -24)
    ctx.line_to(-40, 0)
    ctx.line_to(-14, 24)
    stroke(ctx, color, alpha, 9)
    ctx.move_to(14, -24)
    ctx.line_to(40, 0)
    ctx.line_to(14, 24)
    stroke(ctx, color, alpha, 9)
    ctx.move_to(8, -32)
    ctx.line_to(-8, 32)
    stroke(ctx, color, alpha, 8)


@_icon("clock")
def _clock(ctx, color, alpha, ang=0.0):
    circle(ctx, 0, 0, 42)
    fill(ctx, WHITE, alpha)
    circle(ctx, 0, 0, 42)
    stroke(ctx, color, alpha, 7)
    for i in range(12):
        g = i * PI / 6
        ctx.move_to(34 * math.cos(g), 34 * math.sin(g))
        ctx.line_to(30 * math.cos(g), 30 * math.sin(g))
        stroke(ctx, color, alpha * 0.6, 3)
    ctx.move_to(0, 0)
    ctx.line_to(18 * math.sin(ang / 12), -18 * math.cos(ang / 12))
    stroke(ctx, color, alpha, 6)
    ctx.move_to(0, 0)
    ctx.line_to(28 * math.sin(ang), -28 * math.cos(ang))
    stroke(ctx, color, alpha, 4)
    circle(ctx, 0, 0, 4)
    fill(ctx, color, alpha)


@_icon("person")
def _person(ctx, color, alpha):
    circle(ctx, 0, -18, 18)
    fill(ctx, color, alpha)
    ctx.new_sub_path()
    ctx.arc(0, 44, 34, PI, 2 * PI)
    ctx.close_path()
    fill(ctx, color, alpha)


@_icon("users")
def _users(ctx, color, alpha):
    for x, y, s in ((-24, 6, 0.75), (24, 6, 0.75)):
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(s, s)
        _person(ctx, lighter(color, 0.35), alpha)
        ctx.restore()
    ctx.save()
    ctx.translate(0, 0)
    ctx.scale(0.9, 0.9)
    _person(ctx, color, alpha)
    ctx.restore()


@_icon("heart")
def _heart(ctx, color, alpha):
    ctx.move_to(0, 40)
    ctx.curve_to(-50, 6, -40, -40, 0, -18)
    ctx.curve_to(40, -40, 50, 6, 0, 40)
    ctx.close_path()
    fill(ctx, color, alpha)


@_icon("share")
def _share(ctx, color, alpha):
    ctx.move_to(-34, 32)
    ctx.curve_to(-34, -6, -8, -16, 12, -16)
    ctx.line_to(12, -36)
    ctx.line_to(44, -6)
    ctx.line_to(12, 24)
    ctx.line_to(12, 4)
    ctx.curve_to(-6, 4, -22, 12, -34, 32)
    ctx.close_path()
    fill(ctx, color, alpha)


@_icon("skip")
def _skip(ctx, color, alpha):
    polygon(ctx, [(-42, -28), (-6, 0), (-42, 28)])
    fill(ctx, color, alpha)
    polygon(ctx, [(-8, -28), (28, 0), (-8, 28)])
    fill(ctx, color, alpha)
    ctx.rectangle(30, -28, 10, 56)
    fill(ctx, color, alpha)


@_icon("fullbar")
def _fullbar(ctx, color, alpha):
    rounded_rect(ctx, -46, 14, 92, 14, 7)
    fill(ctx, color, alpha)
    circle(ctx, 46, 21, 11)
    fill(ctx, color, alpha)
    polygon(ctx, [(-14, -34), (14, -16), (-14, 2)])
    fill(ctx, color, alpha)


@_icon("db")
def _db(ctx, color, alpha):
    ctx.rectangle(-36, -30, 72, 60)
    fill(ctx, color, alpha)
    ellipse(ctx, 0, 30, 36, 12)
    fill(ctx, color, alpha)
    ellipse(ctx, 0, -30, 36, 12)
    fill(ctx, lighter(color, 0.3), alpha)
    for y in (-8, 12):
        ctx.save()
        ctx.translate(0, y)
        ctx.scale(36, 12)
        ctx.arc(0, 0, 1, 0.15, PI - 0.15)
        ctx.restore()
        stroke(ctx, WHITE, alpha * 0.8, 3)


@_icon("net")
def _net(ctx, color, alpha):
    cols = [(-38, (-26, 0, 26)), (0, (-36, -12, 12, 36)), (38, (-14, 14))]
    for (x1, ys1), (x2, ys2) in zip(cols, cols[1:], strict=False):
        for y1 in ys1:
            for y2 in ys2:
                ctx.move_to(x1, y1)
                ctx.line_to(x2, y2)
        stroke(ctx, color, alpha * 0.4, 2.5)
    for x, ys in cols:
        for y in ys:
            circle(ctx, x, y, 7.5)
            fill(ctx, color, alpha)


@_icon("sparkle")
def _sparkle(ctx, color, alpha):
    ctx.move_to(0, -48)
    ctx.curve_to(5, -8, 8, -5, 48, 0)
    ctx.curve_to(8, 5, 5, 8, 0, 48)
    ctx.curve_to(-5, 8, -8, 5, -48, 0)
    ctx.curve_to(-8, -5, -5, -8, 0, -48)
    ctx.close_path()
    fill(ctx, color, alpha)


@_icon("pen")
def _pen(ctx, color, alpha):
    ctx.save()
    ctx.rotate(PI / 4)
    rounded_rect(ctx, -9, -46, 18, 70, 4)
    fill(ctx, color, alpha)
    polygon(ctx, [(-9, 24), (9, 24), (0, 44)])
    fill(ctx, PALETTE["navy"], alpha)
    ctx.rectangle(-9, -32, 18, 6)
    fill(ctx, WHITE, alpha * 0.7)
    ctx.restore()


@_icon("forecast")
def _forecast(ctx, color, alpha):
    ctx.move_to(-44, -44)
    ctx.line_to(-44, 40)
    ctx.line_to(46, 40)
    stroke(ctx, PALETTE["navy"], alpha * 0.6, 4)
    ctx.move_to(-36, 22)
    ctx.line_to(-22, 6)
    ctx.line_to(-8, 14)
    ctx.line_to(6, -6)
    stroke(ctx, color, alpha, 6)
    ctx.set_dash([6, 7])
    ctx.move_to(6, -6)
    ctx.line_to(22, -14)
    ctx.line_to(38, -30)
    stroke(ctx, color, alpha, 6, cairo.LINE_CAP_BUTT)
    ctx.set_dash([])
    circle(ctx, 38, -30, 7)
    fill(ctx, color, alpha)


@_icon("speedo")
def _speedo(ctx, color, alpha):
    ctx.new_sub_path()
    ctx.arc(0, 12, 40, PI, 2 * PI)
    stroke(ctx, color, alpha, 10, cairo.LINE_CAP_BUTT)
    ctx.move_to(0, 12)
    ctx.line_to(26, -14)
    stroke(ctx, PALETTE["navy"], alpha, 6)
    circle(ctx, 0, 12, 7)
    fill(ctx, PALETTE["navy"], alpha)


@_icon("alert")
def _alert(ctx, color, alpha):
    polygon(ctx, [(0, -44), (46, 38), (-46, 38)])
    fill(ctx, color, alpha)
    text(ctx, "!", 0, 8, 46, WHITE, EXTRABOLD, alpha=alpha)


@_icon("star")
def _star(ctx, color, alpha):
    pts = []
    for i in range(10):
        r = 46 if i % 2 == 0 else 20
        g = -PI / 2 + i * PI / 5
        pts.append((r * math.cos(g), r * math.sin(g)))
    polygon(ctx, pts)
    fill(ctx, color, alpha)


@_icon("box")
def _box(ctx, color, alpha):
    ctx.rectangle(-38, -14, 76, 56)
    fill(ctx, color, alpha)
    polygon(ctx, [(-38, -14), (-26, -40), (26, -40), (38, -14)])
    fill(ctx, lighter(color, 0.25), alpha)
    ctx.rectangle(-8, -40, 16, 26)
    fill(ctx, WHITE, alpha * 0.6)
    ctx.rectangle(-8, -14, 16, 56)
    fill(ctx, WHITE, alpha * 0.35)


@_icon("sun")
def _sun(ctx, color, alpha):
    circle(ctx, 0, 0, 20)
    fill(ctx, color, alpha)
    for i in range(8):
        g = i * PI / 4
        ctx.move_to(30 * math.cos(g), 30 * math.sin(g))
        ctx.line_to(42 * math.cos(g), 42 * math.sin(g))
    stroke(ctx, color, alpha, 6)


@_icon("city")
def _city(ctx, color, alpha):
    for x, w, h in ((-46, 20, 50), (-24, 24, 80), (2, 18, 60), (22, 24, 90)):
        ctx.rectangle(x, 44 - h, w, h)
        fill(ctx, color, alpha)
        for wy in range(int(44 - h + 8), 40, 14):
            ctx.rectangle(x + 5, wy, w - 10, 5)
            fill(ctx, WHITE, alpha * 0.5)


@_icon("calendar")
def _calendar(ctx, color, alpha):
    rounded_rect(ctx, -40, -34, 80, 76, 9)
    fill(ctx, WHITE, alpha)
    rounded_rect(ctx, -40, -34, 80, 76, 9)
    stroke(ctx, color, alpha, 5)
    ctx.rectangle(-40, -34, 80, 20)
    fill(ctx, color, alpha)
    for r_ in range(3):
        for q in range(4):
            circle(ctx, -24 + q * 16, -2 + r_ * 14, 3.5)
            fill(ctx, color, alpha * 0.7)


def icon(ctx, name, x, y, size, color, alpha=1.0, **options):
    """Draw icon name centred on (x, y), size pixels wide."""
    if alpha <= 0.001 or size <= 0.5:
        return
    ctx.save()
    ctx.new_path()
    ctx.translate(x, y)
    ctx.scale(size / 100, size / 100)
    ICONS[name](ctx, color, alpha, **options)
    ctx.restore()
