"""Vector-style artwork for story reels: themes (sky/ground), props and characters. All drawn with Pillow, original."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from . import theme as th

W, H = 720, 1280
HORIZON = 905
S = 3  # supersampling for props and figures

WARM = (246, 240, 228)
GOLD = (236, 190, 112)

THEMES = {
    "night":  dict(top=(8, 8, 9), bot=(24, 19, 13), ground=(5, 5, 6), body="moon", body_pos=(0.80, 0.15), body_col=(238, 232, 212),
                   stars=True, rain=False, parts=(255, 232, 180), beam=(255, 226, 160), hills=0),
    "dusk":   dict(top=(34, 22, 12), bot=(128, 82, 30), ground=(16, 11, 7), body="sun", body_pos=(0.30, 0.16), body_col=(255, 214, 120),
                   stars=False, rain=False, parts=(255, 200, 110), beam=(255, 214, 140), hills=30),
    "dawn":   dict(top=(30, 16, 44), bot=(214, 112, 72), ground=(14, 8, 18), body="sun", body_pos=(0.72, 0.70), body_col=(255, 196, 130),
                   stars=False, rain=False, parts=(255, 214, 170), beam=(255, 206, 150), hills=34),
    "rain":   dict(top=(12, 16, 22), bot=(44, 56, 68), ground=(8, 10, 13), body=None, body_pos=(0.5, 0.2), body_col=(200, 210, 220),
                   stars=False, rain=True, parts=(170, 190, 210), beam=(210, 225, 240), hills=0),
    "desert": dict(top=(26, 17, 9), bot=(150, 98, 42), ground=(38, 25, 11), body="moon", body_pos=(0.24, 0.17), body_col=(246, 232, 196),
                   stars=True, rain=False, parts=(255, 214, 140), beam=(255, 222, 160), hills=44),
    "forest": dict(top=(5, 12, 10), bot=(18, 44, 32), ground=(4, 10, 8), body="moon", body_pos=(0.78, 0.14), body_col=(226, 238, 214),
                   stars=False, rain=False, parts=(214, 255, 150), beam=(226, 255, 190), hills=26),
}


def theme_of(name):
    return THEMES.get(name, THEMES["night"])


def background(name, seed=0):
    T = theme_of(name)
    bg = th.gradient(W, H, T["top"], T["bot"]).convert("RGBA")
    d = ImageDraw.Draw(bg)
    rng = np.random.default_rng(seed + 5)
    if T["stars"]:
        for _ in range(60):
            x, y, r = rng.uniform(0, W), rng.uniform(0, HORIZON * 0.7), rng.uniform(0.6, 1.6)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 244, 220, int(rng.uniform(60, 190))))
    if T["body"]:
        bx, by = T["body_pos"][0] * W, T["body_pos"][1] * H
        glow = th.glow_layer(W, H, [(bx, by, 170, 0.55)], T["body_col"])
        bg.alpha_composite(glow)
        if T["body"] == "sun":
            d = ImageDraw.Draw(bg)
            d.ellipse((bx - 46, by - 46, bx + 46, by + 46), fill=T["body_col"] + (255,))
        else:
            bg.alpha_composite(th.crescent(96, T["body_col"], 245), (int(bx - 48), int(by - 48)))
    # ground silhouette with gentle hills
    d = ImageDraw.Draw(bg)
    hills = T["hills"]
    pts = [(0, H)]
    for x in range(0, W + 20, 20):
        y = HORIZON - hills * (0.5 + 0.5 * math.sin(x / 95.0 + seed)) * (0.4 + 0.6 * math.sin(x / 260.0 + 1.0) ** 2) if hills else HORIZON
        pts.append((x, y))
    pts.append((W, H))
    d.polygon(pts, fill=T["ground"] + (255,))
    d.rectangle((0, HORIZON, W, H), fill=T["ground"] + (255,))
    d.line((0, HORIZON, W, HORIZON), fill=(150, 130, 100, 70), width=1)
    return bg


# ------------------------------------------------------------------ props

def _patch(w, h):
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _blit(dst, patch, x, ground_y, w, h, alpha=1.0, scale=1.0):
    p = patch.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    if alpha < 0.999:
        a = p.getchannel("A").point(lambda v: int(v * alpha))
        p.putalpha(a)
    dst.alpha_composite(p, (int(x - p.width / 2), int(ground_y - p.height + 4)))


def _p(v):
    return int(v * S)


def prop_gold(t):
    w, h = 220, 120
    img, d = _patch(w, h)
    d.pieslice((_p(10), _p(30), _p(210), _p(230)), 180, 360, fill=(222, 170, 70, 255))
    for i in range(14):
        a = 0.5 + 0.5 * math.sin(t * 3 + i)
        x, y = 30 + i * 12, 70 - abs(math.sin(i * 1.7)) * 36
        d.ellipse((_p(x), _p(y), _p(x + 5), _p(y + 5)), fill=(255, 236, 160, int(120 + 135 * a)))
    return img, w, h


def prop_car(t):
    w, h = 300, 120
    img, d = _patch(w, h)
    body = (238, 196, 70, 255)
    d.rounded_rectangle((_p(20), _p(50), _p(280), _p(96)), radius=_p(16), fill=body)
    d.polygon([(_p(78), _p(52)), (_p(110), _p(20)), (_p(210), _p(20)), (_p(244), _p(52))], fill=body)
    d.polygon([(_p(92), _p(50)), (_p(116), _p(27)), (_p(160), _p(27)), (_p(160), _p(50))], fill=(40, 34, 24, 255))
    d.polygon([(_p(168), _p(50)), (_p(168), _p(27)), (_p(206), _p(27)), (_p(230), _p(50))], fill=(40, 34, 24, 255))
    for cx in (80, 224):
        d.ellipse((_p(cx - 20), _p(78), _p(cx + 20), _p(118)), fill=(20, 18, 16, 255))
        d.ellipse((_p(cx - 8), _p(90), _p(cx + 8), _p(106)), fill=(120, 110, 96, 255))
    d.polygon([(_p(22), _p(62)), (_p(-70), _p(40)), (_p(-70), _p(100)), (_p(22), _p(80))], fill=(255, 236, 170, 60))
    return img, w, h


def prop_house(t):
    w, h = 240, 220
    img, d = _patch(w, h)
    d.rectangle((_p(30), _p(90), _p(210), _p(216)), fill=(70, 52, 36, 255))
    d.polygon([(_p(14), _p(92)), (_p(120), _p(22)), (_p(226), _p(92))], fill=(52, 36, 26, 255))
    d.rectangle((_p(100), _p(146), _p(140), _p(216)), fill=(30, 22, 16, 255))
    for x in (46, 156):
        d.rectangle((_p(x), _p(118), _p(x + 36), _p(150)), fill=(255, 214, 120, 255))
        d.line((_p(x + 18), _p(118), _p(x + 18), _p(150)), fill=(70, 52, 36, 255), width=_p(2))
    return img, w, h


def prop_mosque(t):
    w, h = 260, 260
    img, d = _patch(w, h)
    c = (210, 184, 130, 255)
    d.rectangle((_p(60), _p(130), _p(200), _p(256)), fill=c)
    d.pieslice((_p(70), _p(70), _p(190), _p(190)), 180, 360, fill=c)
    d.line((_p(130), _p(72), _p(130), _p(50)), fill=c, width=_p(3))
    d.rectangle((_p(14), _p(80), _p(40), _p(256)), fill=c)
    d.polygon([(_p(10), _p(80)), (_p(44), _p(80)), (_p(27), _p(40))], fill=c)
    d.rectangle((_p(220), _p(80), _p(246), _p(256)), fill=c)
    d.polygon([(_p(216), _p(80)), (_p(250), _p(80)), (_p(233), _p(40))], fill=c)
    d.rounded_rectangle((_p(112), _p(176), _p(148), _p(256)), radius=_p(16), fill=(255, 220, 140, 255))
    return img, w, h


def prop_tree(t):
    w, h = 200, 280
    img, d = _patch(w, h)
    d.polygon([(_p(92), _p(276)), (_p(108), _p(276)), (_p(104), _p(130)), (_p(96), _p(130))], fill=(66, 46, 30, 255))
    for cx, cy, r in ((100, 96, 54), (62, 130, 42), (140, 128, 44), (100, 150, 40)):
        d.ellipse((_p(cx - r), _p(cy - r), _p(cx + r), _p(cy + r)), fill=(40, 90, 52, 255))
    return img, w, h


def prop_sprout(t):
    w, h = 80, 90
    img, d = _patch(w, h)
    d.line((_p(40), _p(86), _p(40), _p(40)), fill=(110, 190, 90, 255), width=_p(4))
    d.ellipse((_p(40), _p(26), _p(66), _p(44)), fill=(120, 205, 100, 255))
    d.ellipse((_p(14), _p(36), _p(40), _p(54)), fill=(100, 180, 84, 255))
    d.ellipse((_p(22), _p(80), _p(58), _p(90)), fill=(70, 50, 34, 255))
    return img, w, h


def prop_plate(t):
    w, h = 120, 60
    img, d = _patch(w, h)
    d.ellipse((_p(10), _p(30), _p(110), _p(54)), fill=(236, 230, 218, 255))
    d.ellipse((_p(28), _p(22), _p(92), _p(46)), fill=(214, 160, 84, 255))
    d.ellipse((_p(42), _p(14), _p(78), _p(34)), fill=(236, 190, 110, 255))
    for i in range(3):
        a = 0.5 + 0.5 * math.sin(t * 2 + i)
        d.ellipse((_p(44 + i * 14), _p(4 - a * 4), _p(48 + i * 14), _p(8 - a * 4)), fill=(255, 255, 255, int(110 * a)))
    return img, w, h


def prop_gift(t):
    w, h = 90, 90
    img, d = _patch(w, h)
    d.rectangle((_p(12), _p(34), _p(78), _p(84)), fill=(236, 184, 70, 255))
    d.rectangle((_p(8), _p(26), _p(82), _p(40)), fill=(250, 210, 100, 255))
    d.rectangle((_p(40), _p(26), _p(50), _p(84)), fill=(190, 60, 60, 255))
    d.ellipse((_p(26), _p(8), _p(46), _p(28)), outline=(190, 60, 60, 255), width=_p(3))
    d.ellipse((_p(44), _p(8), _p(64), _p(28)), outline=(190, 60, 60, 255), width=_p(3))
    return img, w, h


def prop_stall(t):
    w, h = 260, 220
    img, d = _patch(w, h)
    d.rectangle((_p(30), _p(100), _p(36), _p(216)), fill=(90, 66, 44, 255))
    d.rectangle((_p(224), _p(100), _p(230), _p(216)), fill=(90, 66, 44, 255))
    for i in range(8):
        d.polygon([(_p(20 + i * 30), _p(60)), (_p(50 + i * 30), _p(60)), (_p(56 + i * 30), _p(100)), (_p(14 + i * 30), _p(100))],
                  fill=(210, 60, 50, 255) if i % 2 == 0 else (240, 232, 214, 255))
    d.rectangle((_p(24), _p(150), _p(236), _p(166)), fill=(110, 80, 52, 255))
    d.rectangle((_p(40), _p(120), _p(86), _p(150)), fill=(214, 170, 90, 255))
    d.rectangle((_p(110), _p(126), _p(150), _p(150)), fill=(150, 200, 120, 255))
    return img, w, h


def prop_phone(t):
    w, h = 70, 130
    img, d = _patch(w, h)
    d.rounded_rectangle((_p(6), _p(4), _p(64), _p(126)), radius=_p(10), fill=(24, 24, 28, 255), outline=(180, 180, 190, 255), width=_p(2))
    d.rounded_rectangle((_p(12), _p(16), _p(58), _p(112)), radius=_p(6), fill=(120, 190, 240, 255))
    for i in range(3):
        d.rounded_rectangle((_p(18), _p(28 + i * 24), _p(52), _p(40 + i * 24)), radius=_p(4), fill=(255, 255, 255, 200))
    return img, w, h


def prop_door(t):
    w, h = 120, 200
    img, d = _patch(w, h)
    d.rectangle((_p(14), _p(10), _p(106), _p(196)), fill=(255, 218, 130, 90))
    d.rectangle((_p(20), _p(16), _p(100), _p(196)), fill=(86, 58, 36, 255))
    d.rectangle((_p(30), _p(30), _p(90), _p(100)), outline=(60, 40, 26, 255), width=_p(3))
    d.ellipse((_p(84), _p(112), _p(94), _p(122)), fill=(236, 190, 90, 255))
    return img, w, h


def prop_dog(t):
    w, h = 150, 100
    img, d = _patch(w, h)
    c = (150, 120, 84, 255)
    d.ellipse((_p(30), _p(34), _p(110), _p(76)), fill=c)
    d.ellipse((_p(96), _p(24), _p(132), _p(58)), fill=c)
    d.polygon([(_p(104), _p(26)), (_p(112), _p(8)), (_p(118), _p(28))], fill=c)
    d.polygon([(_p(34), _p(46)), (_p(10), _p(30 + 4 * math.sin(t * 6))), (_p(36), _p(56))], fill=c)
    for x in (44, 60, 88, 100):
        d.rectangle((_p(x), _p(66), _p(x + 8), _p(96)), fill=c)
    d.ellipse((_p(120), _p(36), _p(124), _p(40)), fill=(20, 16, 12, 255))
    return img, w, h


def prop_lamp(t):
    w, h = 80, 260
    img, d = _patch(w, h)
    d.rectangle((_p(37), _p(40), _p(43), _p(256)), fill=(60, 50, 40, 255))
    d.rounded_rectangle((_p(24), _p(20), _p(56), _p(46)), radius=_p(6), fill=(255, 226, 150, 255))
    return img, w, h


def prop_book(t):
    w, h = 150, 110
    img, d = _patch(w, h)
    d.polygon([(_p(14), _p(100)), (_p(74), _p(86)), (_p(74), _p(30)), (_p(14), _p(42))], fill=(236, 226, 200, 255))
    d.polygon([(_p(136), _p(100)), (_p(76), _p(86)), (_p(76), _p(30)), (_p(136), _p(42))], fill=(244, 236, 214, 255))
    d.polygon([(_p(40), _p(100)), (_p(110), _p(100)), (_p(100), _p(108)), (_p(50), _p(108))], fill=(110, 76, 44, 255))
    for i in range(4):
        a = 0.4 + 0.6 * abs(math.sin(t * 1.5 + i))
        d.ellipse((_p(58 + i * 12), _p(10 - i * 2), _p(64 + i * 12), _p(16 - i * 2)), fill=(255, 232, 160, int(150 * a)))
    return img, w, h


def prop_mat(t):
    w, h = 170, 60
    img, d = _patch(w, h)
    d.polygon([(_p(20), _p(52)), (_p(150), _p(52)), (_p(170), _p(12)), (_p(0), _p(12))], fill=(120, 40, 50, 255))
    d.pieslice((_p(62), _p(8), _p(108), _p(60)), 180, 360, fill=(236, 190, 110, 255))
    return img, w, h


def prop_heart(t):
    w, h = 100, 100
    img, d = _patch(w, h)
    pulse = 1 + 0.06 * math.sin(t * 4)
    c = (255, 200, 110, 255)
    r = 22 * pulse
    d.ellipse((_p(50 - r * 1.8), _p(38 - r), _p(50), _p(38 + r)), fill=c)
    d.ellipse((_p(50), _p(38 - r), _p(50 + r * 1.8), _p(38 + r)), fill=c)
    d.polygon([(_p(50 - r * 1.75), _p(46)), (_p(50 + r * 1.75), _p(46)), (_p(50), _p(88))], fill=c)
    return img, w, h


def prop_money(t):
    w, h = 130, 70
    img, d = _patch(w, h)
    for i, (x, y) in enumerate(((10, 40), (46, 34), (80, 40), (28, 22), (62, 18))):
        d.ellipse((_p(x), _p(y), _p(x + 36), _p(y + 22)), fill=(236, 188, 70, 255), outline=(180, 130, 40, 255), width=_p(2))
    return img, w, h


def prop_clock(t):
    w, h = 110, 120
    img, d = _patch(w, h)
    d.ellipse((_p(10), _p(10), _p(100), _p(100)), fill=(236, 228, 210, 255), outline=(120, 96, 60, 255), width=_p(4))
    a = t * 2.0
    d.line((_p(55), _p(55), _p(55 + 28 * math.sin(a)), _p(55 - 28 * math.cos(a))), fill=(40, 34, 28, 255), width=_p(3))
    d.line((_p(55), _p(55), _p(55 + 20 * math.sin(a / 12)), _p(55 - 20 * math.cos(a / 12))), fill=(40, 34, 28, 255), width=_p(4))
    return img, w, h


PROPS = {"gold": prop_gold, "car": prop_car, "house": prop_house, "mosque": prop_mosque, "tree": prop_tree, "sprout": prop_sprout,
         "plate": prop_plate, "gift": prop_gift, "stall": prop_stall, "phone": prop_phone, "door": prop_door, "dog": prop_dog,
         "lamp": prop_lamp, "book": prop_book, "mat": prop_mat, "heart": prop_heart, "money": prop_money, "clock": prop_clock}
FLOATING = {"heart": 90, "book": 0, "phone": 0, "clock": 40}


def draw_prop(dst, name, x_frac, t, alpha=1.0, scale=1.0):
    fn = PROPS.get(name)
    if fn is None:
        return
    patch, w, h = fn(t)
    lift = FLOATING.get(name, 0)
    y = HORIZON - lift + (math.sin(t * 2.0) * 5 if name == "heart" else 0)
    _blit(dst, patch, x_frac * W, y + 6, w, h, alpha, scale)


# ------------------------------------------------------------------ characters

KINDS = {"man": 1.0, "woman": 0.97, "child": 0.62, "elder": 0.95}


def draw_figure(dst, x, y_ground, pose, t, color, kind="man", scale=1.75, flip=False):
    """Stick-figure family: man, woman (hijab + long dress), child, elder (stooped, with a cane)."""
    pw, ph = 380, 420
    patch = Image.new("RGBA", (pw * S, ph * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(patch)
    ox, oy = pw * S / 2, (ph - 6) * S
    sc = scale * KINDS.get(kind, 1.0) * S
    swing = math.sin(t * 5.2) * 0.5 if pose == "walk" else (0.07 if pose != "slump" else 0.04)
    lean = {"walk": 0.04, "stand": 0.0, "slump": 0.42, "open": 0.0}[pose]
    if kind == "elder":
        lean += 0.22
        swing *= 0.6
    thigh, shin, torso, uarm, farm = 42, 42, 74, 30, 30
    hip = (ox, oy - (thigh + shin) * sc * 0.97 / S * S / S * S / S)
    hip = (ox, oy - (thigh + shin) * sc * 0.97)
    neck = (hip[0] + math.sin(lean) * torso * sc, hip[1] - math.cos(lean) * torso * sc)
    head_r = (15 if kind != "woman" else 16) * sc
    head_dir = lean + (0.18 if pose == "slump" else 0.0)
    head = (neck[0] + math.sin(head_dir) * (head_r + 3 * sc), neck[1] - math.cos(head_dir) * (head_r + 3 * sc))
    col = color + (255,)
    w = int(3.4 * sc / S * 1.0) + 2 if False else max(4, int(3.6 * sc / 1.0 * 0.5))

    def limb(origin, a1, l1, a2, l2):
        k = (origin[0] + math.sin(a1) * l1 * sc, origin[1] + math.cos(a1) * l1 * sc)
        e = (k[0] + math.sin(a2) * l2 * sc, k[1] + math.cos(a2) * l2 * sc)
        return k, e

    if kind == "woman":
        dress_w = 38 * sc
        d.polygon([(neck[0] - 7 * sc, neck[1] + 4 * sc), (neck[0] + 7 * sc, neck[1] + 4 * sc),
                   (ox + dress_w * 0.5 + swing * 18 * sc, oy), (ox - dress_w * 0.5 + swing * 18 * sc, oy)], fill=col)
    else:
        for sgn in (1, -1):
            a = swing * sgn
            kn, ft = limb(hip, a, thigh, a - max(0.0, -a) * 0.8, shin)
            d.line([hip, kn, ft], fill=col, width=w, joint="curve")
    d.line([hip, neck], fill=col, width=w)
    sh = (neck[0] - math.sin(lean) * 8 * sc, neck[1] + math.cos(lean) * 8 * sc)
    for sgn in (1, -1):
        if pose == "open":
            e1 = (sh[0] + sgn * uarm * sc * 0.95, sh[1] - uarm * sc * 0.18)
            e2 = (e1[0] + sgn * farm * sc * 0.95, e1[1] - farm * sc * 0.28)
        elif pose == "slump":
            e1 = (sh[0] + sgn * 3 * sc, sh[1] + uarm * sc)
            e2 = (e1[0] + sgn * 2 * sc, e1[1] + farm * sc * 0.9)
        else:
            ang = -swing * sgn * 0.9 + sgn * 0.12
            e1 = (sh[0] + math.sin(ang) * uarm * sc, sh[1] + math.cos(ang) * uarm * sc)
            e2 = (e1[0] + math.sin(ang * 0.6) * farm * sc, e1[1] + math.cos(ang * 0.6) * farm * sc)
        d.line([sh, e1, e2], fill=col, width=w, joint="curve")
        if kind == "elder" and sgn == 1:
            d.line([e2, (e2[0] + 10 * sc, oy)], fill=col, width=max(3, w - 1))
    d.ellipse((head[0] - head_r, head[1] - head_r, head[0] + head_r, head[1] + head_r), fill=col)
    if kind == "woman":
        d.pieslice((head[0] - head_r * 1.25, head[1] - head_r * 1.25, head[0] + head_r * 1.25, head[1] + head_r * 1.25), 150, 390, fill=col)
        d.polygon([(head[0] - head_r * 1.2, head[1]), (head[0] + head_r * 1.2, head[1]),
                   (neck[0] + 12 * sc, neck[1] + 18 * sc), (neck[0] - 12 * sc, neck[1] + 18 * sc)], fill=col)
    patch = patch.resize((pw, ph), Image.LANCZOS)
    if flip:
        patch = patch.transpose(Image.FLIP_LEFT_RIGHT)
    dst.alpha_composite(patch, (int(x - pw / 2), int(y_ground - ph + 6)))
