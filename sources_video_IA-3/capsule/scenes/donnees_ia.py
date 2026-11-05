"""Illustrations for the text « Avec quoi nourrit-on les IA ? » (dialogue.txt, 8 paragraphs).

Each scene is a function (ctx, t, timeline) drawing the panel at time t; scene_list() says when each
one starts. Scenes are synchronised with words of the text through timeline.cue(paragraph, words),
so they must be adapted if the text changes.
Local conventions: a = opacity, p = pop-in scale, k = progress of a transition (all 0..1).
"""

import math
import random

from ..drawing import (
    EXTRABOLD,
    MEDIUM,
    PALETTE,
    PANEL,
    PI,
    SEMIBOLD,
    WHITE,
    AlphaGroup,
    Transform,
    appear,
    arrow,
    circle,
    ease_in_out,
    ease_out,
    ellipse,
    fill,
    hex_color,
    lerp,
    lighter,
    mix_colors,
    pill,
    pop,
    progress,
    rounded_rect,
    stroke,
    text,
    text_width,
)
from ..icons import icon

CENTER_X = PANEL.center_x
TEAL, CORAL, NAVY, INK = PALETTE["teal"], PALETTE["coral"], PALETTE["navy"], PALETTE["ink"]
RED, GOLD, GREY = PALETTE["red"], PALETTE["gold"], PALETTE["grey"]
EU_BLUE = hex_color("#1F4E9E")
SKINS = [hex_color(h) for h in ("#E9B48F", "#A86E4A", "#F1C9A5", "#7B4B32", "#D9A07A", "#C68863", "#5C3A28")]


def label(ctx, caption, color):
    """Small title capsule at the top of the panel."""
    pill(ctx, caption, CENTER_X, 120, 21, lighter(color, 0.86), color, SEMIBOLD, height=46)


# ====================================================================== shared pieces
def tile(
    ctx, x, y, scale, color, icon_name=None, glyph=None, caption=None, caption2=None, alpha=1.0, size=140
):
    """Rounded tile with an icon (or a short text glyph) and up to two caption lines."""
    if scale <= 0.001 or alpha <= 0.001:
        return
    half = size / 2
    with Transform(ctx, x, y, scale), AlphaGroup(ctx, alpha):
        rounded_rect(ctx, -half, -half, size, size, size * 0.18)
        fill(ctx, color, 0.1)
        if icon_name:
            icon(ctx, icon_name, 0, 0, size * 0.64, color)
        if glyph:
            text(ctx, glyph, 0, 0, size * 0.3, color, EXTRABOLD)
        if caption:
            text(ctx, caption, 0, half + 28, 21, NAVY, SEMIBOLD)
        if caption2:
            text(ctx, caption2, 0, half + 56, 21, NAVY, SEMIBOLD)


def flow(ctx, t, x1, y1, x2, y2, color, alpha, dots=5, speed=0.6, radius=6):
    """Arrow with dots travelling along it."""
    if alpha <= 0.01:
        return
    arrow(ctx, x1, y1, x2, y2, INK, alpha, 5)
    for j in range(dots):
        u = (t * speed + j / dots) % 1
        circle(ctx, lerp(x1, x2 - 16, u), lerp(y1, y2, u), radius)
        fill(ctx, color, alpha * math.sin(PI * u))


def phone(ctx, x, y, scale, t, phase, mic=0.0):
    """Smartphone whose screen shows a watching eye; mic is the scale of a microphone badge."""
    with Transform(ctx, x, y, scale):
        rounded_rect(ctx, -56, -96, 112, 192, 20)
        fill(ctx, NAVY)
        rounded_rect(ctx, -47, -80, 94, 158, 11)
        fill(ctx, lighter(TEAL, 0.75))
        # an eye on the screen: the camera is watching
        ctx.move_to(-34, -6)
        ctx.curve_to(-14, -32, 14, -32, 34, -6)
        ctx.curve_to(14, 20, -14, 20, -34, -6)
        fill(ctx, WHITE)
        circle(ctx, 4 * math.sin(t * 1.3 + phase), -6, 13)
        fill(ctx, NAVY)
        circle(ctx, 0, -88, 4.5)
        fill(ctx, INK)
        if (t * 1.6 + phase) % 1 < 0.6:
            circle(ctx, 30, -64, 6)
            fill(ctx, RED)
        text(ctx, "REC", 6, -64, 12, RED, SEMIBOLD, alpha=0.9)
        if mic > 0.001:
            with Transform(ctx, 50, 66, mic):
                circle(ctx, 0, 0, 25)
                fill(ctx, CORAL)
                rounded_rect(ctx, -6, -14, 12, 20, 6)
                fill(ctx, WHITE)
                ctx.new_sub_path()
                ctx.arc(0, 0, 11, 0.15, PI - 0.15)
                stroke(ctx, WHITE, 1, 3)
                ctx.move_to(0, 11)
                ctx.line_to(0, 16)
                stroke(ctx, WHITE, 1, 3)


