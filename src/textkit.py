"""Text wrapping and auto-fitting, including right-to-left Arabic (needs Pillow built with raqm)."""
from __future__ import annotations

from PIL import ImageFont

from . import theme


def _len(font, text, rtl):
    if rtl:
        return font.getlength(text, direction="rtl", language="ar")
    return font.getlength(text)


def wrap(text, font, max_w, rtl=False):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and _len(font, trial, rtl) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def wrap_balanced(text, font, max_w, rtl=False):
    """Greedy wrap, then narrow the width as far as the line count allows so no line is a lonely word."""
    lines = wrap(text, font, max_w, rtl)
    n = len(lines)
    if n < 2:
        return lines
    lo, hi = max_w * 0.45, max_w
    best = lines
    for _ in range(14):
        mid = (lo + hi) / 2
        cand = wrap(text, font, mid, rtl)
        if len(cand) <= n:
            best, hi = cand, mid
        else:
            lo = mid
    return best


def fit(text, make_font, max_w, max_h, max_size, min_size, line_gap=1.45, rtl=False, step=2):
    """Largest font size whose wrapped text fits in max_w x max_h. Returns (font, lines, line_h)."""
    size = max_size
    while True:
        f = make_font(size)
        lines = wrap_balanced(text, f, max_w, rtl)
        lh = size * line_gap
        if len(lines) * lh <= max_h or size <= min_size:
            return f, lines, lh
        size -= step


def draw_line(draw, cx, y, text, font, fill, rtl=False):
    if rtl:
        draw.text((cx, y), text, font=font, fill=fill, anchor="ma", direction="rtl", language="ar")
    else:
        draw.text((cx, y), text, font=font, fill=fill, anchor="ma")


def draw_block(draw, cx, y, lines, font, fill, line_h, rtl=False):
    for i, line in enumerate(lines):
        draw_line(draw, cx, y + i * line_h, line, font, fill, rtl)
    return y + len(lines) * line_h
