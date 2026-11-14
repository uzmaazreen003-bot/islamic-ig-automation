"""Topic explainer reel (e.g. "Rizq, explained slowly"): chapters with an animated picture, a spoken line,
and a verbatim ayah / hadith quote. Each chapter has its own colour tint."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import audio, narrate, polish, stage, textkit, theme
from .tasbih import scale_alpha

W, H, FPS = stage.W, stage.H, 30
TINTS = {"gold": ((236, 190, 112), (255, 226, 160)), "rose": ((240, 150, 140), (255, 196, 180)), "jade": ((150, 220, 180), (200, 255, 226)),
         "violet": ((210, 170, 235), (232, 205, 250)), "amber": ((255, 170, 90), (255, 206, 150))}
serif = lambda s: theme.font("Amiri-Regular.ttf", s)       # noqa: E731


def _th(base, tint, kind="sil"):
    acc, glow = TINTS[tint]
    return stage.sil_theme(dict(base, accent=acc, glow=glow))


# ------------------------------------------------------------------ pictures

def _person(img, th, kind, x, pose, tm, scale=1.0, face=1, role="main"):
    p, ax, ay, _ = stage.person(kind, x, pose, tm, th, role, face, scale)
    img.alpha_composite(p, (int(x - ax), stage.GROUND - ay + 4))


def _rays(img, th, x, top, bot, width_top, width_bot, a):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).polygon([(x - width_top, top), (x + width_top, top), (x + width_bot, bot), (x - width_bot, bot)], fill=th["glow"] + (a,))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(14)))


def _sparks(img, th, x, tm, n=16, fall=True, spread=130, top=120, bot=None, seed=1):
    bot = bot or stage.GROUND - 20
    rng = np.random.default_rng(seed)
    d = ImageDraw.Draw(img)
    for i in range(n):
        ph, sp, ox, r = rng.uniform(0, 1), rng.uniform(25, 55), rng.uniform(-spread, spread), rng.uniform(2, 4.5)
        y = top + ((ph * (bot - top) + (tm * sp if fall else -tm * sp)) % (bot - top))
        al = int(230 * math.sin(math.pi * (y - top) / (bot - top)))
        d.ellipse((x + ox - r, y - r, x + ox + r, y + r), fill=th["glow"] + (max(0, al),))


def _label(d, th, x, y, text, a=255):
    d.text((x, y), text, font=theme.poppins("light", 22), fill=th["text"] + (a,), anchor="mt")


def _cloud(img, th, cx, cy, s=1.0):
    d = ImageDraw.Draw(img)
    col = stage.lerp(th["bot"], th["text"], 0.30) + (255,)
    for dx, dy, r in ((-70, 6, 46), (-18, -22, 58), (42, -6, 50), (88, 14, 36), (0, 22, 56)):
        d.ellipse((cx + (dx - r) * s, cy + (dy - r) * s, cx + (dx + r) * s, cy + (dy + r) * s), fill=col)


def draw_icon(icon, img, th, tm, u):
    """u = progress through the chapter (0..1)."""
    G = stage.GROUND
    d = ImageDraw.Draw(img)
    fade = lambda t0: max(0.0, min(1.0, (tm - t0) / 0.7))      # noqa: E731
    if icon in ("intro", "intro_s"):
        rng = np.random.default_rng(4)
        _person(img, th, "man", 360, "sit" if icon == "intro" else "slump", tm, 1.05)
        if icon == "intro":
            for i in range(16):
                ph, sp, ox = rng.uniform(0, 1), rng.uniform(70, 120), rng.uniform(-200, 200)
                y = 120 + ((ph * 520 + tm * sp) % 520)
                r = 14
                d.ellipse((360 + ox - r, y - r * 0.5, 360 + ox + r, y + r * 0.5), fill=th["accent"] + (230,))
            stage.draw_prop(img, "coins", 0.78, th, 0.9)
        else:
            _sparks(img, th, 360, tm, 10, fall=False, spread=60, top=200, bot=G - 120, seed=5)
    elif icon in ("four", "four_s"):
        names = ("health", "family", "peace of mind", "your next breath") if icon == "four" else ("hurt", "tears", "waiting", "still standing")
        spots = ((0.27, 0.19), (0.73, 0.19), (0.27, 0.40), (0.73, 0.40))
        for i, (sx, sy) in enumerate(spots):
            a = fade(0.6 + i * 1.3)
            if a <= 0:
                continue
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            cx, cy = sx * W, sy * H
            if i == 0:
                stage.draw_prop(lay, "heart", sx, th, 1.5, y=sy + 0.06)
            elif i == 1:
                for k, (kd, dx) in enumerate((("man", -48), ("woman", 0), ("child", 46))):
                    p, ax, ay, _ = stage.person(kd, 0, "stand", tm, th, "main", 1, 0.32)
                    lay.alpha_composite(p, (int(cx + dx - ax), int(cy + 70 - ay)))
            elif i == 2:
                stage.draw_prop(lay, "lamp", sx, th, 1.6, y=sy + 0.07)
            else:
                dl = ImageDraw.Draw(lay)
                for k in range(3):
                    pts = [(cx - 70 + x, cy + 20 + k * 22 + 8 * math.sin(x / 22 + tm * 2 + k)) for x in range(0, 141, 6)]
                    dl.line(pts, fill=th["glow"] + (230,), width=4)
            dl = ImageDraw.Draw(lay)
            _label(dl, th, cx, cy + 150, names[i])
            img.alpha_composite(scale_alpha(lay, a))
    elif icon == "creature":
        _rays(img, th, 360, 0, G, 60, 260, 70)
        stage.draw_prop(img, "dog", 0.2, th, 1.25)
        stage.draw_prop(img, "sprout", 0.78, th, 1.6)
        _person(img, th, "child", 520, "stand", tm, 1.0)
        _sparks(img, th, 360, tm, 22, spread=220, seed=2)
    elif icon == "beam":
        _rays(img, th, 360, 0, G, 40, 200, 90)
        _person(img, th, "man", 360, "look" if u < 0.5 else "open", tm, 1.05)
        _sparks(img, th, 360, tm, 26, spread=170, seed=3)
    elif icon == "rain":
        _cloud(img, th, 360, 220, 1.5)
        rng = np.random.default_rng(6)
        for i in range(26):
            ox, ph, sp = rng.uniform(-150, 150), rng.uniform(0, 1), rng.uniform(260, 380)
            y = 300 + ((ph * 330 + tm * sp) % 330)
            if y < G - 10:
                d.line([(360 + ox, y), (360 + ox - 3, y + 22)], fill=th["glow"] + (200,), width=3)
        grow = 0.7 + 1.9 * min(1.0, u * 1.6)
        stage.draw_prop(img, "sprout", 0.5, th, grow)
        _person(img, th, "woman", 150, "stand", tm, 0.95, 1, "other")
    elif icon == "lamp":
        pulse = 0.5 + 0.5 * math.sin(tm * 2)
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        r = 150 + 100 * min(1.0, u * 1.5) + 14 * pulse
        ImageDraw.Draw(glow).ellipse((360 - r, G - 260 - r, 360 + r, G - 260 + r), fill=th["glow"] + (70,))
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(75)))
        stage.draw_prop(img, "lamp", 0.5, th, 3.2)
        _person(img, th, "man", 160, "open", tm, 1.0, 1, "other")
        _sparks(img, th, 360, tm, 14, fall=False, spread=90, top=140, bot=G - 120, seed=7)
    elif icon == "door":
        op = min(1.0, max(0.0, (u - 0.2) * 1.6))
        _rays(img, th, 520, G - 330, G, 40 + 60 * op, 70 + 150 * op, int(120 * op))
        stage.draw_prop(img, "door", 0.72, th, 1.15)
        d = ImageDraw.Draw(img)
        d.rectangle((520 - 80 * 1.15, G - 345, 520 + 80 * 1.15, G), fill=stage.lerp(th["ground"], th["glow"], 0.0) + (0,))
        x = 150 + 230 * min(1.0, u * 1.2)
        _person(img, th, "man", x, "walk", tm, 1.0)
    elif icon == "ties":
        xa, xb = 190, 530
        pulse = 0.5 + 0.5 * math.sin(tm * 2.4)
        pts = [(xa + 20 + (xb - xa - 40) * t / 40, G - 170 - 60 * math.sin(math.pi * t / 40)) for t in range(41)]
        d.line(pts, fill=th["glow"] + (int(110 + 120 * pulse),), width=5)
        _person(img, th, "elder", xa, "stand", tm, 1.0)
        _person(img, th, "man", xb, "stand", tm, 1.0, -1)
        stage.draw_prop(img, "heart", 0.5, th, 1.1, y=0.24 + 0.006 * math.sin(tm * 3))
    elif icon == "walk":
        sunu = min(1.0, u * 1.2)
        d.ellipse((360 - 90, G - 40 - 330 * sunu - 90, 360 + 90, G - 40 - 330 * sunu + 90), fill=th["glow"] + (230,))
        x = 120 + 480 * u
        _person(img, th, "man", x, "walk", tm, 1.05)
        if icon == "walk" and u < 0.0:
            pass
    else:
        raise ValueError(icon)


# ------------------------------------------------------------------ text layers

def _text_block(ch, th):
    """Heading, spoken line and quote as separate layers so they can appear one after another."""
    head = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dh = ImageDraw.Draw(head)
    f, lines, lh = textkit.fit(ch["heading"], lambda s: theme.lora(s), 620, 140, 54, 36, line_gap=1.2)
    y = textkit.draw_block(dh, W / 2, 700, lines, f, th["text"], lh)
    f2, l2, lh2 = textkit.fit(ch["line"], lambda s: theme.poppins("light", s), 600, 120, 25, 19, line_gap=1.45)
    y2 = textkit.draw_block(dh, W / 2, y + 12, l2, f2, stage.lerp(th["text"], th["top"], 0.28), lh2)
    quote = None
    if ch.get("quote"):
        q = ch["quote"]
        quote = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dq = ImageDraw.Draw(quote)
        yy = y2 + 26
        dq.line([(W / 2 - 40, yy), (W / 2 + 40, yy)], fill=th["accent"] + (200,), width=2)
        yy += 22
        room = 1150 - yy
        if q.get("arabic"):
            fa, la, lha = textkit.fit(q["arabic"], theme.arabic, 620, min(150, room * 0.4), 50, 28, line_gap=1.7, rtl=True)
            yy = textkit.draw_block(dq, W / 2, yy, la, fa, th["accent"], lha, rtl=True) + 8
            room = 1150 - yy
        fe, le, lhe = textkit.fit(q["english"], serif, 620, max(90, room - 40), 38, 24, line_gap=1.3)
        yy = textkit.draw_block(dq, W / 2, yy, le, fe, th["text"], lhe) + 8
        dq.text((W / 2, yy), q["ref"], font=theme.poppins("medium", 20), fill=th["accent"] + (255,), anchor="mt")
    return head, quote


def _bg(th, seed):
    img = stage.backdrop_sil(th, "none", seed=seed)
    return img


def make_reel(topic, handle, out_path, seed=0, workdir=".", voice_on=True):
    base = stage.THEMES[topic.get("theme", "gold")]
    rng = np.random.default_rng(seed)
    saved = stage.GROUND
    stage.GROUND = 640
    try:
        chs, t = [], 0.6
        n = len(topic["chapters"])
        for i, ch in enumerate(topic["chapters"]):
            th = _th(base, ch.get("tint", "gold"))
            head, quote = _text_block(ch, th)
            c1 = narrate.line(ch["line"], workdir, f"{topic['id']}-{i}a") if voice_on else None
            c2 = narrate.line(ch["quote"]["english"], workdir, f"{topic['id']}-{i}b") if (voice_on and ch.get("quote")) else None
            d1 = max(len(ch["line"].split()) * 0.40 + 1.4, (len(c1) / audio.SR + 1.0) if c1 is not None else 0)
            d2 = 0.0
            if ch.get("quote"):
                d2 = max(len(ch["quote"]["english"].split()) * 0.38 + 1.6, (len(c2) / audio.SR + 1.6) if c2 is not None else 0)
            dur = 1.2 + d1 + d2 + (1.0 if i == n - 1 else 0.4)
            chs.append(dict(ch=ch, th=th, head=head, quote=quote, c1=c1, c2=c2, t0=t, t1=t + dur, tq=t + 1.2 + d1, bg=_bg(th, i + seed)))
            t += dur
        total = t + 1.0
        events = []
        for c in chs:
            events.append((c["t0"] + 0.05, audio.bowl(396, 2.2, 0.07)))
            if c["c1"] is not None:
                events.append((c["t0"] + 0.9, c["c1"]))
            if c["c2"] is not None:
                events.append((c["tq"] + 0.5, c["c2"]))
        wav = f"{workdir}/explainer-audio.wav"
        audio.mix(events, total, wav, seed=seed, extra=audio.pad(total, 98.0, 0.04))
        foot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        theme.spaced(ImageDraw.Draw(foot), (W / 2, 1196), "RUH CORNER", theme.poppins("medium", 18), (200, 190, 170), spacing=6)
        ImageDraw.Draw(foot).text((W / 2, 1226), handle, font=theme.poppins("light", 16), fill=(150, 140, 125, 255), anchor="ma")
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
                k = max(i for i, c in enumerate(chs) if c["t0"] <= tm or i == 0)
                c = chs[k]
                u = min(1.0, max(0.0, (tm - c["t0"]) / (c["t1"] - c["t0"])))
                bg = c["bg"]
                if k > 0 and tm - c["t0"] < 0.7:
                    bg = Image.blend(chs[k - 1]["bg"], c["bg"], (tm - c["t0"]) / 0.7)
                fr = bg.copy()
                pic = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                draw_icon(c["ch"]["icon"], pic, c["th"], tm - c["t0"], u)
                a_in = min(1.0, (tm - c["t0"]) / 0.6)
                a_out = 1.0 if k == n - 1 else min(1.0, (c["t1"] - tm) / 0.4)
                fr.alpha_composite(scale_alpha(pic, min(a_in, a_out)) if min(a_in, a_out) < 1.0 else pic)
                x = lay(("h", k), c["head"], min((tm - c["t0"] - 0.3) / 0.7, a_out))
                if x is not None:
                    fr.alpha_composite(x)
                if c["quote"] is not None:
                    x = lay(("q", k), c["quote"], min((tm - c["tq"]) / 0.9, a_out))
                    if x is not None:
                        fr.alpha_composite(x)
                # progress bar + chapter label
                d = ImageDraw.Draw(fr)
                d.text((44, 52), c["ch"]["label"].upper(), font=theme.poppins("medium", 17), fill=c["th"]["accent"] + (255,), anchor="lm")
                d.text((W - 44, 52), f"{k + 1:02d} / {n:02d}", font=theme.poppins("light", 17), fill=(190, 180, 165, 255), anchor="rm")
                d.line([(44, 82), (W - 44, 82)], fill=(255, 255, 255, 36), width=2)
                d.line([(44, 82), (44 + (W - 88) * ((k + u) / n), 82)], fill=c["th"]["accent"] + (255,), width=2)
                fr.alpha_composite(foot)
                out = fr.convert("RGB")
                fade = min(1.0, tm / 0.6 + 0.001, (total - tm) / 1.0)
                if fade < 1.0:
                    out = Image.blend(Image.new("RGB", (W, H), c["th"]["top"]), out, max(0.0, fade))
                yield polish.finish(out, tm, total, fi=fi)

        audio.encode_video(frames(), W, H, FPS, wav, out_path)
        return dict(total=round(total, 1), chapters=n, voice=any(c["c1"] is not None for c in chs))
    finally:
        stage.GROUND = saved