def face(ctx, x, y, r, color, alpha=1.0):
    """Small smiling face of radius r."""
    circle(ctx, x, y, r)
    fill(ctx, color, alpha)
    for dx in (-0.35, 0.35):
        circle(ctx, x + dx * r, y - 0.1 * r, 0.11 * r)
        fill(ctx, NAVY, alpha)
    ctx.new_sub_path()
    ctx.arc(x, y + 0.1 * r, 0.38 * r, 0.3, PI - 0.3)
    stroke(ctx, NAVY, alpha, max(1.5, r * 0.09))


def globe(ctx, x, y, r, color, t):
    """Slowly rotating globe."""
    circle(ctx, x, y, r)
    fill(ctx, WHITE)
    circle(ctx, x, y, r)
    fill(ctx, color, 0.12)
    for f in (-0.5, 0.0, 0.5):
        w = r * math.sqrt(1 - f * f)
        ctx.move_to(x - w, y + f * r)
        ctx.line_to(x + w, y + f * r)
        stroke(ctx, color, 0.7, 3)
    for j in range(3):
        rx = abs(r * math.cos(t * 0.6 + j * PI / 3))
        if rx > 2:
            ellipse(ctx, x, y, rx, r)
            stroke(ctx, color, 0.7, 3)
    circle(ctx, x, y, r)
    stroke(ctx, color, 1, 5)


def eu_flag(ctx, x, y, scale):
    with Transform(ctx, x, y, scale):
        rounded_rect(ctx, -105, -70, 210, 140, 14)
        fill(ctx, EU_BLUE)
        for i in range(12):
            g = i * PI / 6
            icon(ctx, "star", 46 * math.cos(g), 46 * math.sin(g), 22, GOLD)


def toggle(ctx, x, y, off):
    """Switch sliding from on (teal) to off (coral) as off goes from 0 to 1."""
    color = mix_colors(TEAL, CORAL, off)
    rounded_rect(ctx, x - 60, y - 30, 120, 60, 30)
    fill(ctx, color)
    circle(ctx, x + lerp(30, -30, ease_in_out(off)), y, 23)
    fill(ctx, WHITE)


def scales(ctx, x, y, tilt, t):
    """Balance: pivot at (x, y); authors on the left pan, AI on the right pan."""
    rounded_rect(ctx, x - 70, y + 196, 140, 18, 9)
    fill(ctx, INK)
    ctx.move_to(x, y)
    ctx.line_to(x, y + 200)
    stroke(ctx, INK, 1, 9)
    ca, sa = math.cos(tilt), math.sin(tilt)
    ctx.move_to(x - 220 * ca, y - 220 * sa)
    ctx.line_to(x + 220 * ca, y + 220 * sa)
    stroke(ctx, NAVY, 1, 9)
    circle(ctx, x, y, 12)
    fill(ctx, GOLD)
    for side, icon_name, color, caption in ((-1, "users", TEAL, "Auteurs"), (1, "net", CORAL, "IA")):
        ex, ey = x + side * 220 * ca, y + side * 220 * sa
        py = ey + 100
        ctx.move_to(ex, ey)
        ctx.line_to(ex - 60, py)
        stroke(ctx, GREY, 1, 2.5)
        ctx.move_to(ex, ey)
        ctx.line_to(ex + 60, py)
        stroke(ctx, GREY, 1, 2.5)
        ctx.new_sub_path()
        ctx.arc(ex, py, 70, 0, PI)
        ctx.close_path()
        fill(ctx, color, 0.25)
        ctx.move_to(ex - 70, py)
        ctx.line_to(ex + 70, py)
        stroke(ctx, color, 1, 5)
        icon(ctx, icon_name, ex, py - 40, 72, color)
        text(ctx, caption, ex, py + 92, 24, NAVY, SEMIBOLD)


