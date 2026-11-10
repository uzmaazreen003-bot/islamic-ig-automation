"""Text carousels (4:5 images) for hadith and ayah posts. Text is copied from the data files only."""
from __future__ import annotations

import os
import re

from PIL import Image, ImageDraw

from . import textkit, theme

W, H = 1080, 1350


def _base(pal, seed_shift=0):
    img = theme.gradient(W, H, pal["bg_top"], pal["bg_bot"]).convert("RGBA")
    img.alpha_composite(theme.glow_layer(W, H, [(300, 360, 420, 0.5), (820, 1000, 380, 0.4)], pal["glow"]))
    img.alpha_composite(theme.skyline(W, 330, pal["accent"], 36 if pal["name"] != "night" else 60), (0, H - 330))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((36, 36, W - 36, H - 36), radius=34, outline=pal["accent"] + (110,), width=3)
    d.rounded_rectangle((52, 52, W - 52, H - 52), radius=28, outline=pal["accent"] + (55,), width=1)
    return img


def _footer(img, pal, handle, n=None, total=None):
    d = ImageDraw.Draw(img)
    d.text((W / 2, H - 120), handle, font=theme.poppins("medium", 30), fill=pal["accent"], anchor="ma")
    if n:
        d.text((W - 90, 78), f"{n}/{total}", font=theme.poppins("light", 26), fill=pal["soft"], anchor="ra")


def _swipe(d, pal, y):
    d.text((W / 2 - 14, y), "Swipe", font=theme.poppins("light", 30), fill=pal["soft"], anchor="ma")
    x0 = W / 2 + 50
    d.line([(x0, y + 20), (x0 + 34, y + 20)], fill=pal["soft"], width=3)
    d.line([(x0 + 24, y + 11), (x0 + 34, y + 20), (x0 + 24, y + 29)], fill=pal["soft"], width=3)


def _save(img, path):
    img.convert("RGB").save(path, "JPEG", quality=92, optimize=True)
    return path


def split_hadith(text):
    """Separate the narrator line ('Narrated X: ... said:') from the words of the hadith, and tidy the ending."""
    text = text.replace("\n", " ").strip()
    m = re.search(r"\bsaid\s*[:,]\s*", text[:320])
    narrator, body = (text[: m.end()].strip(), text[m.end():].strip()) if m else ("", text)
    body = body.strip('"').strip()
    if body and body[-1] not in ".!?\"”":
        body += "."
    return narrator, body


