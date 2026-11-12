"""Story reel v2: every story has its own colour theme, backdrop, cast (man/woman/child/elder) and props,
English narration, phrase-by-phrase text with highlighted key words, and a verbatim verse/hadith ending."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from . import audio, narrate, stage, textkit, theme
from .story import ending_content
from .tasbih import scale_alpha

W, H, FPS = stage.W, stage.H, 30
GROUND = stage.GROUND


def _text_layer(text, hl, th, y=150):
    """Serif text, centred, with highlighted words drawn in the accent colour."""
    f, lines, lh = textkit.fit(text, lambda s: theme.font("Amiri-Regular.ttf", s), 620, 260, 60, 38, line_gap=1.3)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    hl = {w.lower().strip(".,!?'\"") for w in hl}
    space = d.textlength(" ", font=f)
    for i, ln in enumerate(lines):
        words = ln.split()
        widths = [d.textlength(w, font=f) for w in words]
        x = W / 2 - (sum(widths) + space * (len(words) - 1)) / 2
        for w, wd in zip(words, widths):
            on = w.lower().strip(".,!?'\"") in hl
            d.text((x, y + i * lh), w, font=f, fill=(th["accent"] if on else th["text"]) + (255,))
            x += wd + space
    return lay


def make_reel(story, ending, handle, out_path, seed=0, workdir=".", voice_on=True):
    rng = np.random.default_rng(seed + 5)
    th = stage.THEMES[story.get("theme", "gold")]
    bg = stage.backdrop(th, story.get("backdrop", "none"), seed=sum(map(ord, story["id"])))
    glow = th["glow"]
    foot_col, dim = th["accent"], tuple(int(c * 0.65 + b * 0.35) for c, b in zip(th["text"], th["bot"]))

    # narration + timeline
    scenes, t = [], 1.0
    for i, sc in enumerate(story["scenes"]):
        clip = narrate.line(sc["text"], workdir, f"{story['id']}-{i}") if voice_on else None
        words = len(sc["text"].split())
        dur = max(2.8 + words * 0.5, (len(clip) / audio.SR + 1.6) if clip is not None else 0)
        scenes.append(dict(sc, t0=t, t1=t + dur, clip=clip, layer=_text_layer(sc["text"], sc.get("hl", []), th)))
        t += dur
    end_t0 = t + 0.2
    # closing card
    if ending.get("arabic"):
        f_ar, l_ar, lh_ar = textkit.fit(ending["arabic"], theme.arabic, 600, 330, 64, 36, line_gap=1.8, rtl=True)
    else:
        f_ar, l_ar, lh_ar = None, [], 0
    f_en, l_en, lh_en = textkit.fit(ending["english"], lambda s: theme.font("Amiri-Regular.ttf", s), 620, 480 if not l_ar else 320, 50, 30, line_gap=1.4)
    end_dur = max(7.0, len(ending["english"].split()) / 1.9 + 3.0)
    total = end_t0 + end_dur + 1.4
    end_lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    de = ImageDraw.Draw(end_lay)
    y = 190
    if l_ar:
        y = textkit.draw_block(de, W / 2, y, l_ar, f_ar, th["accent"], lh_ar, rtl=True) + 26
    y = textkit.draw_block(de, W / 2, y, l_en, f_en, th["text"], lh_en) + 24
    de.text((W / 2, y), ending["ref"], font=theme.poppins("medium", 22), fill=th["accent"], anchor="ma")
    foot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    theme.spaced(ImageDraw.Draw(foot), (W / 2, 1180), "RUH CORNER", theme.poppins("medium", 20), foot_col, spacing=6)
    ImageDraw.Draw(foot).text((W / 2, 1214), handle, font=theme.poppins("light", 18), fill=dim, anchor="ma")

    # audio
    events = []
    for sc in scenes:
        if sc["clip"] is not None:
            events.append((sc["t0"] + 0.5, sc["clip"]))
        if any(c.get("pose") == "walk" and c.get("move") for c in sc.get("cast", [])):
            tt = sc["t0"] + 0.3
            while tt < sc["t1"] - 0.2:
                events.append((tt, audio.footstep(rng)))
                tt += 0.6
    events.append((end_t0, audio.bowl(432, 3.5, 0.12)))
    wav = f"{workdir}/story-audio.wav"
    audio.mix(events, total, wav, seed=seed, extra=audio.pad(total, 98.0, 0.04))

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
    first_cast = scenes[0].get("cast", [])

    def frames():
        for fi in range(n_frames):
            tm = fi / FPS
            fr = bg.copy()
            cur = None
            for sc in scenes:
                if sc["t0"] <= tm < sc["t1"] + (0.0):
                    cur = sc
            if cur is None:
                cur = scenes[0] if tm < scenes[0]["t0"] else scenes[-1]
            u = min(1.0, max(0.0, (tm - cur["t0"]) / (cur["t1"] - cur["t0"])))
            # soft light pool at the scene's focus
            fx = cur.get("focus", 0.5) * W
            gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(gl).ellipse((fx - 330, GROUND - 520, fx + 330, GROUND + 60), fill=glow + (int(36 + 10 * math.sin(tm)),))
            fr.alpha_composite(gl.filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(60)))
            fade_scene = 1.0 if tm < end_t0 else max(0.0, 1 - (tm - end_t0) / 0.9)
            if fade_scene > 0:
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                for p in cur.get("props", []):
                    stage.draw_prop(layer, p["k"], p["x"], th, p.get("s", 1.0), y=p.get("y"), text=p.get("text", ""), t=tm)
                for c in cur.get("cast", []):
                    xa, xb = c.get("move", [c["x"], c["x"]])
                    x = (xa + (xb - xa) * u) * W
                    patch, ax, ay, _ = stage.person(c["who"], x, c.get("pose", "stand"), tm, th, c.get("role", "main"), c.get("face", 1))
                    layer.alpha_composite(patch, (int(x - ax), GROUND - ay + 4))
                if fade_scene < 1.0:
                    layer = scale_alpha(layer, fade_scene)
                # crossfade between scenes
                a_in = min(1.0, (tm - cur["t0"]) / 0.6)
                if a_in < 1.0:
                    layer = scale_alpha(layer, max(0.0, a_in))
                fr.alpha_composite(layer)
            for k, s_ in enumerate(scenes):
                a = min((tm - s_["t0"]) / 0.8, (s_["t1"] - tm) / 0.5 if k < len(scenes) - 1 else (s_["t1"] + 0.3 - tm) / 0.5)
                x = lay(("sc", k), s_["layer"], a)
                if x is not None:
                    fr.alpha_composite(x)
            x = lay("end", end_lay, (tm - end_t0) / 1.2)
            if x is not None:
                fr.alpha_composite(x)
            x = lay("foot", foot, (tm - end_t0) / 1.2)
            if x is not None:
                fr.alpha_composite(x)
            out = fr.convert("RGB")
            fade = min(1.0, tm / 0.8 + 0.001, (total - tm) / 1.0)
            if fade < 1.0:
                out = Image.blend(Image.new("RGB", (W, H), th["top"]), out, max(0.0, fade))
            yield np.asarray(out)

    audio.encode_video(frames(), W, H, FPS, wav, out_path)
    return dict(total=round(total, 1), scenes=len(scenes), voice=any(s["clip"] is not None for s in scenes))
