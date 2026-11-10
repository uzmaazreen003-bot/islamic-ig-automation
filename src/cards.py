"""Quran ayah / dua Reel: Arabic fades in line by line, then the English meaning. Calm, no music."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from . import audio, textkit, theme, voice
from .tasbih import scale_alpha

W, H, FPS = 720, 1280, 30


def _header(item):
    if item["kind"] == "dua":
        return "DUA FROM THE QURAN"
    return "FROM THE QURAN"


def _ref_line(item):
    return f"Surah {item['surah_name']}  ·  {item['ref']}"


def make_reel(item, handle, out_path, seed=0, workdir="."):
    pal = theme.palette_for(seed)
    recit = voice.recitation(item.get("numbers", []), workdir) if item.get("numbers") else None
    if recit is None:
        print("[cards] no recitation audio; reel will use natural sounds only")
    bg = theme.gradient(W, H, pal["bg_top"], pal["bg_bot"]).convert("RGBA")
    sky = theme.skyline(W, 240, pal["accent"], 40 if pal["name"] != "night" else 64)
    bg.alpha_composite(sky, (0, H - 240))
    bg.alpha_composite(theme.crescent(70, pal["accent"], 230), (598, 52))
    d = ImageDraw.Draw(bg)
    # thin ornamental frame
    d.rounded_rectangle((28, 28, W - 28, H - 28), radius=26, outline=pal["accent"] + (110,), width=2)
    d.rounded_rectangle((40, 40, W - 40, H - 40), radius=20, outline=pal["accent"] + (60,), width=1)
    theme.spaced(d, (W / 2, 96), _header(item), theme.poppins("medium", 21), pal["accent"], spacing=5)
    y_cursor = 150
    if item.get("title"):
        ft, lt, lht = textkit.fit(item["title"], lambda s: theme.poppins("light", s), 600, 70, 26, 20, line_gap=1.3)
        y_cursor = textkit.draw_block(d, W / 2, 140, lt, ft, pal["soft"], lht) + 6
    d.line((W / 2 - 40, y_cursor + 8, W / 2 + 40, y_cursor + 8), fill=pal["accent"] + (200,), width=2)

    top = int(y_cursor + 38)
    # Arabic block
    box_h = 470
    fa, lines_ar, lha = textkit.fit(item["arabic"], theme.arabic, 610, box_h, 82, 40, line_gap=1.85, rtl=True)
    ar_h = len(lines_ar) * lha
    ar_y = top + (box_h - ar_h) / 2
    ar_layers = []
    for i, line in enumerate(lines_ar):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        textkit.draw_line(ImageDraw.Draw(lay), W / 2, ar_y + i * lha, line, fa, pal["ink"], rtl=True)
        ar_layers.append(lay)

    # English block
    en_top = top + box_h + 24
    fe, lines_en, lhe = textkit.fit(item["english"], lambda s: theme.poppins("medium", s), 610, 250, 34, 24, line_gap=1.42)
    en = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    de = ImageDraw.Draw(en)
    textkit.draw_block(de, W / 2, en_top, lines_en, fe, pal["ink"], lhe)
    ref = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ref)
    dr.text((W / 2, en_top + len(lines_en) * lhe + 22), _ref_line(item), font=theme.poppins("medium", 22), fill=pal["accent"], anchor="ma")
    credit = "Translation: Saheeh International" + (f"  ·  Recitation: {voice.RECITER}" if recit is not None else "")
    dr.text((W / 2, en_top + len(lines_en) * lhe + 56), credit, font=theme.poppins("light", 16), fill=pal["soft"], anchor="ma")
    foot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(foot).text((W / 2, 1176), handle, font=theme.poppins("light", 21), fill=pal["soft"], anchor="ma")

    # timing: Arabic appears line by line while it is recited, then the English stays long enough to read
    rec_start = 1.6
    rec_len = len(recit) / audio.SR if recit is not None else 1.8 * len(lines_ar)
    weights = [max(1, len(l.replace(" ", ""))) for l in lines_ar]
    cum = np.cumsum([0] + weights)
    t_ar = [rec_start - 0.2 + rec_len * 0.92 * (cum[i] / cum[-1]) for i in range(len(lines_ar))]
    t_ar = [min(t, rec_start + rec_len) for t in t_ar]
    t_en = rec_start + rec_len + 0.9
    words = len(item["english"].split())
    read = max(7.0, words / 1.7)
    t_ref = t_en + 1.4
    total = min(80.0, t_en + 0.8 + read + 2.0)
    glow_spots = [(200, 380, 280, 0.5), (540, 900, 300, 0.4)]
    glow = theme.glow_layer(W + 240, H + 240, [(x + 120, y + 120, r, s) for x, y, r, s in glow_spots], pal["glow"])

    rng = np.random.default_rng(seed + 3)
    events = [(0.3, audio.bowl(432, 3.2, 0.13)), (total - 3.2, audio.bowl(396, 3.0, 0.12))]
    if recit is not None:
        events.append((rec_start, recit))
    wav = f"{workdir}/card-audio.wav"
    audio.mix(events, total, wav, seed=seed)

    cache = {}

    def lay(key, layer, a):
        q = round(max(0, min(1, a)) * 12) / 12
        if q <= 0:
            return None
        k = (key, q)
        if k not in cache:
            cache[k] = scale_alpha(layer, q)
        return cache[k]

    n_frames = int(total * FPS)

    def frames():
        for fi in range(n_frames):
            t = fi / FPS
            fr = bg.copy()
            ox = int(120 + 40 * math.sin(t * 0.35))
            oy = int(120 + 40 * math.cos(t * 0.28))
            fr.alpha_composite(glow.crop((ox, oy, ox + W, oy + H)))
            fr.alpha_composite(foot)
            for i, l in enumerate(ar_layers):
                x = lay(("ar", i), l, (t - t_ar[i]) / 0.8)
                if x is not None:
                    fr.alpha_composite(x)
            for key, layer, t0 in (("en", en, t_en), ("ref", ref, t_ref)):
                x = lay(key, layer, (t - t0) / 0.9)
                if x is not None:
                    fr.alpha_composite(x)
            out = fr.convert("RGB")
            fade = min(1.0, (total - t) / 0.6, t / 0.3 + 0.0001)
            if fade < 1.0:
                out = Image.blend(Image.new("RGB", (W, H), pal["bg_bot"]), out, max(0.0, fade))
            yield np.asarray(out)

    audio.encode_video(frames(), W, H, FPS, wav, out_path)
    return dict(total=round(total, 1), palette=pal["name"], lines=len(lines_ar), recitation=recit is not None)