# ====================================================================== title / end
def scene_title(ctx, t, timeline):
    with Transform(ctx, CENTER_X, 270, pop(t, 0.4)):
        text(ctx, "Avec quoi nourrit-on", 0, 0, 50, NAVY, EXTRABOLD)
    with Transform(ctx, CENTER_X, 360, pop(t, 0.8)):
        text(ctx, "les IA ?", 0, 0, 80, CORAL, EXTRABOLD)
    text(ctx, "Données · droit d’auteur · opt-out", CENTER_X, 470, 28, INK, MEDIUM, alpha=appear(t, 1.4))
    a = appear(t, 1.8)
    tile(ctx, 730, 640, pop(t, 1.8), TEAL, "db", size=120)
    tile(ctx, 1190, 640, pop(t, 2.0), CORAL, "net", size=120)
    flow(ctx, t, 810, 640, 1110, 640, TEAL, a)


def scene_end(ctx, t, timeline):
    t0 = timeline.end_start
    with Transform(ctx, CENTER_X, 220, pop(t, t0 + 0.1)):
        text(ctx, "Nourrir les IA", 0, 0, 58, NAVY, EXTRABOLD)
    rows = (
        ("db", TEAL, "Des données massives,", "souvent collectées sans consentement"),
        ("doc", EU_BLUE, "Une exception légale en Europe :", "la fouille de textes et de données"),
        ("shield", CORAL, "L’opt-out, un droit d’opposition", "encore difficile à faire respecter"),
    )
    for j, (icon_name, color, line1, line2) in enumerate(rows):
        y = 360 + j * 140
        a = appear(t, t0 + 0.5 + 0.35 * j)
        tile(ctx, 680, y, pop(t, t0 + 0.5 + 0.35 * j), color, icon_name, size=100)
        text(ctx, line1, 760, y - 18, 26, NAVY, SEMIBOLD, align="left", alpha=a, max_width=560)
        text(ctx, line2, 760, y + 20, 24, color, MEDIUM, align="left", alpha=a, max_width=560)


# ====================================================================== 1 Ex Machina
FACE_ORDER = random.Random(3).sample(range(42), 42)


def scene_exmachina(ctx, t, timeline):
    label(ctx, "Au cinéma", INK)
    k_up = ease_in_out(progress(t, timeline.cue(1, "Son secret") - 0.2, 0.7))
    with Transform(
        ctx, CENTER_X, lerp(370, 250, k_up), pop(t, timeline.start(1) + 0.1) * lerp(1, 0.62, k_up)
    ):
        rounded_rect(ctx, -210, -130, 420, 260, 20)
        fill(ctx, NAVY)
        for j in range(9):
            for yy in (-116, 104):
                rounded_rect(ctx, -186 + j * 44, yy, 22, 12, 3)
                fill(ctx, WHITE, 0.55)
        text(ctx, "EX MACHINA", 0, -18, 50, WHITE, EXTRABOLD)
        text(ctx, "2014", 0, 42, 32, GOLD, SEMIBOLD)
    a1 = appear(t, timeline.cue(1, "génie") - 0.2) * (1 - k_up)
    text(ctx, "Un génie de la tech crée une IA…", CENTER_X, 590, 32, NAVY, SEMIBOLD, alpha=a1)
    text(
        ctx,
        "… étonnamment humaine",
        CENTER_X,
        645,
        34,
        CORAL,
        EXTRABOLD,
        alpha=a1 * appear(t, timeline.cue(1, "humaine") - 0.2),
    )
    if k_up <= 0.001:
        return
    mic = pop(t, timeline.cue(1, "micros") - 0.15)
    for j, x in enumerate((760, 960, 1160)):
        p = pop(t, timeline.cue(1, "caméras") - 0.2 + 0.15 * j)
        if p > 0.001:
            phone(ctx, x, 470, p * 0.85, t, j * 1.7, mic)
    t0 = timeline.cue(1, "milliards de visages") - 0.3
    for n, idx in enumerate(FACE_ORDER):
        p = pop(t, t0 + 0.06 * n, 0.4)
        if p > 0.001:
            r, c = divmod(idx, 14)
            face(ctx, 625 + c * 51.5, 662 + r * 50, 19 * p, SKINS[idx % len(SKINS)])
    for j, (x, y) in enumerate(((865, 380), (1065, 400), (665, 410))):
        p = pop(t, timeline.cue(1, "conversations") - 0.2 + 0.12 * j)
        if p > 0.001:
            icon(ctx, "chat", x, y, 52 * p, CORAL)


