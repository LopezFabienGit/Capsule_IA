"""Animated presenters: two people and a humanised goat.

A character is drawn in four layers (back, body, head, arms) so that the desk can be painted between
the head and the arms. Its animation at a given instant is described by a Pose.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import cairo

from .drawing import (
    PALETTE,
    PI,
    WHITE,
    Color,
    circle,
    darker,
    ellipse,
    fill,
    hex_color,
    lerp,
    polygon,
    rounded_rect,
    stroke,
)
from .speakers import Speaker

HEAD_Y = 452
MOUTH_DARK, TONGUE = hex_color("#6B2735"), hex_color("#E07A7A")
CHEEK = hex_color("#E7837B")
ANIMATION_HORIZON = 900  # seconds of pre-computed blinks and nods


@dataclass(frozen=True)
class CharacterStyle:
    skin: str  # fur colour for the goat
    hair: str  # dark fur colour for the goat
    top: str  # sweater
    seed: int  # random seed of the blinks and nods
    long_hair: bool = False
    beard: bool = False
    glasses: bool = False
    v_neck: bool = False
    brow_width: float = 5


STYLES = {
    Speaker.PERSON_1: CharacterStyle(
        "#A86E4A", "#2B211C", "#E2A72E", 23, beard=True, glasses=True, v_neck=True, brow_width=6
    ),
    Speaker.PERSON_2: CharacterStyle("#E9B48F", "#3B2620", "#7A4FA0", 11, long_hair=True),
    Speaker.GOAT: CharacterStyle("#C9A47E", "#7A5A3E", "#3E6FA8", 37),
}


@dataclass
class Pose:
    """Animation state of a character at one instant (all amounts are 0..1 unless stated)."""

    t: float  # time (s)
    glow: float  # halo while speaking
    mouth: float  # mouth opening
    dy: float  # vertical head offset (px)
    angle: float  # head tilt (rad)
    blink: float  # eyelid closure
    brow: float  # eyebrow raise (px)
    smile: float
    gesture: float  # raised outer hand
    look: float  # how much the eyes turn towards the panel
    eye_scale: float = 1.0


class Character:
    glow_radius = 250

    def __init__(self, speaker: Speaker, center_x: float, side: int, style: CharacterStyle):
        """side is -1 for the left of the screen, +1 for the right."""
        self.speaker, self.cx, self.side = speaker, center_x, side
        self.style = style
        self.skin, self.hair, self.top = hex_color(style.skin), hex_color(style.hair), hex_color(style.top)
        self.look_dx = 5 if side < 0 else -5  # pupils look towards the centre of the screen
        rnd = random.Random(style.seed)
        self.blinks, t = [], rnd.uniform(0.5, 2)
        while t < ANIMATION_HORIZON:
            self.blinks.append(t)
            t += rnd.uniform(2.2, 5.2)
            if rnd.random() < 0.15:  # occasional double blink
                self.blinks.append(t)
                t += 0.3
        self.nods, t = [], rnd.uniform(1, 3)
        while t < ANIMATION_HORIZON:
            self.nods.append(t)
            t += rnd.uniform(2.4, 4.6)
        self.phase = rnd.uniform(0, 6)

    # -------------------------------------------------------------- timed gestures
    def blink(self, t: float) -> float:
        for b in self.blinks:
            if b - 0.01 <= t <= b + 0.14:
                return math.sin(PI * (t - b) / 0.14)
            if b > t:
                break
        return 0.0

    def nod(self, t: float) -> float:
        for n in self.nods:
            if n <= t <= n + 0.5:
                return math.sin(PI * (t - n) / 0.5)
            if n > t:
                break
        return 0.0

    # -------------------------------------------------------------- layers
    def _draw_glow(self, ctx: cairo.Context, pose: Pose) -> None:
        if pose.glow <= 0.01:
            return
        r, cx, cy = self.glow_radius, self.cx, HEAD_Y + 20
        gradient = cairo.RadialGradient(cx, cy, 40, cx, cy, r)
        gradient.add_color_stop_rgba(0, *self.top, 0.20 * pose.glow)
        gradient.add_color_stop_rgba(1, *self.top, 0)
        ctx.set_source(gradient)
        circle(ctx, cx, cy, r)
        ctx.fill()

    def _head_transform(self, ctx: cairo.Context, pose: Pose):
        character = self

        class HeadTransform:
            def __enter__(self):
                ctx.save()
                ctx.translate(character.cx, HEAD_Y + 100)
                ctx.rotate(pose.angle)
                ctx.translate(-character.cx, -HEAD_Y - 100 + pose.dy)

            def __exit__(self, *exc):
                ctx.restore()

        return HeadTransform()

    def draw_back(self, ctx: cairo.Context, pose: Pose) -> None:
        """Halo and everything behind the head (long hair)."""
        self._draw_glow(ctx, pose)
        with self._head_transform(ctx, pose):
            if self.style.long_hair:
                circle(ctx, self.cx, HEAD_Y - 10, 116)
                fill(ctx, self.hair)
                rounded_rect(ctx, self.cx - 114, HEAD_Y - 10, 228, 170, 50)
                fill(ctx, self.hair)

    def draw_body(self, ctx: cairo.Context, pose: Pose) -> None:
        cx = self.cx
        breath = 1 + 0.006 * math.sin(pose.t * 2 * PI * 0.25 + self.phase)
        ctx.save()
        ctx.translate(cx, 880)
        ctx.scale(1, breath)
        ctx.translate(-cx, -880)
        # neck
        rounded_rect(ctx, cx - 33, HEAD_Y + 60, 66, 110, 22)
        fill(ctx, darker(self.skin, 0.9))
        # torso
        ctx.move_to(cx - 198, 900)
        ctx.line_to(cx - 192, 712)
        ctx.curve_to(cx - 190, 646, cx - 150, 614, cx - 72, 604)
        ctx.line_to(cx + 72, 604)
        ctx.curve_to(cx + 150, 614, cx + 190, 646, cx + 192, 712)
        ctx.line_to(cx + 198, 900)
        ctx.close_path()
        fill(ctx, self.top)
        self._draw_collar(ctx, cx)
        ctx.restore()

    def _draw_collar(self, ctx: cairo.Context, cx: float) -> None:
        if self.style.v_neck:
            polygon(ctx, [(cx - 46, 604), (cx, 664), (cx + 46, 604)])
            fill(ctx, WHITE)
            polygon(ctx, [(cx - 30, 604), (cx, 646), (cx + 30, 604)])
            fill(ctx, darker(self.skin, 0.9))
            ctx.move_to(cx - 52, 604)
            ctx.line_to(cx, 672)
            ctx.line_to(cx + 52, 604)
            stroke(ctx, darker(self.top, 0.82), 1, 9)
        else:  # crew neck
            for draw in (fill, stroke):
                ctx.save()
                ctx.translate(cx, 604)
                ctx.scale(44, 26)
                ctx.arc(0, 0, 1, 0, PI)
                ctx.restore()
                if draw is fill:
                    fill(ctx, darker(self.skin, 0.9))
                else:
                    stroke(ctx, darker(self.top, 0.8), 1, 6)

    def draw_head(self, ctx: cairo.Context, pose: Pose) -> None:
        cx, y = self.cx, HEAD_Y
        skin, hair = self.skin, self.hair
        look_dx = self.look_dx * pose.look
        with self._head_transform(ctx, pose):
            for side in (-1, 1):  # ears
                ellipse(ctx, cx + side * 90, y + 10, 15, 21)
                fill(ctx, darker(skin, 0.93))
            ellipse(ctx, cx, y, 92, 104)  # face
            fill(ctx, skin)
            if self.style.beard:
                self._draw_beard(ctx, look_dx)
            for side in (-1, 1):  # cheeks
                ellipse(ctx, cx + side * 54 + look_dx * 0.5, y + 40, 17, 9)
                fill(ctx, CHEEK, 0.28)
            self._draw_eyes(ctx, pose, look_dx)
            for side in (-1, 1):  # brows
                bx, by = cx + side * 34 + look_dx * 0.8, y - 30 - pose.brow
                ctx.move_to(bx - 15, by + 4)
                ctx.curve_to(bx - 6, by - 4, bx + 6, by - 4, bx + 15, by + 3)
                stroke(ctx, hair, 1, self.style.brow_width)
            if self.style.glasses:
                self._draw_glasses(ctx, look_dx)
            nx = cx + look_dx * 1.3  # nose
            ctx.move_to(nx - 2, y + 18)
            ctx.curve_to(nx + 6 * (1 if look_dx >= 0 else -1), y + 30, nx + 4, y + 36, nx - 6, y + 36)
            stroke(ctx, darker(skin, 0.8), 1, 4)
            self._draw_mouth(ctx, pose, cx + look_dx * 1.6, y + 64)
            self._draw_front_hair(ctx)

    def _draw_beard(self, ctx: cairo.Context, look_dx: float) -> None:
        cx, y = self.cx, HEAD_Y
        ctx.save()
        ctx.translate(cx, y)
        ctx.scale(92, 104)
        ctx.arc(0, 0, 1, 0.05, PI - 0.05)
        ctx.restore()
        ctx.curve_to(cx - 70, y + 60, cx - 40, y + 46, cx, y + 50)
        ctx.curve_to(cx + 40, y + 46, cx + 70, y + 60, cx + 92, y + 5)
        ctx.close_path()
        fill(ctx, self.hair, 0.92)
        ctx.move_to(cx - 34 + look_dx, y + 60)  # moustache
        ctx.curve_to(cx - 20 + look_dx, y + 48, cx + 20 + look_dx, y + 48, cx + 34 + look_dx, y + 60)
        stroke(ctx, self.hair, 1, 9)

    def _draw_eyes(self, ctx: cairo.Context, pose: Pose, look_dx: float) -> None:
        opening = 1 - pose.blink
        scale = pose.eye_scale
        for side in (-1, 1):
            ex, ey = self.cx + side * 34 + look_dx, HEAD_Y + 2
            if opening > 0.15:
                ellipse(ctx, ex, ey, 9.5 * scale, 12 * scale * opening)
                fill(ctx, PALETTE["navy"])
                circle(ctx, ex + 3, ey - 4 * opening, 3)
                fill(ctx, WHITE)
            else:
                ctx.move_to(ex - 10, ey)
                ctx.curve_to(ex - 4, ey + 4, ex + 4, ey + 4, ex + 10, ey)
                stroke(ctx, PALETTE["navy"], 1, 4)

    def _draw_glasses(self, ctx: cairo.Context, look_dx: float) -> None:
        cx, y = self.cx, HEAD_Y
        for side in (-1, 1):
            rounded_rect(ctx, cx + side * 34 + look_dx - 26, y - 19, 52, 40, 13)
            stroke(ctx, PALETTE["navy"], 1, 4.5)
        ctx.move_to(cx - 8 + look_dx, y - 2)
        ctx.curve_to(cx - 3 + look_dx, y - 7, cx + 3 + look_dx, y - 7, cx + 8 + look_dx, y - 2)
        stroke(ctx, PALETTE["navy"], 1, 4)

    def _draw_mouth(self, ctx: cairo.Context, pose: Pose, mx: float, my: float) -> None:
        if pose.mouth > 0.04:
            draw_open_mouth(
                ctx, mx, my, height=5 + 26 * pose.mouth, width=30 + 6 * pose.mouth, amount=pose.mouth
            )
        elif pose.smile > 0.5:
            ctx.move_to(mx - 22, my - 4)
            ctx.curve_to(mx - 18, my + 22, mx + 18, my + 22, mx + 22, my - 4)
            ctx.close_path()
            fill(ctx, MOUTH_DARK)
            rounded_rect(ctx, mx - 15, my - 3, 30, 7, 3)
            fill(ctx, WHITE)
        else:
            curve = 8 + 3 * pose.smile
            ctx.move_to(mx - 17, my)
            ctx.curve_to(mx - 8, my + curve, mx + 8, my + curve, mx + 17, my)
            stroke(ctx, MOUTH_DARK, 1, 5)

    def _draw_front_hair(self, ctx: cairo.Context) -> None:
        cx, y = self.cx, HEAD_Y
        if self.style.long_hair:
            ctx.save()
            ctx.translate(cx, y)
            ctx.scale(102, 114)
            ctx.arc(0, 0, 1, PI * 1.02, PI * 1.98)
            ctx.restore()
            ctx.curve_to(cx + 98, y - 20, cx + 70, y - 70, cx + 18, y - 76)
            ctx.curve_to(cx - 30, y - 74, cx - 70, y - 50, cx - 94, y + 18)
            ctx.close_path()
            fill(ctx, self.hair)
        else:
            ctx.save()
            ctx.translate(cx, y)
            ctx.scale(98, 112)
            ctx.arc(0, 0, 1, PI * 1.08, PI * 1.92)
            ctx.restore()
            ctx.curve_to(cx + 72, y - 60, cx + 40, y - 74, cx + 6, y - 70)
            ctx.curve_to(cx - 34, y - 66, cx - 70, y - 56, cx - 88, y - 36)
            ctx.close_path()
            fill(ctx, self.hair)
            ctx.move_to(cx - 40, y - 100)  # quiff
            ctx.curve_to(cx - 10, y - 128, cx + 40, y - 126, cx + 62, y - 96)
            ctx.close_path()
            fill(ctx, self.hair)

    def draw_arms(self, ctx: cairo.Context, pose: Pose) -> None:
        """Arms resting on the desk; the outer hand rises while gesturing."""
        sleeve = darker(self.top, 0.88)
        for side in (-1, 1):
            elbow = (self.cx + side * 178, 822)
            rest = (self.cx + side * 66, 858)
            hand = rest
            if side == self.side and pose.gesture > 0.01:
                up = (self.cx + side * 222, 736 + 9 * math.sin(pose.t * 2 * PI * 1.4 + self.phase))
                hand = (lerp(rest[0], up[0], pose.gesture), lerp(rest[1], up[1], pose.gesture))
            ctx.move_to(*elbow)
            ctx.line_to(*hand)
            stroke(ctx, sleeve, 1, 52)
            self._draw_hand(ctx, *hand)

    def _draw_hand(self, ctx: cairo.Context, x: float, y: float) -> None:
        circle(ctx, x, y, 25)
        fill(ctx, self.skin)


def draw_open_mouth(
    ctx: cairo.Context, mx: float, my: float, height: float, width: float, amount: float
) -> None:
    ctx.move_to(mx - width / 2, my - 3)
    ctx.curve_to(mx - width / 2, my + height, mx + width / 2, my + height, mx + width / 2, my - 3)
    ctx.curve_to(mx + width / 3, my - 6, mx - width / 3, my - 6, mx - width / 2, my - 3)
    fill(ctx, MOUTH_DARK)
    if amount > 0.35:
        ellipse(ctx, mx, my + height * 0.55, width * 0.25, height * 0.18)
        fill(ctx, TONGUE)


HORN, HOOF, EAR_PINK, IRIS = (
    hex_color("#D8C3A0"),
    hex_color("#4A3B30"),
    hex_color("#E8A9A0"),
    hex_color("#E8B83A"),
)


class Goat(Character):
    """Humanised goat: horns, floppy ears, muzzle, goatee, slot pupils, hooves, shirt and tie."""

    glow_radius = 260

    def __init__(
        self, speaker: Speaker, center_x: float, side: int, style: CharacterStyle, muzzle: str = "#EFE1CC"
    ):
        super().__init__(speaker, center_x, side, style)
        self.muzzle: Color = hex_color(muzzle)

    def draw_back(self, ctx: cairo.Context, pose: Pose) -> None:
        self._draw_glow(ctx, pose)
        cx, y = self.cx, HEAD_Y
        with self._head_transform(ctx, pose):
            for side in (-1, 1):  # horns sweeping up and outwards, with ridges
                for color, width in ((HORN, 26), (darker(HORN, 0.85), 4)):
                    ctx.move_to(cx + side * 30, y - 78)
                    ctx.curve_to(cx + side * 34, y - 150, cx + side * 86, y - 182, cx + side * 112, y - 146)
                    stroke(ctx, color, 1, width)
                for k in range(3):
                    u = 0.25 + 0.2 * k
                    hx, hy = cx + side * lerp(32, 90, u), y - lerp(95, 165, u)
                    ctx.move_to(hx - 10, hy)
                    ctx.line_to(hx + 10, hy - 4)
                    stroke(ctx, darker(HORN, 0.8), 0.7, 3)

    def _draw_collar(self, ctx: cairo.Context, cx: float) -> None:
        """White shirt collar and a tie under the sweater."""
        polygon(ctx, [(cx - 58, 600), (cx, 650), (cx - 20, 672), (cx - 70, 628)])
        fill(ctx, WHITE)
        polygon(ctx, [(cx + 58, 600), (cx, 650), (cx + 20, 672), (cx + 70, 628)])
        fill(ctx, WHITE)
        rounded_rect(ctx, cx - 7, 650, 14, 60, 4)
        fill(ctx, PALETTE["coral"])

    def _draw_hand(self, ctx: cairo.Context, x: float, y: float) -> None:
        """Hoof."""
        circle(ctx, x, y, 25)
        fill(ctx, HOOF)
        ellipse(ctx, x, y - 9, 27, 19)
        fill(ctx, self.skin)
        ctx.move_to(x, y + 6)
        ctx.line_to(x, y + 24)
        stroke(ctx, self.skin, 1, 3)

    def draw_head(self, ctx: cairo.Context, pose: Pose) -> None:
        cx, y = self.cx, HEAD_Y
        fur, dark = self.skin, self.hair
        look_dx = self.look_dx * pose.look
        jaw = pose.mouth
        with self._head_transform(ctx, pose):
            for side in (-1, 1):  # floppy ears, sticking out sideways
                flap = 0.05 * math.sin(pose.t * 1.7 + self.phase + side)
                ctx.save()
                ctx.translate(cx + side * 78, y - 30)
                ctx.rotate(side * (0.35 + flap))
                ellipse(ctx, side * 52, 0, 58, 22)
                fill(ctx, fur)
                ellipse(ctx, side * 56, 2, 42, 12)
                fill(ctx, EAR_PINK)
                ctx.restore()
            ellipse(ctx, cx, y - 4, 80, 106)  # long face
            fill(ctx, fur)
            ellipse(ctx, cx + look_dx * 0.4, y - 48, 16, 42)  # forehead blaze
            fill(ctx, WHITE, 0.45)
            for dx in (-14, 0, 14):  # tuft
                ctx.move_to(cx + dx - 10, y - 100)
                ctx.curve_to(cx + dx - 4, y - 122, cx + dx + 6, y - 120, cx + dx + 10, y - 100)
                ctx.close_path()
                fill(ctx, fur)
            ellipse(ctx, cx + look_dx * 0.9, y + 62, 60, 44)  # muzzle
            fill(ctx, self.muzzle)
            # goatee under the chin, swinging a little with the jaw
            gx = cx + look_dx
            ctx.move_to(gx - 22, y + 96)
            ctx.curve_to(gx - 18, y + 136 + 8 * jaw, gx, y + 156 + 10 * jaw, gx + 4, y + 166 + 10 * jaw)
            ctx.curve_to(gx + 10, y + 146 + 8 * jaw, gx + 20, y + 126, gx + 22, y + 96)
            ctx.close_path()
            fill(ctx, dark)
            self._draw_goat_eyes(ctx, pose, look_dx)
            for side in (-1, 1):  # brows
                bx, by = cx + side * 38 + look_dx * 0.8, y - 36 - pose.brow
                ctx.move_to(bx - 16, by + 4)
                ctx.curve_to(bx - 6, by - 5, bx + 6, by - 5, bx + 16, by + 3)
                stroke(ctx, dark, 1, 7)
            nx = cx + look_dx * 1.2
            for side in (-1, 1):  # nostrils
                ellipse(ctx, nx + side * 15, y + 44, 6, 4)
                fill(ctx, darker(self.muzzle, 0.45))
            ctx.move_to(nx, y + 50)
            ctx.line_to(nx, y + 62)
            stroke(ctx, darker(self.muzzle, 0.6), 1, 3)
            mx, my = nx, y + 72
            if jaw > 0.04:
                draw_open_mouth(ctx, mx, my, height=4 + 22 * jaw, width=34 + 6 * jaw, amount=jaw)
            else:
                curve = 6 + 6 * pose.smile
                ctx.move_to(mx - 22, my - 2)
                ctx.curve_to(mx - 10, my + curve, mx + 10, my + curve, mx + 22, my - 2)
                stroke(ctx, MOUTH_DARK, 1, 5)

    def _draw_goat_eyes(self, ctx: cairo.Context, pose: Pose, look_dx: float) -> None:
        """Amber eyes with horizontal slot pupils."""
        opening = 1 - pose.blink
        scale = pose.eye_scale
        for side in (-1, 1):
            ex, ey = self.cx + side * 38 + look_dx, HEAD_Y - 10
            if opening > 0.15:
                px = ex + look_dx * 0.3
                ellipse(ctx, ex, ey, 17 * scale, 14 * scale * opening)
                fill(ctx, WHITE)
                ellipse(ctx, px, ey, 13 * scale, 11 * scale * opening)
                fill(ctx, IRIS)
                rounded_rect(ctx, px - 9, ey - 3 * opening, 18, max(1.5, 6 * opening), 3)
                fill(ctx, PALETTE["navy"])
                circle(ctx, px + 5, ey - 5 * opening, 2.5)
                fill(ctx, WHITE)
                ellipse(ctx, ex, ey, 17 * scale, 14 * scale * opening)
                stroke(ctx, darker(self.skin, 0.6), 1, 2.5)
            else:
                ctx.move_to(ex - 15, ey)
                ctx.curve_to(ex - 6, ey + 6, ex + 6, ey + 6, ex + 15, ey)
                stroke(ctx, PALETTE["navy"], 1, 4)


def make_character(speaker: Speaker, center_x: float, side: int) -> Character:
    cls = Goat if speaker == Speaker.GOAT else Character
    return cls(speaker, center_x, side, STYLES[speaker])
