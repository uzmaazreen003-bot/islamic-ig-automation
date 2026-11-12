"""Scenery for story reels: colour themes per story, people (man, woman, child, elder) and everyday props.

Everything is drawn with simple vector shapes (original artwork). Figures are silhouettes/stick figures in the
calm black-and-gold spirit of the reference videos, but with enough variety to tell a story.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from . import theme

W, H = 720, 1280
GROUND = 905

THEMES = {
    "gold":    dict(top=(12, 10, 8),   bot=(34, 25, 13),  ground=(8, 7, 6),    fig=(246, 240, 228), other=(190, 180, 160), accent=(236, 190, 112), text=(246, 240, 228), glow=(255, 226, 160), prop=(214, 168, 92),  dark=False),
    "emerald": dict(top=(5, 20, 16),   bot=(14, 42, 32),  ground=(4, 14, 11),   fig=(240, 244, 230), other=(168, 190, 170), accent=(226, 204, 120), text=(240, 244, 230), glow=(190, 255, 214), prop=(120, 180, 140), dark=False),
    "maroon":  dict(top=(30, 8, 14),   bot=(62, 18, 28),  ground=(20, 5, 9),    fig=(250, 238, 226), other=(206, 170, 160), accent=(240, 200, 150), text=(250, 238, 226), glow=(255, 196, 170), prop=(210, 130, 120), dark=False),
    "dusk":    dict(top=(40, 22, 16),  bot=(120, 62, 36), ground=(26, 14, 10),  fig=(255, 244, 228), other=(222, 190, 160), accent=(255, 214, 150), text=(255, 244, 228), glow=(255, 170, 90),  prop=(240, 170, 100), dark=False),
    "dawn":    dict(top=(250, 242, 230), bot=(238, 214, 186), ground=(206, 180, 150), fig=(52, 36, 30), other=(118, 96, 84), accent=(160, 100, 50), text=(60, 36, 30), glow=(255, 226, 180), prop=(176, 120, 70), dark=True),
    "plum":    dict(top=(22, 12, 30),  bot=(52, 28, 56),  ground=(14, 8, 20),   fig=(246, 236, 244), other=(190, 170, 196), accent=(238, 196, 140), text=(246, 236, 244), glow=(220, 170, 230), prop=(190, 140, 200), dark=False),
}


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def backdrop(th, kind="none", seed=0, ground=True):
    """Sky gradient, optional far scenery silhouettes, and the ground."""
    img = theme.gradient(W, H, th["top"], th["bot"]).convert("RGBA")
    d = ImageDraw.Draw(img)
    sil = lerp(th["ground"], th["bot"], 0.35)
    rng = np.random.default_rng(seed)
    if kind in ("city", "street"):
        x = -20
        while x < W:
            w = int(rng.integers(50, 110)); h = int(rng.integers(120, 300) if kind == "city" else rng.integers(90, 170))
            d.rectangle((x, GROUND - h, x + w, GROUND), fill=sil + (255,))
            for wy in range(GROUND - h + 18, GROUND - 20, 34):
                for wx in range(x + 10, x + w - 14, 22):
                    if rng.random() < 0.28:
                        d.rectangle((wx, wy, wx + 8, wy + 12), fill=th["glow"] + (170,))
            x += w + int(rng.integers(4, 18))
    elif kind == "dunes":
        for k, (amp, yy, a) in enumerate(((60, GROUND - 120, 255), (90, GROUND - 70, 255))):
            pts = [(0, GROUND)]
            for x in range(0, W + 20, 20):
                pts.append((x, yy - amp * (0.5 + 0.5 * math.sin(x / 130.0 + k * 2 + seed))))
            pts.append((W, GROUND))
            d.polygon(pts, fill=lerp(th["ground"], th["bot"], 0.25 + 0.2 * k) + (a,))
    elif kind == "mosque":
        img.alpha_composite(theme.skyline(W, 420, sil, 255), (0, GROUND - 420))
    elif kind == "village":
        for x in range(-30, W, 150):
            hh = int(rng.integers(70, 120))
            d.rectangle((x, GROUND - hh, x + 100, GROUND), fill=sil + (255,))
            d.polygon([(x - 10, GROUND - hh), (x + 50, GROUND - hh - 50), (x + 110, GROUND - hh)], fill=sil + (255,))
            d.rectangle((x + 40, GROUND - 45, x + 60, GROUND), fill=th["glow"] + (120,))
    # stars on dark themes
    if not th["dark"]:
        for _ in range(60):
            sx, sy = int(rng.integers(10, W - 10)), int(rng.integers(20, (GROUND if ground else H) - 260))
            r = rng.uniform(0.6, 1.8)
            d.ellipse((sx - r, sy - r, sx + r, sy + r), fill=th["glow"] + (int(rng.integers(40, 150)),))
    if ground:
        d.rectangle((0, GROUND, W, H), fill=th["ground"] + (255,))
        d.line((0, GROUND, W, GROUND), fill=th["accent"] + (70,), width=1)
    return img


# ------------------------------------------------------------------ people

def person(kind, x, pose, t, th, who="main", face=1, scale=1.0):
    """Return (RGBA patch, anchor_x, anchor_y_of_feet) for one person. Drawn at 3x then reduced."""
    S = 3
    pw, ph = 420, 470
    patch = Image.new("RGBA", (pw * S, ph * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(patch)
    col = (th["fig"] if who == "main" else th["other"]) + (255,)
    acc = th["accent"] + (255,)
    k = {"man": 1.0, "woman": 0.96, "child": 0.56, "elder": 0.95}[kind] * scale * 1.75
    sc = k * S
    ox, oy = pw * S / 2, (ph - 8) * S
    walking = pose == "walk"
    swing = math.sin(t * 5.0) * 0.5 if walking else 0.05
    lean = {"walk": 0.04, "stand": 0.0, "slump": 0.4, "open": 0.0, "give": 0.05, "sit": 0.08, "look": -0.05}[pose]
    if kind == "elder":
        lean += 0.2
    thigh, shin, torso, uarm, farm = 42, 42, 74, 30, 30
    hip_h = (thigh + shin) * 0.97 if pose != "sit" else 10
    hip = (ox, oy - hip_h * sc)
    neck = (hip[0] + math.sin(lean) * torso * sc, hip[1] - math.cos(lean) * torso * sc)
    head_r = (15 if kind != "child" else 19) * sc / (k / 1.0 / (k if kind != "child" else k)) if False else (15 * sc if kind != "child" else 15 * sc * 1.5 / 1.0 * 0.62 / 0.56)
    head_dir = lean + (0.2 if pose == "slump" else 0.0) + (-0.2 if pose == "look" else 0.0)
    head = (neck[0] + math.sin(head_dir) * (head_r + 3 * sc), neck[1] - math.cos(head_dir) * (head_r + 3 * sc))
    w = max(3, int(3.4 * sc / 1.0 * 0.5))

    def seg(a, b):
        d.line([a, b], fill=col, width=w)

    def limb(origin, a1, l1, a2, l2):
        kx = (origin[0] + math.sin(a1) * l1 * sc, origin[1] + math.cos(a1) * l1 * sc)
        ex = (kx[0] + math.sin(a2) * l2 * sc, kx[1] + math.cos(a2) * l2 * sc)
        return kx, ex

    # legs (hidden under a dress for women)
    if kind == "woman":
        hem_y = oy - 14 * sc
        d.polygon([(neck[0] - 13 * sc, neck[1] + 6 * sc), (neck[0] + 13 * sc, neck[1] + 6 * sc),
                   (hip[0] + 34 * sc, hem_y), (hip[0] - 34 * sc, hem_y)], fill=col)
    else:
        for sgn in (1, -1):
            if pose == "sit":
                kn = (hip[0] + 40 * sc, hip[1] + 4 * sc)
                fo = (kn[0] + 6 * sc, oy)
                d.line([hip, kn, fo], fill=col, width=w, joint="curve")
            else:
                a = swing * sgn
                kn, fo = limb(hip, a, thigh, a - max(0.0, -a) * 0.8, shin)
                d.line([hip, kn, fo], fill=col, width=w, joint="curve")
    seg(hip, neck)
    sh = (neck[0] - math.sin(lean) * 8 * sc, neck[1] + math.cos(lean) * 8 * sc)
    for sgn in (1, -1):
        if pose == "open":
            e1 = (sh[0] + sgn * uarm * sc * 0.95, sh[1] - uarm * sc * 0.18)
            e2 = (e1[0] + sgn * farm * sc * 0.95, e1[1] - farm * sc * 0.28)
        elif pose == "give" and sgn == 1:
            e1 = (sh[0] + uarm * sc * 0.95, sh[1] + uarm * sc * 0.25)
            e2 = (e1[0] + farm * sc * 0.95, e1[1] + farm * sc * 0.05)
        elif pose == "slump":
            e1 = (sh[0] + sgn * 4 * sc, sh[1] + uarm * sc)
            e2 = (e1[0] + sgn * 2 * sc, e1[1] + farm * sc)
        else:
            ang = -swing * sgn * 0.9 + sgn * 0.12 if walking else sgn * 0.12
            e1 = (sh[0] + math.sin(ang) * uarm * sc, sh[1] + math.cos(ang) * uarm * sc)
            e2 = (e1[0] + math.sin(ang * 0.6) * farm * sc, e1[1] + math.cos(ang * 0.6) * farm * sc)
        d.line([sh, e1, e2], fill=col, width=w, joint="curve")
        if kind == "elder" and sgn == -1:      # cane in the back hand
            d.line([e2, (e2[0] - 2 * sc, oy)], fill=acc, width=max(3, int(w * 0.8)))
    # head
    d.ellipse((head[0] - head_r, head[1] - head_r, head[0] + head_r, head[1] + head_r), fill=col)
    if kind == "woman":                      # hijab: wraps the head and falls over the shoulders
        d.ellipse((head[0] - head_r * 1.28, head[1] - head_r * 1.2, head[0] + head_r * 1.28, head[1] + head_r * 1.35), fill=col)
        d.polygon([(head[0] - head_r * 1.25, head[1] + head_r * 0.4), (head[0] + head_r * 1.25, head[1] + head_r * 0.4),
                   (neck[0] + 20 * sc, neck[1] + 34 * sc), (neck[0] - 20 * sc, neck[1] + 34 * sc)], fill=col)
        d.ellipse((head[0] - head_r * 0.62 + 3 * sc, head[1] - head_r * 0.5, head[0] + head_r * 0.62 + 3 * sc, head[1] + head_r * 0.55), fill=th["ground"] + (150,) if not th["dark"] else (255, 255, 255, 90))
    if kind == "man":                        # small prayer cap
        d.pieslice((head[0] - head_r * 1.02, head[1] - head_r * 1.05, head[0] + head_r * 1.02, head[1] + head_r * 0.95), 180, 360, fill=acc)
    if kind == "elder":                      # white beard and cap
        d.polygon([(head[0] - head_r * 0.7, head[1] + head_r * 0.3), (head[0] + head_r * 0.7, head[1] + head_r * 0.3), (head[0] + 2 * sc, head[1] + head_r * 1.9)], fill=(236, 232, 222, 255) if not th["dark"] else (120, 110, 100, 255))
        d.pieslice((head[0] - head_r * 1.02, head[1] - head_r * 1.05, head[0] + head_r * 1.02, head[1] + head_r * 0.95), 180, 360, fill=acc)
    patch = patch.resize((pw, ph), Image.LANCZOS)
    if face < 0:
        patch = ImageOps.mirror(patch)
    return patch, pw // 2, ph - 8, (hip, neck, head, sh)


# ------------------------------------------------------------------ props

def _fnt(size):
    return theme.poppins("medium", size)


def draw_prop(img, kind, x, th, scale=1.0, y=None, text="", t=0.0):
    """Draw one prop onto `img` (RGBA, canvas size). x is a fraction of the width; y (fraction of H) overrides the ground."""
    S = 2
    big = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    cx = x * W * S
    gy = GROUND * S if y is None else y * H * S
    s = scale * S
    pr, ac, gl, gr = th["prop"] + (255,), th["accent"] + (255,), th["glow"], th["ground"]
    dim = lerp(th["bot"], th["prop"], 0.45) + (255,)
    dark = lerp(gr, th["bot"], 0.5) + (255,)

    def rect(x0, y0, x1, y1, fill, r=0):
        if r:
            d.rounded_rectangle((cx + x0 * s, gy + y0 * s, cx + x1 * s, gy + y1 * s), radius=r * s, fill=fill)
        else:
            d.rectangle((cx + x0 * s, gy + y0 * s, cx + x1 * s, gy + y1 * s), fill=fill)

    def ell(x0, y0, x1, y1, fill):
        d.ellipse((cx + x0 * s, gy + y0 * s, cx + x1 * s, gy + y1 * s), fill=fill)

    def poly(pts, fill):
        d.polygon([(cx + px * s, gy + py * s) for px, py in pts], fill=fill)

    def glow_win(x0, y0, x1, y1):
        rect(x0, y0, x1, y1, gl + (230,))

    if kind == "house":
        rect(-130, -190, 130, 0, dim)
        poly([(-150, -190), (0, -290), (150, -190)], dark)
        glow_win(-90, -140, -40, -90); glow_win(40, -140, 90, -90)
        rect(-22, -100, 22, 0, dark, 4)
    elif kind == "mansion":
        rect(-190, -230, 190, 0, dim)
        rect(-60, -330, 60, -230, dim)
        poly([(-70, -330), (0, -400), (70, -330)], dark)
        for wx in range(-165, 150, 55):
            for wy in (-200, -140, -80):
                glow_win(wx, wy, wx + 28, wy + 38)
        rect(-26, -90, 26, 0, dark, 6)
    elif kind == "door":
        rect(-75, -300, 75, 0, dark, 10)
        d.pieslice((cx - 75 * s, gy - 360 * s, cx + 75 * s, gy - 240 * s), 180, 360, fill=dark)
        rect(-55, -280, 55, 0, gl + (60,), 8)
        ell(34, -140, 46, -128, ac)
    elif kind == "tree":
        rect(-14, -230, 14, 0, dark if th["dark"] else lerp(gr, th["prop"], 0.35) + (255,), 4)
        for (ex, ey, er) in ((0, -300, 110), (-70, -250, 80), (70, -250, 80), (0, -380, 80)):
            ell(ex - er, ey - er, ex + er, ey + er, lerp(th["bot"], th["prop"], 0.55) + (255,))
    elif kind == "sprout":
        ell(-44, -12, 44, 12, dark)
        rect(-2, -52, 2, -8, pr)
        ell(-20, -64, 0, -46, pr); ell(0, -70, 22, -50, pr)
    elif kind == "dog":
        body = lerp(th["bot"], th["other"], 0.8) + (255,)
        rect(-60, -62, 44, -22, body, 20)
        ell(32, -88, 76, -48, body)
        poly([(66, -80), (84, -64), (66, -62)], body)
        poly([(36, -88), (44, -108), (54, -88)], body)
        for lx in (-48, -26, 20, 36):
            rect(lx, -30, lx + 8, 0, body)
        d.line([(cx - 58 * s, gy - 50 * s), (cx - 84 * s, gy - 78 * s)], fill=body, width=int(7 * s))
    elif kind == "bowl":
        d.pieslice((cx - 50 * s, gy - 46 * s, cx + 50 * s, gy + 6 * s), 0, 180, fill=pr)
        rect(-50, -28, 50, -20, th["glow"] + (200,))
    elif kind == "plate":
        ell(-44, -12, 44, 6, pr)
        d.pieslice((cx - 28 * s, gy - 34 * s, cx + 28 * s, gy - 6 * s), 180, 360, fill=ac)
    elif kind == "phone":
        rect(-38, -130, 38, 0, dark, 10)
        rect(-32, -122, 32, -10, gl + (200,), 6)
    elif kind == "coins":
        for i in range(6):
            ell(-50, -14 - i * 12, 50, 4 - i * 12, ac if i % 2 == 0 else pr)
    elif kind == "heart":
        rr = 40
        ell(-rr, -rr, 0, rr * 0.4, ac); ell(0, -rr, rr, rr * 0.4, ac)
        poly([(-rr * 0.97, -4), (rr * 0.97, -4), (0, rr * 1.35)], ac)
    elif kind == "mosque":
        rect(-120, -190, 120, 0, dim)
        d.pieslice((cx - 120 * s, gy - 330 * s, cx + 120 * s, gy - 70 * s), 180, 360, fill=dim)
        rect(-4, -380, 4, -320, ac); ell(-10, -400, 10, -380, ac)
        rect(150, -330, 180, 0, dim); poly([(146, -330), (184, -330), (165, -400)], dim)
        rect(-120, -190, -90, 0, dim)
        d.pieslice((cx - 36 * s, gy - 130 * s, cx + 36 * s, gy + 40 * s), 180, 360, fill=gl + (210,))
        rect(-36, -45, 36, 0, gl + (210,))
    elif kind == "stall":
        rect(-130, -120, 130, -90, pr, 4)
        rect(-120, -90, -108, 0, dark); rect(108, -90, 120, 0, dark)
        for i in range(8):
            poly([(-140 + i * 35, -250), (-105 + i * 35, -250), (-105 + i * 35 + 8, -190), (-140 + i * 35 - 2, -190)], ac if i % 2 == 0 else dim)
        rect(-140, -270, 140, -250, dark, 3)
        for i in range(4):
            ell(-90 + i * 50, -150, -60 + i * 50, -120, pr)
    elif kind == "gift":
        rect(-34, -50, 34, 0, ac, 4); rect(-4, -50, 4, 0, dark); rect(-34, -30, 34, -24, dark)
    elif kind == "sun":
        ell(-48, -48, 48, 48, ac)
        d.ellipse((cx - 110 * s, gy - 110 * s, cx + 110 * s, gy + 110 * s), outline=ac[:3] + (70,), width=int(3 * s))
    elif kind == "clock":
        ell(-48, -48, 48, 48, dark); ell(-42, -42, 42, 42, gl + (60,))
        d.line([(cx, gy), (cx, gy - 30 * s)], fill=ac, width=int(4 * s)); d.line([(cx, gy), (cx + 22 * s, gy + 8 * s)], fill=ac, width=int(4 * s))
    elif kind == "book":
        poly([(-60, 0), (0, -14), (60, 0), (60, 14), (0, 0), (-60, 14)], pr)
        d.line([(cx, gy - 14 * s), (cx, gy)], fill=dark, width=int(2 * s))
    elif kind == "lamp":
        d.pieslice((cx - 26 * s, gy - 60 * s, cx + 26 * s, gy - 4 * s), 180, 360, fill=ac)
        rect(-2, -4, 2, 0, ac)
        d.ellipse((cx - 90 * s, gy - 100 * s, cx + 90 * s, gy + 40 * s), outline=None, fill=gl + (26,))
    elif kind == "tears":
        for i, ox in enumerate((-16, 18)):
            yy = ((t * 70 + i * 40) % 80)
            ell(ox - 4, yy - 6, ox + 4, yy + 6, gl + (200,))
    elif kind == "sparkles":
        rng = np.random.default_rng(3)
        for _ in range(14):
            sx, sy = rng.uniform(-110, 110), rng.uniform(-260, -20)
            r = rng.uniform(3, 7)
            poly([(sx, sy - r * 1.6), (sx + r * 0.5, sy - r * 0.5), (sx + r * 1.6, sy), (sx + r * 0.5, sy + r * 0.5), (sx, sy + r * 1.6), (sx - r * 0.5, sy + r * 0.5), (sx - r * 1.6, sy), (sx - r * 0.5, sy - r * 0.5)], gl + (210,))
    elif kind == "bubble":
        f = _fnt(int(30 * S * scale))
        lines = text.split("\\n")
        tw = max(d.textlength(l, font=f) for l in lines)
        lh = 38 * S * scale
        pad = 20 * S * scale
        bw, bh = tw + pad * 2, lh * len(lines) + pad * 1.2
        x0, y0 = cx - bw / 2, gy - bh
        fill = (250, 242, 228, 255) if not th["dark"] else (60, 40, 34, 255)
        tc = (50, 34, 28, 255) if not th["dark"] else (250, 242, 228, 255)
        d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=22 * S, fill=fill)
        d.polygon([(cx - 14 * S, y0 + bh - 2), (cx + 14 * S, y0 + bh - 2), (cx - 4 * S, y0 + bh + 26 * S)], fill=fill)
        for i, l in enumerate(lines):
            d.text((cx, y0 + pad * 0.6 + i * lh), l, font=f, fill=tc, anchor="ma")
    else:
        raise ValueError(f"unknown prop {kind}")
    img.alpha_composite(big.resize((W, H), Image.LANCZOS))