# ====================================================================== 2 illegal / question
def scene_illegal(ctx, t, timeline):
    kq = appear(t, timeline.cue(2, "Mais la question") - 0.2, 0.6)
    label(ctx, "Dans la réalité" if kq < 0.5 else "La vraie question", RED if kq < 0.5 else TEAL)
    if kq < 0.999:
        with AlphaGroup(ctx, 1 - kq):
            ps = progress(t, timeline.cue(2, "illégal") - 0.25, 0.35)
            if ps > 0:
                stamp_scale = lerp(1.8, 1, ease_out(ps))  # a stamp: big, then slammed down
                with Transform(ctx, CENTER_X, 350, stamp_scale, -0.1), AlphaGroup(ctx, ease_out(ps)):
                    rounded_rect(ctx, -230, -75, 460, 150, 18)
                    stroke(ctx, RED, 1, 10)
                    text(ctx, "ILLÉGAL", 0, 0, 84, RED, EXTRABOLD)
            a = appear(t, timeline.cue(2, "violation") - 0.2)
            ps = pop(t, timeline.cue(2, "violation") - 0.2)
            if ps > 0.001:  # privacy shield, crossed out
                with Transform(ctx, CENTER_X, 545, ps * 0.9):
                    ctx.move_to(0, -46)
                    ctx.line_to(38, -32)
                    ctx.curve_to(38, 10, 22, 32, 0, 46)
                    ctx.curve_to(-22, 32, -38, 10, -38, -32)
                    ctx.close_path()
                    fill(ctx, RED)
                    for d in (-1, 1):
                        ctx.move_to(-14, -14 * d)
                        ctx.line_to(14, 14 * d)
                        stroke(ctx, WHITE, 1, 8)
            text(ctx, "Violation massive de la vie privée", CENTER_X, 655, 34, NAVY, EXTRABOLD, alpha=a)
    if kq > 0.001:
        with AlphaGroup(ctx, kq):
            a = appear(t, timeline.cue(2, "nourrir") - 0.4)
            text(ctx, "Pour apprendre,", CENTER_X, 205, 34, NAVY, SEMIBOLD, alpha=a)
            text(ctx, "une IA doit être nourrie", CENTER_X, 255, 38, TEAL, EXTRABOLD, alpha=a)
            tile(ctx, 760, 410, pop(t, timeline.cue(2, "nourrir") - 0.2), TEAL, "db", caption="Données")
            tile(ctx, 1160, 410, pop(t, timeline.cue(2, "nourrir")), CORAL, "net", caption="IA")
            flow(ctx, t, 845, 410, 1075, 410, TEAL, appear(t, timeline.cue(2, "nourrir") + 0.2))
            with Transform(ctx, CENTER_X, 600, pop(t, timeline.cue(2, "avec quoi") - 0.15)):
                text(ctx, "Avec quoi ?", 0, 0, 52, TEAL, EXTRABOLD)
            with Transform(ctx, CENTER_X, 690, pop(t, timeline.cue(2, "Et a-t-on") - 0.15)):
                text(ctx, "Et a-t-on le droit ?", 0, 0, 42, CORAL, EXTRABOLD)


# ====================================================================== 3 language model
WORDS = (("canapé", 0.61), ("tapis", 0.24), ("toit", 0.09))


