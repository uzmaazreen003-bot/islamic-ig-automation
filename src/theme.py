"""Colours, fonts and small drawing helpers shared by all post types."""
from __future__ import annotations

import functools
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "assets", "fonts")

PALETTES = [
    dict(name="rose", bg_top=(253, 246, 238), bg_bot=(242, 222, 203), ink=(92, 26, 43), accent=(176, 120, 60),
         soft=(140, 96, 100), glow=(255, 214, 190), jar=[(248, 241, 230), (212, 138, 128), (214, 166, 70)]),
    dict(name="sage", bg_top=(247, 249, 241), bg_bot=(222, 231, 212), ink=(36, 64, 50), accent=(160, 124, 56),
         soft=(88, 110, 98), glow=(214, 236, 200), jar=[(246, 244, 233), (118, 162, 132), (212, 170, 78)]),
    dict(name="sand", bg_top=(251, 245, 233), bg_bot=(236, 218, 190), ink=(70, 48, 30), accent=(160, 100, 50),
         soft=(122, 100, 82), glow=(255, 226, 180), jar=[(250, 246, 238), (190, 120, 90), (200, 160, 70)]),
]


def palette_for(seed: int):
    return PALETTES[seed % len(PALETTES)]


@functools.lru_cache(maxsize=64)
def font(name: str, size: int):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(size))


def poppins(weight: str, size: int):
    return font({"light": "Poppins-Light.ttf", "medium": "Poppins-Medium.ttf", "bold": "Poppins-Bold.ttf"}[weight], size)


def arabic(size: int):
    return font("AmiriQuran.ttf", size)


def lora(size: int):
    f = font("Lora-Italic-Variable.ttf", size)
    return f


def gradient(w, h, top, bot):
    t = np.linspace(0, 1, h)[:, None, None]
    arr = np.array(top)[None, None, :] * (1 - t) + np.array(bot)[None, None, :] * t
    arr = np.repeat(arr, w, axis=1)
    return Image.fromarray(arr.astype("uint8"), "RGB")


def glow_layer(w, h, spots, color):
    """spots: [(cx, cy, radius, strength 0..1)] -> blurred RGBA light blobs."""
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    for cx, cy, r, s in spots:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=int(255 * s))
    layer = layer.filter(ImageFilter.GaussianBlur(70))
    rgba = Image.new("RGBA", (w, h), color + (0,))
    rgba.putalpha(layer)
    return rgba


def crescent(size, color, alpha=255):
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((s * 0.08, s * 0.08, s * 0.92, s * 0.92), fill=color + (alpha,))
    cut = Image.new("L", (s, s), 0)
    ImageDraw.Draw(cut).ellipse((s * 0.28, s * 0.02, s * 1.05, s * 0.86), fill=255)
    a = img.getchannel("A")
    a = Image.fromarray(np.clip(np.array(a, dtype=int) - np.array(cut, dtype=int), 0, 255).astype("uint8"))
    img.putalpha(a)
    return img.resize((size, size), Image.LANCZOS)


def skyline(w, h, color, alpha):
    """Soft mosque skyline silhouette (domes + minarets), drawn at 2x for smooth edges."""
    s = 2
    img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = color + (alpha,)
    base = h * s

    def dome(cx, r, body_h):
        d.rectangle((cx - r, base - body_h, cx + r, base), fill=c)
        d.pieslice((cx - r, base - body_h - r, cx + r, base - body_h + r), 180, 360, fill=c)
        d.line((cx, base - body_h - r, cx, base - body_h - r - 26), fill=c, width=5)
        d.ellipse((cx - 6, base - body_h - r - 40, cx + 6, base - body_h - r - 26), fill=c)

    def minaret(cx, hh, ww):
        d.rectangle((cx - ww, base - hh, cx + ww, base), fill=c)
        d.rectangle((cx - ww - 8, base - hh, cx + ww + 8, base - hh + 10), fill=c)
        d.polygon([(cx - ww, base - hh), (cx + ww, base - hh), (cx, base - hh - ww * 4.2)], fill=c)

    W = w * s
    dome(W * 0.50, 150, 120)
    dome(W * 0.30, 80, 70)
    dome(W * 0.70, 80, 70)
    minaret(W * 0.13, 300, 20)
    minaret(W * 0.87, 300, 20)
    minaret(W * 0.40, 190, 12)
    minaret(W * 0.60, 190, 12)
    d.rectangle((0, base - 36, W, base), fill=c)
    return img.resize((w, h), Image.LANCZOS)


def spaced(draw, xy, text, font_, fill, spacing=3, anchor_center=True):
    """Letter-spaced text (small caps look)."""
    widths = [draw.textlength(ch, font=font_) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = xy
    if anchor_center:
        x -= total / 2
    for ch, wd in zip(text, widths):
        draw.text((x, y), ch, font=font_, fill=fill)
        x += wd + spacing
