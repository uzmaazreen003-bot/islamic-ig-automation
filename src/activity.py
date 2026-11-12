"""Interactive reels: a 'what would you do?' quiz and a tick-along dhikr checklist. Each item has its own colour theme."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import audio, narrate, stage, textkit, theme
from .story import ending_content
from .tasbih import scale_alpha

W, H, FPS = stage.W, stage.H, 30
serif = lambda s: theme.font("Amiri-Regular.ttf", s)       # noqa: E731


def _bg(th, seed):
    img = stage.backdrop(th, "none", seed, ground=False)
    return img


def _footer(th, handle):
    foot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dim = tuple(int(c * 0.65 + b * 0.35) for c, b in zip(th["text"], th["bot"]))
    theme.spaced(ImageDraw.Draw(foot), (W / 2, 1180), "RUH CORNER", theme.poppins("medium", 20), th["accent"], spacing=6)
    ImageDraw.Draw(foot).text((W / 2, 1214), handle, font=theme.poppins("light", 18), fill=dim, anchor="ma")
    return foot


def _end_layer(ending, th):
    if ending.get("arabic"):
        f_ar, l_ar, lh_ar = textkit.fit(ending["arabic"], theme.arabic, 600, 330, 64, 36, line_gap=1.8, rtl=True)
    else:
        f_ar, l_ar, lh_ar = None, [], 0
    f_en, l_en, lh_en = textkit.fit(ending["english"], serif, 620, 480 if not l_ar else 320, 50, 30, line_gap=1.4)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    y = 190
    if l_ar:
        y = textkit.draw_block(d, W / 2, y, l_ar, f_ar, th["accent"], lh_ar, rtl=True) + 26
    y = textkit.draw_block(d, W / 2, y, l_en, f_en, th["text"], lh_en) + 24
    d.text((W / 2, y), ending["ref"], font=theme.poppins("medium", 22), fill=th["accent"], anchor="ma")
    return lay, max(7.0, len(ending["english"].split()) / 1.9 + 3.0)


def _centered(text, max_w, max_h, max_size, min_size, color, y):
    f, lines, lh = textkit.fit(text, serif, max_w, max_h, max_size, min_size, line_gap=1.3)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    textkit.draw_block(ImageDraw.Draw(lay), W / 2, y, lines, f, color, lh)
    return lay, len(lines) * lh


class _Cache:
    def __init__(self):
        self.c = {}

    def get(self, key, layer, a):
        q = round(max(0, min(1, a)) * 12) / 12
        if q <= 0:
            return None
        if (key, q) not in self.c:
            self.c[(key, q)] = scale_alpha(layer, q)
        return self.c[(key, q)]


def _render(frames_fn, total, events, th, seed, workdir, out_path, ambient_pad=98.0):
    wav = f"{workdir}/act-audio.wav"
    audio.mix(events, total, wav, seed=seed, extra=audio.pad(total, ambient_pad, 0.04))
    audio.encode_video(frames_fn(), W, H, FPS, wav, out_path)


def _finish(fr, tm, total, th):
    out = fr.convert("RGB")
    fade = min(1.0, tm / 0.8 + 0.001, (total - tm) / 1.0)
    if fade < 1.0:
        out = Image.blend(Image.new("RGB", (W, H), th["top"]), out, max(0.0, fade))
    return np.asarray(out)


# ------------------------------------------------------------------ quiz

def make_quiz(q, ending, handle, out_path, seed=0, workdir=".", voice_on=True):
    th = stage.THEMES[q.get("theme", "plum")]
    bg = _bg(th, seed)
    rng = np.random.default_rng(seed)
    cache = _Cache()
    tag = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    theme.spaced(ImageDraw.Draw(tag), (W / 2, 110), "THINK FOR A MOMENT", theme.poppins("medium", 22), th["accent"], spacing=5)
    scen, sh = _centered(q["scenario"], 620, 300, 56, 38, th["text"], 170)
    ask, _ = _centered(q["ask"], 620, 120, 44, 32, th["accent"], 170 + sh + 18)
    clip = narrate.line(q["scenario"] + " " + q["ask"], workdir, "quiz-" + q["id"]) if voice_on else None
    t_scen = 1.0
    d_scen = max(5.0 + len(q["scenario"].split()) * 0.35, (len(clip) / audio.SR + 1.5) if clip is not None else 0)
    t_opt = t_scen + d_scen
    opt_y0 = 170 + sh + 120
    opt_h, gap = 112, 22
    t_count = t_opt + 3 * 1.4 + 0.4
    count_s = 5
    t_rev = t_count + count_s
    pal = [(0.55, 0.62), (0.55, 0.62), (0.55, 0.62)]
    letters = "ABC"
    fo = lambda s: theme.poppins("medium", s)       # noqa: E731

    def card(i, state):                               # state: normal / right / dim
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        y = opt_y0 + i * (opt_h + gap)
        base = stage.lerp(th["bot"], th["text"], 0.16)
        fill = {"normal": base, "right": stage.lerp(th["bot"], th["accent"], 0.55), "dim": stage.lerp(th["top"], th["bot"], 0.5)}[state]
        d.rounded_rectangle((50, y, W - 50, y + opt_h), radius=30, fill=fill + (255,), outline=th["accent"] + (200 if state == "right" else 90,), width=3 if state == "right" else 2)
        d.ellipse((70, y + 26, 130, y + 86), fill=th["accent"] + (255 if state != "dim" else 90,))
        d.text((100, y + 56), letters[i], font=fo(30), fill=th["top"] + (255,), anchor="mm")
        f, lines, lh = textkit.fit(q["options"][i], serif, 500, opt_h - 24, 38, 26, line_gap=1.2)
        tc = th["text"] if state != "dim" else stage.lerp(th["text"], th["bot"], 0.6)
        textkit.draw_block(d, 150 + 250, y + (opt_h - len(lines) * lh) / 2 + 2, lines, f, tc, lh)
        return lay
    cards = {s: [card(i, s) for i in range(3)] for s in ("normal", "right", "dim")}
    ans = q["answer"]
    reveal, _ = _centered(q["reveal"], 600, 170, 44, 30, th["text"], opt_y0 + 3 * (opt_h + gap) + 10)
    t_end = t_rev + 1.0 + 3.6
    end_lay, end_dur = _end_layer(ending, th)
    foot = _footer(th, handle)
    total = t_end + end_dur + 1.4
    events = []
    if clip is not None:
        events.append((t_scen + 0.5, clip))
    for i in range(3):
        events.append((t_opt + i * 1.4, audio.drop_ping(rng) if hasattr(audio, "drop_ping") else audio.clink(rng)))
    for s in range(count_s):
        events.append((t_count + s, audio.drop_ping(rng) if hasattr(audio, "drop_ping") else audio.clink(rng)))
    events.append((t_rev, audio.bowl(396, 3.2, 0.13)))
    events.append((t_end, audio.bowl(432, 3.5, 0.12)))

    def frames():
        for fi in range(int(total * FPS)):
            tm = fi / FPS
            fr = bg.copy()
            main_a = 1.0 if tm < t_end else max(0.0, 1 - (tm - t_end) / 0.8)
            if main_a > 0:
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                for key, l, a in (("tag", tag, (tm - 0.3) / 0.8), ("scen", scen, (tm - t_scen) / 1.0), ("ask", ask, (tm - t_scen - 1.5) / 1.0)):
                    x = cache.get(key, l, a)
                    if x is not None:
                        lay.alpha_composite(x)
                for i in range(3):
                    a = (tm - (t_opt + i * 1.4)) / 0.6
                    state = "normal" if tm < t_rev else ("right" if i == ans else "dim")
                    x = cache.get(("c", i, state), cards[state][i], a if tm < t_rev else 1.0)
                    if x is not None:
                        lay.alpha_composite(x)
                if t_count <= tm < t_rev:
                    u = (tm - t_count) / count_s
                    cx, cy = W / 2, opt_y0 + 3 * (opt_h + gap) + 70
                    d = ImageDraw.Draw(lay)
                    d.ellipse((cx - 46, cy - 46, cx + 46, cy + 46), outline=th["accent"] + (70,), width=6)
                    d.arc((cx - 46, cy - 46, cx + 46, cy + 46), -90, -90 + 360 * (1 - u), fill=th["accent"] + (255,), width=6)
                    d.text((cx, cy), str(int(math.ceil(count_s * (1 - u)))), font=fo(40), fill=th["text"] + (255,), anchor="mm")
                x = cache.get("rev", reveal, (tm - t_rev - 0.8) / 0.9)
                if x is not None:
                    lay.alpha_composite(x)
                if main_a < 1.0:
                    lay = scale_alpha(lay, main_a)
                fr.alpha_composite(lay)
            x = cache.get("end", end_lay, (tm - t_end) / 1.2)
            if x is not None:
                fr.alpha_composite(x)
            x = cache.get("foot", foot, (tm - t_end) / 1.2)
            if x is not None:
                fr.alpha_composite(x)
            yield _finish(fr, tm, total, th)

    _render(frames, total, events, th, seed, workdir, out_path)
    return dict(total=round(total, 1), voice=clip is not None)


# ------------------------------------------------------------------ checklist

CHECK_THEMES = ["emerald", "maroon", "gold", "plum"]


def make_checklist(cl, lib, handle, out_path, seed=0, workdir="."):
    """Tick-along dhikr list. Every row has its own colour; the viewer says each phrase and watches the tick appear."""
    th = stage.THEMES[cl.get("theme", "emerald")]
    bg = _bg(th, seed)
    rng = np.random.default_rng(seed)
    cache = _Cache()
    n = len(cl["items"])
    row_cols = [th["accent"], stage.lerp(th["accent"], (255, 255, 255), 0.35), stage.lerp(th["accent"], th["prop"], 0.6), stage.lerp(th["glow"], th["accent"], 0.5)]
    head = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dh = ImageDraw.Draw(head)
    theme.spaced(dh, (W / 2, 110), "TICK ALONG", theme.poppins("medium", 22), th["accent"], spacing=5)
    f, lines, lh = textkit.fit(cl["title"], serif, 620, 200, 58, 38, line_gap=1.25)
    textkit.draw_block(dh, W / 2, 150, lines, f, th["text"], lh)
    sub = "Say each one slowly, then tick it off."
    dh.text((W / 2, 150 + len(lines) * lh + 10), sub, font=theme.poppins("light", 22), fill=th["other"] + (255,), anchor="ma")
    row_h, y0 = 150, 360
    per = cl.get("seconds", 6.0)
    t0 = 3.0
    rows = []
    for i, k in enumerate(cl["items"]):
        it = lib[k]
        col = row_cols[i % len(row_cols)]
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        y = y0 + i * row_h
        d.rounded_rectangle((44, y, W - 44, y + row_h - 20), radius=30, fill=stage.lerp(th["bot"], th["text"], 0.12) + (255,), outline=col + (160,), width=2)
        d.rounded_rectangle((44, y + 18, 56, y + row_h - 38), radius=6, fill=col + (255,))
        fa, la, lha = textkit.fit(it["ar"], theme.arabic, 440, 60, 44, 28, line_gap=1.3, rtl=True)
        textkit.draw_block(d, 330, y + 8, la, fa, th["text"], lha, rtl=True)
        d.text((330, y + 106), it["en"], font=theme.poppins("light", 21), fill=col + (255,), anchor="ma")
        rows.append(lay)
    box_x = W - 120

    def tick(i, u):                                   # u 0..1 draws the check mark
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        cy = y0 + i * row_h + (row_h - 20) / 2
        col = row_cols[i % len(row_cols)]
        d.ellipse((box_x - 34, cy - 34, box_x + 34, cy + 34), outline=col + (255,), width=4, fill=col + ((int(255 * u),) if u > 0.95 else (0,)))
        if u > 0:
            p = [(box_x - 16, cy + 2), (box_x - 4, cy + 15), (box_x + 18, cy - 12)]
            seg1 = min(1.0, u * 2)
            d.line([p[0], (p[0][0] + (p[1][0] - p[0][0]) * seg1, p[0][1] + (p[1][1] - p[0][1]) * seg1)], fill=th["top"] + (255,) if u > 0.95 else col + (255,), width=7)
            if u > 0.5:
                s2 = (u - 0.5) * 2
                d.line([p[1], (p[1][0] + (p[2][0] - p[1][0]) * s2, p[1][1] + (p[2][1] - p[1][1]) * s2)], fill=th["top"] + (255,) if u > 0.95 else col + (255,), width=7)
        return lay

    t_done = t0 + n * per
    close, _ = _centered(cl.get("closing", "Done. Come back tomorrow."), 600, 200, 52, 34, th["text"], y0 + n * row_h + 10)
    total = t_done + 5.5
    foot = _footer(th, handle)
    events = []
    for i in range(n):
        events.append((t0 + i * per + per - 1.0, audio.bowl(520 + 40 * i, 2.2, 0.10)))
    events.append((t_done, audio.bowl(432, 3.5, 0.12)))

    def frames():
        for fi in range(int(total * FPS)):
            tm = fi / FPS
            fr = bg.copy()
            x = cache.get("head", head, (tm - 0.3) / 0.9)
            if x is not None:
                fr.alpha_composite(x)
            for i in range(n):
                ts = t0 + i * per
                a = (tm - (ts - 1.2)) / 0.7
                x = cache.get(("row", i), rows[i], a)
                if x is not None:
                    fr.alpha_composite(x)
                if tm >= ts + per - 1.4:
                    u = min(1.0, (tm - (ts + per - 1.4)) / 0.5)
                    fr.alpha_composite(tick(i, u))
                elif tm >= ts - 1.2:
                    fr.alpha_composite(tick(i, 0.0))
            # a soft pointer on the active row
            for i in range(n):
                ts = t0 + i * per
                if ts <= tm < ts + per - 1.4:
                    pulse = 0.5 + 0.5 * math.sin((tm - ts) * 4)
                    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    ImageDraw.Draw(g).rounded_rectangle((38, y0 + i * row_h - 6, W - 38, y0 + i * row_h + row_h - 14), radius=34, outline=th["glow"] + (int(60 + 100 * pulse),), width=3)
                    fr.alpha_composite(g)
            x = cache.get("close", close, (tm - t_done) / 1.0)
            if x is not None:
                fr.alpha_composite(x)
            x = cache.get("foot", foot, (tm - 1.0) / 1.0)
            if x is not None:
                fr.alpha_composite(x)
            yield _finish(fr, tm, total, th)

    _render(frames, total, events, th, seed, workdir, out_path)
    return dict(total=round(total, 1), rows=n)