def scene_llm(ctx, t, timeline):
    label(ctx, "Grand modèle de langue", TEAL)
    a = appear(t, timeline.cue(3, "apprend par") - 0.3)
    text(ctx, "Il apprend par l’exemple", CENTER_X, 200, 38, NAVY, EXTRABOLD, alpha=a)
    kb = appear(t, timeline.cue(3, "prédire") - 0.4, 0.6)
    if kb < 0.999:
        with AlphaGroup(ctx, 1 - kb):
            for j in range(3):
                icon(
                    ctx,
                    "doc",
                    680 + j * 22,
                    400 - j * 16,
                    110 * pop(t, timeline.cue(3, "immense") - 0.3 + 0.1 * j),
                    mix_colors(INK, TEAL, j / 2),
                )
            text(
                ctx,
                "Une immense quantité",
                700,
                510,
                21,
                NAVY,
                SEMIBOLD,
                alpha=appear(t, timeline.cue(3, "immense") - 0.2),
            )
            text(
                ctx,
                "de textes",
                700,
                538,
                21,
                NAVY,
                SEMIBOLD,
                alpha=appear(t, timeline.cue(3, "immense") - 0.2),
            )
            tile(ctx, 1200, 390, pop(t, timeline.cue(3, "On lui montre")), CORAL, "net", caption="Modèle")
            fa = appear(t, timeline.cue(3, "immense"))
            if fa > 0.01:
                for j in range(6):
                    u = (t * 0.45 + j / 6) % 1
                    icon(ctx, "doc", lerp(790, 1110, u), 390, 34, TEAL, fa * math.sin(PI * u))
    if kb > 0.001:
        with AlphaGroup(ctx, kb):
            rounded_rect(ctx, 620, 270, 680, 320, 24)
            fill(ctx, TEAL, 0.07)
            text(ctx, "Le chat dort sur le", 900, 320, 34, NAVY, SEMIBOLD, align="right")
            rounded_rect(ctx, 915, 296, 150, 50, 10)
            stroke(ctx, TEAL, 0.5 + 0.5 * math.sin(t * 6) ** 2, 3)
            text(ctx, "?", 990, 320, 34, TEAL, EXTRABOLD)
            g = ease_out(progress(t, timeline.cue(3, "prédire") + 0.2, 1.2))
            for j, (w, p) in enumerate(WORDS):
                y = 395 + j * 62
                k = TEAL if j == 0 else GREY
                text(ctx, w, 660, y, 28, NAVY, SEMIBOLD, align="left")
                rounded_rect(ctx, 820, y - 16, 340, 32, 16)
                fill(ctx, PALETTE["lgrey"], 0.6)
                if g > 0.01:
                    rounded_rect(ctx, 820, y - 16, 340 * p * g / 0.61, 32, 16)
                    fill(ctx, k)
                text(ctx, f"{round(100 * p * g)} %", 1250, y, 24, k, SEMIBOLD, align="right", alpha=g)
    text(
        ctx,
        "À force de répétitions, il saisit :",
        CENTER_X,
        650,
        26,
        INK,
        MEDIUM,
        alpha=appear(t, timeline.cue(3, "À force") - 0.2),
    )
    x = 640
    for w, words in (
        ("la grammaire", "grammaire"),
        ("le style", "le style"),
        ("les faits", "les faits"),
        ("les raisonnements", "les raisonnements"),
    ):
        tw = text_width(ctx, w, 20, SEMIBOLD) + 32
        p = pop(t, timeline.cue(3, words) - 0.2)
        if p > 0.001:
            with Transform(ctx, x + tw / 2, 725, p):
                pill(ctx, w, 0, 0, 20, lighter(TEAL, 0.82), TEAL, SEMIBOLD, height=44)
        x += tw + 14


# ====================================================================== 4 scraping
SOURCES = (
    ("doc", None, "Presse", "articles de presse"),
    ("chat", None, "Forums", "forums"),
    (None, "A–Z", "Encyclopédies", "encyclopédies"),
    ("book", None, "Livres", "livres"),
    ("code", None, "Code", "code informatique"),
    ("image", None, "Images", "images"),
)