def hadith_slides(item, handle, outdir, stem, seed=0):
    pal = theme.palette_for(seed)
    narrator, body = split_hadith(item["text"])
    files = []
    total = 4

    # 1 cover
    img = _base(pal)
    d = ImageDraw.Draw(img)
    img.alpha_composite(theme.crescent(120, pal["accent"], 235), (W // 2 - 60, 190))
    theme.spaced(d, (W / 2, 420), "HADITH OF THE DAY", theme.poppins("medium", 36), pal["accent"], spacing=8)
    d.line((W / 2 - 60, 500, W / 2 + 60, 500), fill=pal["accent"] + (220,), width=3)
    teaser = body if len(body) <= 150 else body[:147].rsplit(" ", 1)[0] + "…"
    f, lines, lh = textkit.fit(f"“{teaser}”", lambda s: theme.lora(s), 820, 420, 58, 36, line_gap=1.4)
    textkit.draw_block(d, W / 2, 560, lines, f, pal["ink"], lh)
    _swipe(d, pal, 1110)
    _footer(img, pal, handle)
    files.append(_save(img, os.path.join(outdir, f"{stem}-1.jpg")))

    # 2 full text
    img = _base(pal)
    d = ImageDraw.Draw(img)
    y = 190
    if narrator:
        fn, ln, lhn = textkit.fit(narrator, lambda s: theme.poppins("light", s), 840, 250, 28, 21, line_gap=1.4)
        y = textkit.draw_block(d, W / 2, y, ln, fn, pal["soft"], lhn) + 28
    f, lines, lh = textkit.fit(body, lambda s: theme.poppins("medium", s), 850, 1010 - y, 50, 28, line_gap=1.5)
    y2 = y + max(0, (1010 - y - len(lines) * lh) / 2)
    textkit.draw_block(d, W / 2, y2, lines, f, pal["ink"], lh)
    _footer(img, pal, handle, 2, total)
    files.append(_save(img, os.path.join(outdir, f"{stem}-2.jpg")))

    # 3 source
    img = _base(pal)
    d = ImageDraw.Draw(img)
    theme.spaced(d, (W / 2, 330), "SOURCE", theme.poppins("medium", 32), pal["accent"], spacing=8)
    d.line((W / 2 - 50, 400, W / 2 + 50, 400), fill=pal["accent"] + (220,), width=3)
    srcs = " · ".join(item.get("sources") or [])
    d.text((W / 2, 470), item["collection"], font=theme.poppins("medium", 46), fill=pal["ink"], anchor="ma")
    d.text((W / 2, 545), f"Hadith {item['number']}", font=theme.poppins("light", 40), fill=pal["soft"], anchor="ma")
    if srcs:
        d.text((W / 2, 640), f"Narrated in: {srcs}", font=theme.poppins("light", 34), fill=pal["soft"], anchor="ma")
    elif item["collection"] == "Sahih al-Bukhari":
        d.text((W / 2, 640), "Graded authentic (sahih)", font=theme.poppins("light", 34), fill=pal["soft"], anchor="ma")
    d.text((W / 2, 800), "Reflect on it today, and act on one small thing.", font=theme.lora(36), fill=pal["ink"], anchor="ma")
    _footer(img, pal, handle, 3, total)
    files.append(_save(img, os.path.join(outdir, f"{stem}-3.jpg")))

    # 4 call to action
    img = _base(pal)
    d = ImageDraw.Draw(img)
    f = theme.arabic(130)
    d.text((W / 2, 280), "جَزَاكَ ٱللَّهُ خَيْرًا", font=f, fill=pal["ink"], anchor="ma", direction="rtl", language="ar")
    d.text((W / 2, 560), "Save this reminder", font=theme.poppins("bold", 54), fill=pal["ink"], anchor="ma")
    d.text((W / 2, 650), "Share it with someone you love", font=theme.poppins("light", 38), fill=pal["soft"], anchor="ma")
    d.text((W / 2, 780), "Follow for a daily reminder", font=theme.poppins("light", 34), fill=pal["soft"], anchor="ma")
    _footer(img, pal, handle, 4, total)
    files.append(_save(img, os.path.join(outdir, f"{stem}-4.jpg")))
    return files


def ayah_slides(item, handle, outdir, stem, seed=0):
    pal = theme.palette_for(seed)
    files = []
    total = 3
    # 1 Arabic
    img = _base(pal)
    d = ImageDraw.Draw(img)
    theme.spaced(d, (W / 2, 150), "DUA FROM THE QURAN" if item["kind"] == "dua" else "FROM THE QURAN",
                 theme.poppins("medium", 30), pal["accent"], spacing=7)
    top = 230
    if item.get("title"):
        ft, lt, lht = textkit.fit(item["title"], lambda s: theme.poppins("light", s), 820, 110, 36, 26, line_gap=1.3)
        top = textkit.draw_block(d, W / 2, 215, lt, ft, pal["soft"], lht) + 14
    d.line((W / 2 - 50, top + 6, W / 2 + 50, top + 6), fill=pal["accent"] + (220,), width=3)
    box = 1000 - (top + 60)
    f, lines, lh = textkit.fit(item["arabic"], theme.arabic, 880, box, 110, 52, line_gap=1.85, rtl=True)
    y = top + 60 + (box - len(lines) * lh) / 2
    textkit.draw_block(d, W / 2, y, lines, f, pal["ink"], lh, rtl=True)
    _swipe(d, pal, 1110)
    _footer(img, pal, handle, 1, total)
    files.append(_save(img, os.path.join(outdir, f"{stem}-1.jpg")))
    # 2 meaning
    img = _base(pal)
    d = ImageDraw.Draw(img)
    theme.spaced(d, (W / 2, 190), "MEANING", theme.poppins("medium", 30), pal["accent"], spacing=8)
    f, lines, lh = textkit.fit(item["english"], lambda s: theme.poppins("medium", s), 850, 760, 52, 28, line_gap=1.5)
    y = 290 + max(0, (760 - len(lines) * lh) / 2)
    y = textkit.draw_block(d, W / 2, y, lines, f, pal["ink"], lh)
    d.text((W / 2, 1090), f"Surah {item['surah_name']}  ·  {item['ref']}", font=theme.poppins("medium", 32), fill=pal["accent"], anchor="ma")
    d.text((W / 2, 1140), "Translation: Saheeh International", font=theme.poppins("light", 24), fill=pal["soft"], anchor="ma")
    _footer(img, pal, handle, 2, total)
    files.append(_save(img, os.path.join(outdir, f"{stem}-2.jpg")))
    # 3 cta
    img = _base(pal)
    d = ImageDraw.Draw(img)
    d.text((W / 2, 300), "جَزَاكَ ٱللَّهُ خَيْرًا", font=theme.arabic(130), fill=pal["ink"], anchor="ma", direction="rtl", language="ar")
    d.text((W / 2, 580), "Save this reminder", font=theme.poppins("bold", 54), fill=pal["ink"], anchor="ma")
    d.text((W / 2, 670), "Share it with someone you love", font=theme.poppins("light", 38), fill=pal["soft"], anchor="ma")
    d.text((W / 2, 800), "Follow for a daily reminder", font=theme.poppins("light", 34), fill=pal["soft"], anchor="ma")
    _footer(img, pal, handle, 3, total)
    files.append(_save(img, os.path.join(outdir, f"{stem}-3.jpg")))
    return files
