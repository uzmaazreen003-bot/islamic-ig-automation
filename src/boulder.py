"""Boulder dhikr reel: a figure keeps striking a huge stone with a hammer; each dhikr is one blow, one more
golden crack. After the last count the stone splits open and light pours out. Original artwork."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import audio, polish, stage, textkit, theme
from .tasbih import scale_alpha

W, H, FPS = 720, 1280, 30
GY = 1130                       # ground line
CX, CY, R = 505, 940, 195       # boulder
FX = 82                         # figure x
CYCLE = 2.0
T_HIT = 1.05                    # seconds into each cycle when the hammer lands
HAND = (1.0, 0.0)

BOULDER_THEMES = {
    "emerald": dict(top=(6, 18, 15), bot=(16, 36, 30), ground=(5, 13, 11), accent=(230, 196, 112), text=(240, 240, 228), glow=(255, 214, 120), stone=(98, 100, 94)),
    "maroon": dict(top=(26, 8, 12), bot=(52, 18, 24), ground=(18, 6, 9), accent=(240, 196, 140), text=(250, 238, 226), glow=(255, 196, 120), stone=(104, 94, 92)),
    "plum": dict(top=(20, 12, 28), bot=(42, 26, 50), ground=(13, 8, 19), accent=(238, 196, 140), text=(246, 236, 244), glow=(255, 206, 140), stone=(100, 94, 102)),
    "amber": dict(top=(26, 18, 10), bot=(54, 36, 18), ground=(16, 11, 7), accent=(255, 206, 130), text=(250, 240, 224), glow=(255, 190, 90), stone=(108, 98, 86)),
}


def _blob(rng, n=44):
    ph = rng.uniform(0, 6.28, 4)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + 0.05 * math.sin(3 * a + ph[0]) + 0.04 * math.sin(5 * a + ph[1]) + 0.025 * math.sin(9 * a + ph[2])
        pts.append((R * 1.0 * k * math.cos(a), R * 1.06 * k * math.sin(a)))
    return pts


def _stone_sprite(th, rng):
    S = 2 * (R + 30)
    sp = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mask = Image.new("L", (S, S), 0)
    pts = [(S / 2 + x, S / 2 + y) for x, y in _blob(rng)]
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    lit = np.clip(1.0 - (np.hypot(xx - S * 0.36, yy - S * 0.30) / (S * 0.85)), 0, 1) ** 0.9
    base = np.array(th["stone"], np.float32)
    shade = (0.45 + 0.75 * lit)[..., None]
    arr = np.clip(base * shade + rng.normal(0, 4.0, (S, S, 1)), 0, 255).astype(np.uint8)
    img = Image.fromarray(np.dstack([arr, np.full((S, S), 255, np.uint8)]), "RGBA")
    d = ImageDraw.Draw(img)
    for _ in range(90):                                      # speckles
        x, y = rng.uniform(0, S), rng.uniform(0, S)
        r = rng.uniform(1.5, 5)
        c = int(rng.integers(-24, 20))
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(max(0, min(255, v + c)) for v in th["stone"]) + (120,))
    sp.paste(img, (0, 0), mask)
    return sp, mask, S


def _cracks(rng, n, S):
    """n polylines growing from the impact point (left side of the stone), spreading across it."""
    ox, oy = S / 2 - R * 0.97, S / 2 + 6
    cr, tips = [], [(ox, oy, 0.0)]
    for i in range(n):
        sx, sy, ang = tips[int(rng.integers(0, len(tips)))]
        ang = ang + rng.uniform(-0.9, 0.9) if i else 0.0
        pts = [(sx, sy)]
        x, y = sx, sy
        for _ in range(int(rng.integers(4, 8))):
            ang += rng.uniform(-0.55, 0.55)
            step = rng.uniform(22, 40)
            x, y = x + math.cos(ang) * step, y + math.sin(ang) * step
            if math.hypot(x - S / 2, y - S / 2) > R * 0.94:
                break
            pts.append((x, y))
        if len(pts) > 1:
            cr.append(pts)
            tips.append((pts[-1][0], pts[-1][1], ang))
            if len(pts) > 3:
                tips.append((pts[len(pts) // 2][0], pts[len(pts) // 2][1], ang + rng.choice([-1, 1]) * 0.8))
    return cr


def _thud(rng):
    t = np.arange(int(0.55 * audio.SR)) / audio.SR
    f = 62 * np.exp(-t * 4.5) + 38
    body = np.sin(2 * math.pi * np.cumsum(f) / audio.SR) * np.exp(-t * 7.0)
    click = rng.normal(0, 1, len(t)) * np.exp(-t * 60.0) * 0.35
    tink = np.sin(2 * math.pi * 1180 * t) * np.exp(-t * 22.0) * 0.12
    return ((body + click + tink) * 0.55).astype(np.float32)


def _shatter(rng):
    t = np.arange(int(2.6 * audio.SR)) / audio.SR
    n = rng.normal(0, 1, len(t)) * np.exp(-t * 5.0) * 0.25
    chime = sum(np.sin(2 * math.pi * f * t) * np.exp(-t * (1.1 + i * 0.3)) * (0.11 / (i + 1)) for i, f in enumerate((523, 784, 1047, 1568)))
    return (n + chime).astype(np.float32)


def make_reel(item, handle, out_path, seed=0, workdir=".", count=33, theme_name="emerald", cycle=2.0):
    th = BOULDER_THEMES[theme_name]
    rng = np.random.default_rng(seed)
    sprite, mask, S = _stone_sprite(th, rng)
    cracks = _cracks(rng, count, S)
    bg = theme.gradient(W, H, th["top"], th["bot"]).convert("RGBA")
    d = ImageDraw.Draw(bg)
    for _ in range(40):
        x, y, r = rng.uniform(0, W), rng.uniform(10, 640), rng.uniform(0.6, 1.6)
        d.ellipse((x - r, y - r, x + r, y + r), fill=th["glow"] + (int(rng.integers(40, 130)),))
    d.rectangle((0, GY, W, H), fill=th["ground"] + (255,))
    d.line((0, GY, W, GY), fill=th["accent"] + (60,), width=1)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((CX - R * 0.95, GY - 22, CX + R * 0.95, GY + 26), fill=(0, 0, 0, 120))
    bg.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))

    # fixed text
    head = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dh = ImageDraw.Draw(head)
    fa, la, lha = textkit.fit(item["ar"], theme.arabic, 600, 150, 74, 40, line_gap=1.5, rtl=True)
    ya = textkit.draw_block(dh, W / 2, 110, la, fa, th["text"], lha, rtl=True)
    dh.text((W / 2, ya + 46), item["tr"], font=theme.poppins("medium", 30), fill=th["text"] + (255,), anchor="mt")
    dh.text((W / 2, ya + 94), item["en"], font=theme.poppins("light", 22), fill=th["text"] + (170,), anchor="mt")
    y_num, y_bar = ya + 150, ya + 232
    foot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    theme.spaced(ImageDraw.Draw(foot), (W / 2, 1196), "RUH CORNER", theme.poppins("medium", 18), th["accent"], spacing=6)
    ImageDraw.Draw(foot).text((W / 2, 1226), handle, font=theme.poppins("light", 16), fill=th["text"] + (120,), anchor="ma")

    f = cycle / CYCLE
    t0, t_end_hits = 1.5, 1.5 + count * cycle
    t_split = t_end_hits - cycle + T_HIT * f + 0.35
    total = t_split + 7.0
    hits = [t0 + k * cycle + T_HIT * f for k in range(count)]
    events = [(h, _thud(rng)) for h in hits] + [(t_split, _shatter(rng)), (t_split + 0.2, audio.bowl(432, 4.0, 0.12))]
    wav = f"{workdir}/boulder-audio.wav"
    audio.mix(events, total, wav, seed=seed, extra=audio.pad(total, 98.0, 0.04))

    stone_cache = {}

    def stone(nc, glow_amt):
        key = (nc, round(glow_amt * 8))
        if key in stone_cache:
            return stone_cache[key]
        im = sprite.copy()
        lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        gl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        dg = ImageDraw.Draw(gl)
        bright = 0.35 + 0.65 * min(1.0, nc / count) + glow_amt
        for pts in cracks[:nc]:
            dl.line(pts, fill=(14, 10, 8, 255), width=7, joint="curve")
            dg.line(pts, fill=th["glow"] + (int(min(255, 150 * bright)),), width=9, joint="curve")
            dl.line(pts, fill=th["accent"] + (int(min(255, 255 * bright)),), width=3, joint="curve")
        if nc:
            im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(7)))
            im.alpha_composite(lay)
        im.putalpha(ImageChops_min(im.getchannel("A"), mask))
        stone_cache[key] = im
        return im

    def ImageChops_min(a, b):
        from PIL import ImageChops
        return ImageChops.darker(a, b)

    def phi_at(c):                                       # hammer angle (radians, 0 = horizontal forward)
        c = c / f
        if c < 0.8:
            e = 0.5 - 0.5 * math.cos(math.pi * c / 0.8)
            return math.radians(-30 - 105 * e)
        if c < T_HIT:
            e = ((c - 0.8) / (T_HIT - 0.8)) ** 1.6
            return math.radians(-135 + 135 * e)
        if c < T_HIT + 0.12:
            return 0.0
        e = min(1.0, (c - T_HIT - 0.12) / (CYCLE - T_HIT - 0.12))
        e = 0.5 - 0.5 * math.cos(math.pi * e)
        return math.radians(-30 * e)

    def figure(fr, phi, tired):
        dd = ImageDraw.Draw(fr)
        col = (236, 228, 208, 255)
        hip = (FX, GY - 104)
        neck = (FX + 6, hip[1] - 92)
        head = (neck[0] + 4, neck[1] - 30)
        dd.line([hip, neck], fill=col, width=10)
        dd.ellipse((head[0] - 26, head[1] - 26, head[0] + 26, head[1] + 26), fill=col)
        for sgn, sw in ((1, 20), (-1, -26)):               # legs, planted wide
            kn = (hip[0] + sgn * 20 + sw * 0.2, hip[1] + 54)
            fo = (hip[0] + sgn * 30 + sw * 0.4, GY)
            dd.line([hip, kn, fo], fill=col, width=10, joint="curve")
        sh = (neck[0], neck[1] + 10)
        d_ = (math.cos(phi), math.sin(phi))
        hand = (sh[0] + 62 * d_[0], sh[1] + 62 * d_[1] + 10)
        elbow = (sh[0] + 34 * d_[0] - 8, sh[1] + 34 * d_[1] + 24)
        dd.line([sh, elbow, hand], fill=col, width=9, joint="curve")
        tail = (hand[0] - 28 * d_[0], hand[1] - 28 * d_[1])
        tip = (hand[0] + 142 * d_[0], hand[1] + 142 * d_[1])
        dd.line([tail, tip], fill=(176, 130, 80, 255), width=9)
        nx, ny = -d_[1], d_[0]
        c0 = (tip[0] + d_[0] * 6, tip[1] + d_[1] * 6)
        poly = [(c0[0] + nx * 30 - d_[0] * 18, c0[1] + ny * 30 - d_[1] * 18), (c0[0] + nx * 30 + d_[0] * 18, c0[1] + ny * 30 + d_[1] * 18),
                (c0[0] - nx * 30 + d_[0] * 18, c0[1] - ny * 30 + d_[1] * 18), (c0[0] - nx * 30 - d_[0] * 18, c0[1] - ny * 30 - d_[1] * 18)]
        dd.polygon(poly, fill=(150, 158, 168, 255))
        dd.line([poly[0], poly[1], poly[2], poly[3], poly[0]], fill=(214, 220, 228, 255), width=2)

    sparks_rng = np.random.default_rng(seed + 11)
    spark_set = {k: [(sparks_rng.uniform(-0.9, 0.9), sparks_rng.uniform(-1.2, -0.1), sparks_rng.uniform(2, 4.5)) for _ in range(12)] for k in range(count)}
    cache = {}

    def lay(key, layer, a):
        q = round(max(0, min(1, a)) * 12) / 12
        if q <= 0:
            return None
        if (key, q) not in cache:
            cache[(key, q)] = scale_alpha(layer, q)
        return cache[(key, q)]

    def frames():
        for fi in range(int(total * FPS)):
            tm = fi / FPS
            fr = bg.copy()
            done = sum(1 for h in hits if tm >= h)
            splitting = tm >= t_split
            # glow behind the stone grows with the count
            gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ga = int(18 + 80 * (done / count) ** 1.5 + ((70 * min(1.0, (tm - t_split) / 1.2) * (1.0 - 0.6 * min(1.0, max(0.0, (tm - t_split - 2.0) / 3.0)))) if splitting else 0))
            r = R + 70 + (90 * min(1.0, max(0.0, (tm - t_split) / 2.0)) if splitting else 0)
            ImageDraw.Draw(gl).ellipse((CX - r, CY - r, CX + r, CY + r), fill=th["glow"] + (min(255, ga),))
            fr.alpha_composite(gl.filter(ImageFilter.GaussianBlur(60)))
            # shake
            shake = 0.0
            last = max([h for h in hits if tm >= h], default=None)
            if last is not None and tm - last < 0.4:
                shake = 7 * math.exp(-(tm - last) * 11) * math.sin((tm - last) * 55)
            cam = (shake * 0.5, -abs(shake) * 0.4)
            glow_amt = min(1.0, (tm - t_split) / 1.0) * 0.8 if splitting else 0.0
            st = stone(done, glow_amt)
            if not splitting:
                fr.alpha_composite(st, (int(CX - S / 2 + shake), int(CY - S / 2)))
            else:
                e = min(1.0, (tm - t_split) / 2.2)
                e = 1 - (1 - e) ** 3
                half = Image.new("L", (S, S), 0)
                ImageDraw.Draw(half).polygon([(0, 0), (S / 2 + 30, 0), (S / 2 - 20, S), (0, S)], fill=255)
                left, right = st.copy(), st.copy()
                from PIL import ImageChops
                left.putalpha(ImageChops.multiply(st.getchannel("A"), half))
                right.putalpha(ImageChops.multiply(st.getchannel("A"), ImageChops.invert(half)))
                fade = max(0.0, 1.0 - max(0.0, tm - t_split - 2.2) / 2.0)
                fr.alpha_composite(scale_alpha(left, fade), (int(CX - S / 2 - 70 * e), int(CY - S / 2 + 6 * e)))
                fr.alpha_composite(scale_alpha(right, fade), (int(CX - S / 2 + 70 * e), int(CY - S / 2 + 10 * e)))
                # rising light pillar
                pil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                pw = 24 + 70 * e
                ImageDraw.Draw(pil).polygon([(CX - pw, CY + 40), (CX + pw, CY + 40), (CX + pw * 2.4, 0), (CX - pw * 2.4, 0)], fill=th["glow"] + (int(80 * e * fade),))
                fr.alpha_composite(pil.filter(ImageFilter.GaussianBlur(22)))
            # cycle
            if tm < t0:
                phi, k = math.radians(-30), -1
            elif not splitting:
                k = min(count - 1, int((tm - t0) // cycle))
                phi = phi_at((tm - t0) - k * cycle)
            else:
                phi = math.radians(-30)
            figure(fr, phi, 0)
            # sparks at the last hit
            if last is not None and not splitting and tm - last < 0.7 * min(1.0, f + 0.2):
                kk = hits.index(last)
                dd = ImageDraw.Draw(fr)
                el = tm - last
                for vx, vy, rr in spark_set[kk]:
                    x = CX - R * 0.97 + vx * 150 * el
                    y = CY + 6 + (vy * 190 * el + 330 * el * el)
                    dd.ellipse((x - rr, y - rr, x + rr, y + rr), fill=th["glow"] + (int(255 * (1 - el / 0.7)),))
            if last is not None and tm - last < 0.9 and not splitting:
                el = (tm - last) / 0.9
                pf = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                pd = ImageDraw.Draw(pf)
                for j in range(6):
                    px = CX - R * 0.9 + (j - 2.5) * 34 * (1 + el) - 40 * el
                    pr = 16 + 40 * el
                    pd.ellipse((px - pr, GY - pr * 0.7 - 20 * el, px + pr, GY + pr * 0.3), fill=th["accent"] + (int(70 * (1 - el)),))
                fr.alpha_composite(pf.filter(ImageFilter.GaussianBlur(8)))
            fr.alpha_composite(head)
            dd = ImageDraw.Draw(fr)
            shown = min(count, done)
            dd.text((W / 2, y_num), str(shown), font=theme.poppins("bold", 54), fill=th["accent"] + (255,), anchor="mt")
            dd.line([(60, y_bar), (W - 60, y_bar)], fill=(255, 255, 255, 40), width=4)
            dd.line([(60, y_bar), (60 + (W - 120) * shown / count, y_bar)], fill=th["accent"] + (255,), width=4)
            dd.text((W - 60, y_bar + 14), f"{shown} / {count}", font=theme.poppins("light", 18), fill=th["text"] + (150,), anchor="ra")
            fr.alpha_composite(foot)
            out = fr.convert("RGB")
            fade = min(1.0, tm / 0.8 + 0.001, (total - tm) / 1.0)
            if fade < 1.0:
                out = Image.blend(Image.new("RGB", (W, H), th["top"]), out, max(0.0, fade))
            yield polish.finish(out, tm, total, shake=cam, fi=fi)

    audio.encode_video(frames(), W, H, FPS, wav, out_path)
    return dict(total=round(total, 1), count=count)