def scene_scraping(ctx, t, timeline):
    label(ctx, "Le scraping, ou moissonnage", INK)
    pg = pop(t, timeline.start(4) + 0.3)
    if pg > 0.001:
        with Transform(ctx, 730, 320, pg):
            globe(ctx, 0, 0, 92, INK, t)
        text(ctx, "Le web", 730, 196, 24, NAVY, SEMIBOLD, alpha=pg)
    tile(
        ctx,
        1190,
        320,
        pop(t, timeline.cue(4, "aspirent") - 0.4),
        TEAL,
        "db",
        caption="Données",
        caption2="d’entraînement",
        size=150,
    )
    pb = pop(t, timeline.cue(4, "programmes") - 0.2)
    if pb > 0.001:  # a little crawler robot running around the globe
        g = t * 1.2
        bx, by = 730 + 112 * math.cos(g), 320 + 112 * math.sin(g)
        with Transform(ctx, bx, by, pb):
            rounded_rect(ctx, -24, -20, 48, 40, 10)
            fill(ctx, CORAL)
            for dx in (-9, 9):
                circle(ctx, dx, -3, 5)
                fill(ctx, WHITE)
            ctx.move_to(0, -20)
            ctx.line_to(0, -30)
            stroke(ctx, CORAL, 1, 3)
            circle(ctx, 0, -32, 4)
            fill(ctx, CORAL)
    fa = appear(t, timeline.cue(4, "aspirent") - 0.1)
    if fa > 0.01:
        for j in range(7):
            u = (t * 0.7 + j / 7) % 1
            x = lerp(835, 1105, u)
            y = 320 - 60 * math.sin(PI * u)
            rounded_rect(ctx, x - 9, y - 11, 18, 22, 3)
            fill(ctx, mix_colors(INK, TEAL, u), fa * math.sin(PI * u))
    for j, (icon_name, glyph, caption, words) in enumerate(SOURCES):
        r, c = divmod(j, 3)
        tile(
            ctx,
            (727, 960, 1193)[c],
            545 + r * 150,
            pop(t, timeline.cue(4, words) - 0.2),
            TEAL if r == 0 else CORAL,
            icon_name,
            glyph,
            caption,
            size=96,
        )


# ====================================================================== 5 quantities
PEOPLE_ORDER = random.Random(7).sample(range(64), 64)


def format_thousands(n):
    """1000000 -> '1 000 000' (French digit grouping)."""
    return f"{n:,}".replace(",", " ")


def scene_quantities(ctx, t, timeline):
    label(ctx, "Des quantités titanesques", CORAL)
    t0 = timeline.start(5) + 0.2  # the counter runs until 'milliers de milliards' is said
    g = ease_in_out(progress(t, t0, timeline.cue(5, "milliers de milliards") + 0.8 - t0))
    if g > 0:
        n = 10 ** (12 * g) if g < 1 else 10**12
        with Transform(ctx, CENTER_X, 240, pop(t, t0)):
            text(
                ctx,
                format_thousands(int(n)) + (" +" if g >= 1 else ""),
                0,
                0,
                62,
                NAVY,
                EXTRABOLD,
                max_width=740,
            )
        text(
            ctx,
            "des milliers de milliards de mots",
            CENTER_X,
            315,
            28,
            CORAL,
            SEMIBOLD,
            alpha=appear(t, timeline.cue(5, "milliers de milliards") - 0.2),
        )
    tp = timeline.cue(5, "Derrière ces chiffres") - 0.2
    grey = appear(t, timeline.cue(5, "jamais") - 0.2, 0.8)
    for n, idx in enumerate(PEOPLE_ORDER):
        p = pop(t, tp + 0.035 * n, 0.4)
        if p > 0.001:
            r, c = divmod(idx, 16)
            k = mix_colors(SKINS[idx % len(SKINS)] if idx % 3 else TEAL, GREY, grey * 0.8)
            icon(ctx, "person", 618 + c * 45.6, 420 + r * 56, 44 * p, k)
    for j, (w, words) in enumerate((("écrits", "écrits"), ("photos", "photos"), ("travail", "travail"))):
        p = pop(t, timeline.cue(5, words) - 0.2)
        if p > 0.001:
            with Transform(ctx, 760 + j * 200, 650, p):
                pill(ctx, w, 0, 0, 22, lighter(INK, 0.85), INK, SEMIBOLD, height=44)
    p = pop(t, timeline.cue(5, "jamais") - 0.1)
    if p > 0.001:
        with Transform(ctx, CENTER_X, 730, p):
            pill(ctx, "Jamais consultées", 0, 0, 30, CORAL, WHITE, EXTRABOLD, height=64)


