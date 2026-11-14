"""'World' dhikr reels: every dhikr changes the picture a little. The world slowly goes from bare to alive.
Three original scenes: oasis (dry land -> garden), lanterns (dark village -> every window lit), dawn (night -> sunrise)."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import audio, polish, textkit, theme
from .tasbih import scale_alpha

W, H, FPS = 720, 1280, 30
CYCLE, T_HIT = 2.0, 1.2


def mix(a, b, t):
    return tuple(float(a[i] + (b[i] - a[i]) * t) for i in range(3))


def grad(top, bot, y0=0, y1=H):
    t = np.linspace(0, 1, y1 - y0, dtype=np.float32)[:, None, None]
    arr = np.array(top, np.float32) * (1 - t) + np.array(bot, np.float32) * t
    return np.repeat(arr, W, axis=1)


def canvas_from(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


# ---------------------------------------------------------------- scenes (all take p in 0..1)

class Oasis:
    accent = (255, 224, 160)
    target = (360, 900)

    def __init__(self, rng):
        self.trees = [(rng.uniform(40, 680), rng.uniform(0.08, 0.85), rng.uniform(0.8, 1.2), rng.uniform(-0.3, 0.3)) for _ in range(9)]
        self.flowers = [(rng.uniform(10, 710), rng.uniform(960, 1180), rng.uniform(0.15, 0.97), rng.choice([0, 1, 2])) for _ in range(110)]
        self.cracks = [[(x, y), (x + rng.uniform(-40, 40), y + rng.uniform(20, 50)), (x + rng.uniform(-70, 70), y + rng.uniform(60, 110))] for x, y in
                       ((rng.uniform(0, 720), rng.uniform(900, 1250)) for _ in range(34))]
        self.rng = np.random.default_rng(3)

    def draw(self, p, tm, ripples):
        sky = grad(mix((74, 52, 46), (252, 214, 168), p ** 0.8), mix((158, 98, 62), (255, 238, 208), p), 0, 880)
        gnd = grad(mix((126, 92, 62), (92, 150, 72), p), mix((96, 70, 48), (64, 120, 56), p), 880, H)
        img = canvas_from(np.concatenate([sky, gnd], axis=0))
        d = ImageDraw.Draw(img, "RGBA")
        sun_a = int(60 + 195 * p)
        d.ellipse((520 - 70, 300 - 70, 520 + 70, 300 + 70), fill=(255, 236, 190, sun_a))
        for cx0, cy0, cs in ((90, 190, 1.0), (430, 120, 1.3), (640, 250, 0.8)):
            cx = (cx0 + tm * 9 * cs) % 900 - 90
            d.ellipse((cx - 70 * cs, cy0 - 20 * cs, cx + 70 * cs, cy0 + 22 * cs), fill=(255, 244, 226, int(90 + 60 * p)))
            d.ellipse((cx - 30 * cs, cy0 - 36 * cs, cx + 50 * cs, cy0 + 12 * cs), fill=(255, 244, 226, int(90 + 60 * p)))
        hill = mix((70, 50, 42), (132, 160, 104), p)
        d.polygon([(0, 880), (0, 740), (140, 690), (300, 760), (460, 680), (620, 740), (720, 700), (720, 880)], fill=tuple(int(v) for v in hill) + (255,))
        for pts in self.cracks:
            d.line(pts, fill=(50, 34, 24, int(150 * (1 - p) ** 1.2)), width=2)
        pw, ph = 70 + 250 * p, 22 + 74 * p                           # pool
        d.ellipse((360 - pw - 10, 900 - ph - 6, 360 + pw + 10, 900 + ph + 6), fill=(120, 100, 80, 255))
        d.ellipse((360 - pw, 900 - ph, 360 + pw, 900 + ph), fill=tuple(int(v) for v in mix((86, 110, 96), (74, 168, 156), p)) + (255,))
        for (age, amp) in ripples:
            r = 14 + 130 * age
            d.ellipse((360 - r, 900 - r * 0.36, 360 + r, 900 + r * 0.36), outline=(235, 250, 245, int(200 * (1 - age))), width=3)
        for x, thr, sc, lean in sorted(self.trees, key=lambda t: t[0]):
            g = (p - thr) / 0.16
            base_y = 905 + (x % 90)
            if g <= 0:                                               # bare dead branches
                d.line([(x, base_y), (x + 6, base_y - 50)], fill=(60, 44, 34, 255), width=4)
                d.line([(x + 4, base_y - 30), (x - 16, base_y - 52)], fill=(60, 44, 34, 255), width=3)
                continue
            g = min(1.0, g)
            h = 60 + 190 * g * sc
            top = (x + lean * h + 7 * math.sin(tm * 1.4 + x), base_y - h)
            d.line([(x, base_y), ((x + top[0]) / 2 + 8, base_y - h * 0.5), top], fill=(96, 66, 40, 255), width=int(5 + 4 * g), joint="curve")
            if g > 0.35:
                f = min(1.0, (g - 0.35) / 0.5)
                for k in range(7):
                    a = -math.pi + k * math.pi / 6
                    L = 70 * f * sc
                    d.line([top, (top[0] + math.cos(a) * L, top[1] + math.sin(a) * L * 0.55 + L * 0.35)], fill=mix((86, 126, 60), (56, 140, 70), p) + (255,) if False else (64, 140, 68, 255), width=6)
        for x, y, thr, c in self.flowers:
            if p > thr:
                s = min(1.0, (p - thr) / 0.06)
                col = ((250, 170, 190), (255, 246, 230), (255, 214, 96))[c] + (255,)
                d.ellipse((x - 4 * s, y - 4 * s, x + 4 * s, y + 4 * s), fill=col)
        haze = Image.new("RGBA", (W, H), (30, 18, 14, int(110 * (1 - p) ** 1.5)))
        img.paste(haze, (0, 0), haze)
        return img


class Lanterns:
    accent = (255, 214, 140)
    target = (360, 880)

    def __init__(self, rng, count=33):
        self.houses, x = [], -10
        while x < W:
            w = int(rng.integers(90, 150))
            self.houses.append((x, w, int(rng.integers(140, 260))))
            x += w + int(rng.integers(6, 24))
        wins = []
        for hx, hw, hh in self.houses:
            for wx in range(hx + 16, hx + hw - 30, 40):
                for wy in range(1000 - hh + 24, 990, 56):
                    wins.append((wx, wy))
        order = rng.permutation(len(wins))
        self.wins = [wins[i] for i in order]
        self.count = count
        self.stars = [(rng.uniform(0, W), rng.uniform(40, 700), rng.uniform(0.0, 1.0), rng.uniform(1, 2.6)) for _ in range(90)]
        self.target = None

    def draw(self, p, tm, ripples):
        sky = grad(mix((8, 6, 14), (66, 36, 40), p), mix((22, 16, 26), (190, 110, 60), p ** 1.2), 0, 1000)
        gnd = grad((12, 9, 10), (20, 14, 12), 1000, H)
        img = canvas_from(np.concatenate([sky, gnd], axis=0))
        d = ImageDraw.Draw(img, "RGBA")
        for x, y, thr, r in self.stars:
            if p >= thr * 0.9:
                d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 240, 210, int(110 + 100 * math.sin(tm * 2 + x))))
        if p > 0.55:
            a = min(1.0, (p - 0.55) / 0.3)
            d.ellipse((560 - 52, 250 - 52, 560 + 52, 250 + 52), fill=(255, 238, 200, int(255 * a)))
        for hx, hw, hh in self.houses:
            d.rectangle((hx, 1000 - hh, hx + hw, 1000), fill=(14, 10, 10, 255))
            d.polygon([(hx - 8, 1000 - hh), (hx + hw / 2, 1000 - hh - 46), (hx + hw + 8, 1000 - hh)], fill=(14, 10, 10, 255))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dg = ImageDraw.Draw(glow)
        lit = int(round(p * len(self.wins)))
        for i, (wx, wy) in enumerate(self.wins):
            if i < lit:
                dg.ellipse((wx - 26, wy - 26, wx + 46, wy + 52), fill=(255, 190, 90, 90))
        img.paste(glow.filter(ImageFilter.GaussianBlur(14)), (0, 0), glow.filter(ImageFilter.GaussianBlur(14)))
        d = ImageDraw.Draw(img, "RGBA")
        for i, (wx, wy) in enumerate(self.wins):
            on = i < lit
            d.rectangle((wx, wy, wx + 22, wy + 32), fill=((255, int(204 + 14 * math.sin(tm * 5 + wx)), 126, 255) if on else (30, 22, 20, 255)))
        return img


class Dawn:
    accent = (255, 214, 150)
    target = (360, 760)

    def __init__(self, rng):
        self.birds = [(rng.uniform(60, 660), rng.uniform(300, 640), rng.uniform(0.5, 0.95), rng.uniform(0.5, 1.2)) for _ in range(9)]
        self.ridges = []
        for k in range(4):
            ph, am = rng.uniform(0, 6), rng.uniform(40, 90)
            self.ridges.append([(x, 900 - k * 60 - am * (0.5 + 0.5 * math.sin(x / (110 + 30 * k) + ph))) for x in range(0, W + 20, 20)])

    def draw(self, p, tm, ripples):
        sky = grad(mix((18, 12, 28), (250, 190, 150), p ** 0.9), mix((50, 30, 52), (255, 232, 190), p), 0, 1000)
        gnd = grad((16, 12, 14), (30, 22, 20), 1000, H)
        img = canvas_from(np.concatenate([sky, gnd], axis=0))
        sy = 980 - 560 * p
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((360 - 260, sy - 260, 360 + 260, sy + 260), fill=(255, 196, 120, int(40 + 120 * p)))
        img.paste(glow.filter(ImageFilter.GaussianBlur(70)), (0, 0), glow.filter(ImageFilter.GaussianBlur(70)))
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse((360 - 64, sy - 64, 360 + 64, sy + 64), fill=(255, 240, 200, 255))
        for k, pts in reversed(list(enumerate(self.ridges))):
            col = mix(mix((10, 8, 14), (26, 18, 28), 1 - k / 4), mix((150, 96, 80), (222, 160, 110), 1 - k / 4), p)
            d.polygon(pts + [(W, 1000), (0, 1000)], fill=tuple(int(v) for v in col) + (255,))
        d.rectangle((0, 1000, W, H), fill=(26, 19, 18, 255))
        for x, y, thr, s in self.birds:
            if p > thr:
                a = min(1.0, (p - thr) / 0.05)
                wob = math.sin(tm * 6 + x) * 5 * s
                x = (x + tm * 18 * s) % 760 - 20
                d.line([(x - 16 * s, y + wob), (x, y - 6 * s), (x + 16 * s, y + wob)], fill=(40, 28, 26, int(255 * a)), width=3, joint="curve")
        if p > 0.8:
            rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dr = ImageDraw.Draw(rays)
            for k in range(7):
                a = -math.pi / 2 + (k - 3) * 0.26
                dr.polygon([(360, sy), (360 + math.cos(a - 0.05) * 900, sy + math.sin(a - 0.05) * 900), (360 + math.cos(a + 0.05) * 900, sy + math.sin(a + 0.05) * 900)], fill=(255, 226, 170, int(60 * (p - 0.8) / 0.2)))
            img.paste(rays.filter(ImageFilter.GaussianBlur(10)), (0, 0), rays.filter(ImageFilter.GaussianBlur(10)))
        return img


SCENES = {"oasis": Oasis, "lanterns": Lanterns, "dawn": Dawn}


def _drop(rng):
    t = np.arange(int(0.7 * audio.SR)) / audio.SR
    f = 900 + 500 * np.exp(-t * 18)
    return (np.sin(2 * math.pi * np.cumsum(f) / audio.SR) * np.exp(-t * 9) * 0.22 + rng.normal(0, 1, len(t)) * np.exp(-t * 80) * 0.05).astype(np.float32)


def make_reel(item, handle, out_path, seed=0, workdir=".", count=33, cycle=2.0):
    rng = np.random.default_rng(seed)
    scene = SCENES[item["scene"]](np.random.default_rng(seed + 7))
    if isinstance(scene, Lanterns):
        scene.count = count
    # fixed overlay: dark top fade, Arabic, transliteration, meaning
    top = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    arr = np.zeros((H, W, 4), np.uint8)
    arr[:560, :, 3] = (np.clip(1 - np.arange(560) / 560, 0, 1) ** 1.2 * 170).astype(np.uint8)[:, None]
    top = Image.fromarray(arr, "RGBA")
    dh = ImageDraw.Draw(top)
    fa, la, lha = textkit.fit(item["ar"], theme.arabic, 600, 140, 72, 40, line_gap=1.5, rtl=True)
    ya = textkit.draw_block(dh, W / 2, 96, la, fa, (252, 246, 232), lha, rtl=True)
    dh.text((W / 2, ya + 46), item["tr"], font=theme.poppins("medium", 28), fill=(252, 246, 232, 255), anchor="mt")
    dh.text((W / 2, ya + 90), item["en"], font=theme.poppins("light", 21), fill=(252, 246, 232, 190), anchor="mt")
    y_num, y_bar = ya + 140, ya + 214
    foot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    theme.spaced(ImageDraw.Draw(foot), (W / 2, 1204), "RUH CORNER", theme.poppins("medium", 18), (255, 240, 214), spacing=6)
    ImageDraw.Draw(foot).text((W / 2, 1234), handle, font=theme.poppins("light", 16), fill=(255, 240, 214, 170), anchor="ma")
    t0 = 1.5
    hits = [t0 + k * cycle + T_HIT * cycle / CYCLE for k in range(count)]
    total = hits[-1] + 7.0
    events = [(h, _drop(rng)) for h in hits] + [(hits[-1] + 0.3, audio.bowl(432, 4.0, 0.13))]
    wav = f"{workdir}/world-audio.wav"
    audio.mix(events, total, wav, seed=seed, extra=audio.pad(total, 98.0, 0.04))
    end_a = hits[-1] + 3.0
    closing = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fc, lc, lhc = textkit.fit(item.get("closing", "One by one, the light came back."), lambda s: theme.lora(s), 600, 200, 48, 32, line_gap=1.3)
    textkit.draw_block(ImageDraw.Draw(closing), W / 2, 760, lc, fc, (255, 248, 236), lhc)
    mrng = np.random.default_rng(seed + 21)
    motes = [(mrng.uniform(0, W), mrng.uniform(0, 1100), mrng.uniform(0, 6.28), mrng.uniform(0.4, 1.6), mrng.uniform(1.4, 3.2)) for _ in range(46)]
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
            done = sum(1 for h in hits if tm >= h)
            last = hits[done - 1] if done else None
            frac = 0.0 if last is None else min(1.0, (tm - last) / (0.55 * cycle))
            frac = frac * frac * (3 - 2 * frac)
            p = min(1.0, (max(0, done - 1) + (frac if done else 0.0)) / (count - 1)) if done else 0.0
            p = min(1.0, p)
            ripples = [((tm - h) / 1.3, 1) for h in hits if 0 <= tm - h < 1.3]
            img = scene.draw(p, tm, ripples)
            fr = img.convert("RGBA")
            # the falling light drop that lands on the world a moment before each count
            nxt = next((h for h in hits if h > tm), None)
            fall = 0.6 * cycle
            if nxt is not None and nxt - tm < fall:
                u = 1 - (nxt - tm) / fall
                tx, ty = (scene.target if scene.target else (360, 880))
                y = 560 + (ty - 560) * (u * u)
                dd = ImageDraw.Draw(fr)
                for k in range(5):
                    dd.ellipse((tx - 7 + k * 0.0, y - 12 - k * 11, tx + 7, y + 4 - k * 11), fill=scene.accent + (int(240 - 40 * k),))
            dd = ImageDraw.Draw(fr)
            for (fx, fy, fph, fsp, fr_) in motes:
                x = (fx + math.sin(tm * 0.6 + fph) * 28 + tm * fsp * 6) % W
                y = (fy - tm * fsp * 9) % 1100 + 120
                a = int(200 * (0.5 + 0.5 * math.sin(tm * 2.2 + fph)) * (0.25 + 0.75 * min(1.0, p + 0.2)))
                dd.ellipse((x - fr_, y - fr_, x + fr_, y + fr_), fill=scene.accent + (a,))
            fr.alpha_composite(top)
            dd = ImageDraw.Draw(fr)
            dd.text((W / 2, y_num), str(done), font=theme.poppins("bold", 52), fill=(255, 236, 190, 255), anchor="mt")
            dd.line([(60, y_bar), (W - 60, y_bar)], fill=(255, 255, 255, 60), width=4)
            dd.line([(60, y_bar), (60 + (W - 120) * done / count, y_bar)], fill=(255, 224, 160, 255), width=4)
            dd.text((W - 60, y_bar + 14), f"{done} / {count}", font=theme.poppins("light", 18), fill=(255, 255, 255, 170), anchor="ra")
            x = lay("close", closing, (tm - end_a) / 1.2)
            if x is not None:
                fr.alpha_composite(x)
            fr.alpha_composite(foot)
            out = fr.convert("RGB")
            fade = min(1.0, tm / 0.8 + 0.001, (total - tm) / 1.0)
            if fade < 1.0:
                out = Image.blend(Image.new("RGB", (W, H), (10, 8, 8)), out, max(0.0, fade))
            yield polish.finish(out, tm, total, fi=fi)

    audio.encode_video(frames(), W, H, FPS, wav, out_path)
    return dict(total=round(total, 1), count=count)