# ====================================================================== 6 copyright
def scene_copyright(ctx, t, timeline):
    label(ctx, "Le droit d’auteur", NAVY)
    p = pop(t, timeline.cue(6, "droit d") - 0.2)
    if p > 0.001:
        with Transform(ctx, CENTER_X, 270, p):
            circle(ctx, 0, 0, 82)
            fill(ctx, NAVY, 0.08)
            circle(ctx, 0, 0, 82)
            stroke(ctx, NAVY, 1, 10)
            text(ctx, "C", 4, -4, 110, NAVY, EXTRABOLD)
    y = 480
    tile(ctx, 720, y, pop(t, timeline.cue(6, "copier") - 0.3), INK, "doc", caption="Œuvre", size=110)
    flow(ctx, t, 790, y, 880, y, INK, appear(t, timeline.cue(6, "copier")), dots=3)
    tile(ctx, 960, y, pop(t, timeline.cue(6, "copier") + 0.1), INK, "doc", caption="Copie", size=110)
    pa = pop(t, timeline.cue(6, "autorisation") - 0.2)
    if pa > 0.001:
        with Transform(ctx, 1190, y, pa):
            rounded_rect(ctx, -120, -55, 240, 110, 20)
            fill(ctx, TEAL, 0.12)
            icon(ctx, "shield", -72, 0, 64, TEAL)
            text(ctx, "Autorisation", 34, -14, 22, TEAL, SEMIBOLD)
            text(ctx, "nécessaire", 34, 16, 22, TEAL, SEMIBOLD)
    p = pop(t, timeline.cue(6, "Or, pour") - 0.2)
    if p > 0.001:
        with Transform(ctx, CENTER_X, 690, p):
            rounded_rect(ctx, -360, -60, 720, 120, 24)
            fill(ctx, CORAL, 0.12)
            icon(ctx, "net", -290, 0, 70, CORAL)
            text(ctx, "Entraîner une IA", 25, -20, 30, NAVY, EXTRABOLD)
            text(
                ctx,
                "= d’abord copier les données",
                25,
                22,
                26,
                CORAL,
                SEMIBOLD,
                alpha=appear(t, timeline.cue(6, "copier les données") - 0.3),
            )


# ====================================================================== 7 European directive / opt-out
def scene_directive(ctx, t, timeline):
    kb = appear(t, timeline.cue(7, "condition importante") - 0.3, 0.7)
    label(ctx, "En Europe" if kb < 0.5 else "L’opt-out", EU_BLUE if kb < 0.5 else CORAL)
    if kb < 0.999:
        with AlphaGroup(ctx, 1 - kb):
            p = pop(t, timeline.cue(7, "En Europe") - 0.1)
            if p > 0.001:
                eu_flag(ctx, CENTER_X, 260, p)
            with Transform(ctx, CENTER_X, 395, pop(t, timeline.cue(7, "directive 2019") - 0.2)):
                text(ctx, "Directive (UE) 2019/790", 0, 0, 40, NAVY, EXTRABOLD)
            p = pop(t, timeline.cue(7, "exception") - 0.2)
            if p > 0.001:
                with Transform(ctx, CENTER_X, 470, p):
                    pill(
                        ctx,
                        "Exception de fouille de textes et de données",
                        0,
                        0,
                        22,
                        lighter(EU_BLUE, 0.85),
                        EU_BLUE,
                        SEMIBOLD,
                        height=50,
                    )
            y = 600
            tile(
                ctx,
                730,
                y,
                pop(t, timeline.cue(7, "Elle autorise") - 0.2),
                INK,
                "doc",
                caption="Contenus",
                caption2="légaux",
                size=100,
            )
            flow(ctx, t, 790, y, 900, y, TEAL, appear(t, timeline.cue(7, "copie automatisée") - 0.2), dots=3)
            tile(
                ctx,
                960,
                y,
                pop(t, timeline.cue(7, "copie automatisée") - 0.2),
                TEAL,
                "gear",
                caption="Copie",
                caption2="automatisée",
                size=100,
            )
            flow(ctx, t, 1020, y, 1130, y, TEAL, appear(t, timeline.cue(7, "analyser") - 0.2), dots=3)
            tile(
                ctx,
                1190,
                y,
                pop(t, timeline.cue(7, "analyser") - 0.2),
                CORAL,
                "net",
                caption="Analyse",
                size=100,
            )
    if kb > 0.001:
        with AlphaGroup(ctx, kb):
            text(ctx, "Une condition importante :", CENTER_X, 200, 30, NAVY, SEMIBOLD)
            off = progress(t, timeline.cue(7, "opt-out") - 0.2, 0.5)
            a = appear(t, timeline.cue(7, "peuvent s") - 0.3)
            text(ctx, "les auteurs et autrices", 800, 268, 26, NAVY, SEMIBOLD, alpha=a)
            text(ctx, "peuvent s’y opposer", 800, 304, 26, CORAL, EXTRABOLD, alpha=a)
            if a > 0.01:
                toggle(ctx, 1150, 286, off)
                text(ctx, "OPT-OUT", 1150, 336, 18, CORAL, EXTRABOLD, alpha=off)
            for j, (icon_name, caption, words) in enumerate(
                (
                    ("doc", "Un site", "Un site"),
                    ("book", "Un éditeur", "un éditeur"),
                    ("pen", "Un artiste", "un artiste"),
                )
            ):
                tile(
                    ctx,
                    740 + j * 220,
                    445,
                    pop(t, timeline.cue(7, words) - 0.2),
                    INK,
                    icon_name,
                    caption=caption,
                    size=100,
                )
            p = pop(t, timeline.cue(7, "lisible") - 0.2)
            if p > 0.001:
                with Transform(ctx, CENTER_X, 690, p):
                    rounded_rect(ctx, -300, -70, 600, 140, 18)
                    fill(ctx, NAVY)
                    text(ctx, "robots.txt", -280, -42, 18, GREY, MEDIUM, align="left")
                    text(ctx, "User-agent: GPTBot", -230, -2, 28, GOLD, SEMIBOLD, align="left")
                    text(ctx, "Disallow: /", -230, 38, 28, WHITE, SEMIBOLD, align="left")
                    pr = pop(t, timeline.cue(7, "refuse") - 0.2)
                    if pr > 0.001:
                        with Transform(ctx, 210, 18, pr, -0.12):
                            rounded_rect(ctx, -64, -28, 128, 56, 10)
                            stroke(ctx, CORAL, 1, 5)
                            text(ctx, "REFUS", 0, 0, 28, CORAL, EXTRABOLD)
                text(
                    ctx,
                    "Un signal lisible par les machines",
                    CENTER_X,
                    590,
                    22,
                    INK,
                    MEDIUM,
                    alpha=appear(t, timeline.cue(7, "lisible")),
                )


# ====================================================================== 8 balance
def scene_balance(ctx, t, timeline):
    kp = appear(t, timeline.cue(8, "En pratique") - 0.2, 0.6)
    label(ctx, "Sur le papier" if kp < 0.5 else "En pratique", TEAL if kp < 0.5 else CORAL)
    tilt = 0.17 * ease_in_out(progress(t, timeline.cue(8, "compliqué") - 0.4, 1.2)) + 0.03 * math.sin(
        t * 2.2
    ) * (1 - kp * 0.5)
    with AlphaGroup(ctx, appear(t, timeline.start(8))):
        scales(ctx, CENTER_X, 215, tilt, t)
    text(
        ctx,
        "L’équilibre semble trouvé…",
        CENTER_X,
        545,
        32,
        TEAL,
        EXTRABOLD,
        alpha=appear(t, timeline.cue(8, "équilibre") - 0.3) * (1 - kp),
    )
    text(ctx, "… mais c’est plus compliqué", CENTER_X, 545, 32, CORAL, EXTRABOLD, alpha=kp)
    for j, (s, words) in enumerate(
        (
            ("Comment savoir si son opposition a été respectée ?", "comment savoir"),
            ("Et tout ce qui a été aspiré avant ?", "aspiré avant"),
        )
    ):
        p = pop(t, timeline.cue(8, words) - 0.3)
        if p > 0.001:
            with Transform(ctx, CENTER_X, 635 + j * 82, p):
                pill(ctx, s, 0, 0, 24, lighter(CORAL, 0.85), CORAL, SEMIBOLD, height=60)


def scene_list(timeline):
    return [
        (0.0, scene_title),
        (timeline.start(1) - 0.3, scene_exmachina),
        (timeline.start(2) - 0.2, scene_illegal),
        (timeline.start(3) - 0.2, scene_llm),
        (timeline.start(4) - 0.2, scene_scraping),
        (timeline.start(5) - 0.2, scene_quantities),
        (timeline.start(6) - 0.2, scene_copyright),
        (timeline.start(7) - 0.2, scene_directive),
        (timeline.start(8) - 0.2, scene_balance),
        (timeline.end_start, scene_end),
    ]
