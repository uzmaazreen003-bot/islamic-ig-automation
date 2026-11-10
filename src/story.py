"""Story reel: a dark, calm parable. One short line at a time, a stick figure and a beam of light, then a verse or hadith.

Original artwork and animation. The closing verse/hadith is copied verbatim from the data files.
"""
from __future__ import annotations

import math
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import audio, textkit, theme, voice
from .tasbih import scale_alpha

W, H, FPS = 720, 1280, 30
HORIZON = 905
BG_TOP, BG_BOT = (8, 8, 9), (24, 19, 13)
GOLD = (236, 190, 112)
WARM = (246, 240, 228)
DIM = (150, 142, 130)


def hadith_body(text):
    m = re.search(r"\bsaid\s*[:,]\s*", text[:320])
    body = text[m.end():] if m else text
    body = body.strip().strip('"').strip()
    return body if body[-1] in ".!?" else body + "."


def ending_content(ending, pools):
    """-> dict(arabic, english, ref, numbers) for the closing card, verbatim from the data."""
    if ending["type"] == "ayah":
        it = pools["ayah"].get(ending["key"]) or pools["dua"].get(ending["key"])
        return dict(arabic=it["arabic"], english=it["english"], ref=f"Surah {it['surah_name']} · {it['ref']}", numbers=it.get("numbers", []))
    it = pools["hadith_all"][ending["key"]]
    body = hadith_body(it["text"])
    ex = ending.get("excerpt")
    if ex:
        assert ex in body, f"excerpt not found verbatim in {ending['key']}"
        body = "… " + ex + "."
    return dict(arabic="", english=f"“{body}”", ref=f"{it['collection']} {it['number']}", numbers=[])


# ------------------------------------------------------------------ drawing

def background():
    bg = theme.gradient(W, H, BG_TOP, BG_BOT).convert("RGBA")
    d = ImageDraw.Draw(bg)
    below = Image.new("RGBA", (W, H - HORIZON), (5, 5, 6, 190))
    bg.alpha_composite(below, (0, HORIZON))
    d.line((0, HORIZON, W, HORIZON), fill=(120, 108, 90, 90), width=1)
    return bg


def beam_layer(cx=W, width=2 * W):
    """Soft vertical column of light on a canvas 2x as wide, so it can slide to follow the figure."""
    xs = np.arange(width)[None, :]
    ys = np.arange(HORIZON)[:, None]
    core = np.exp(-((xs - cx) / 52.0) ** 2)
    halo = 0.45 * np.exp(-((xs - cx) / 150.0) ** 2)
    fall = np.clip(0.35 + 0.65 * (ys / HORIZON) ** 1.4, 0, 1)
    a = np.clip((core + halo) * fall, 0, 1)
    img = Image.new("RGBA", (width, HORIZON), (255, 226, 160, 0))
    img.putalpha(Image.fromarray((a * 255).astype("uint8")))
    gh = 420
    gx = np.arange(width)[None, :]
    gy = np.arange(gh)[:, None]
    g = np.exp(-(((gx - cx) / 230.0) ** 2 + ((gy - gh / 2) / 70.0) ** 2))
    glow = Image.new("RGBA", (width, gh), (255, 226, 160, 0))
    glow.putalpha(Image.fromarray((np.clip(g, 0, 1) * 230).astype("uint8")))
    return img, glow


def draw_figure(draw_img, x, y_ground, pose, t, color, scale=1.0, lean_extra=0.0):
    """Stick figure with head, torso, arms and legs. Drawn at 3x on a patch and downsampled for clean lines."""
    S = 3
    pw, ph = 380, 420
    patch = Image.new("RGBA", (pw * S, ph * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(patch)
    ox, oy = pw * S / 2, (ph - 6) * S          # feet baseline at bottom of the patch
    sc = scale * S
    swing = math.sin(t * 5.2) * 0.5 if pose == "walk" else (0.07 if pose != "slump" else 0.04)
    lean = {"walk": 0.04, "stand": 0.0, "slump": 0.42, "open": 0.0}[pose] + lean_extra
    thigh, shin, torso, uarm, farm = 42, 42, 74, 30, 30
    hip = (ox, oy - (thigh + shin) * sc * 0.97)
    neck = (hip[0] + math.sin(lean) * torso * sc, hip[1] - math.cos(lean) * torso * sc)
    head_r = 15 * sc
    head_dir = lean + (0.18 if pose == "slump" else 0.0)
    head = (neck[0] + math.sin(head_dir) * (head_r + 3 * sc), neck[1] - math.cos(head_dir) * (head_r + 3 * sc))

    def limb(origin, a1, l1, a2, l2):
        k = (origin[0] + math.sin(a1) * l1 * sc, origin[1] + math.cos(a1) * l1 * sc)
        e = (k[0] + math.sin(a2) * l2 * sc, k[1] + math.cos(a2) * l2 * sc)
        return k, e

    w = int(6 * sc / S * S * 0.55) + 2
    col = color + (255,)
    # legs
    for sgn in (1, -1):
        a = swing * sgn
        k, e = limb(hip, a, thigh, a - max(0.0, -a) * 0.8, shin)
        d.line([hip, k, e], fill=col, width=w, joint="curve")
    # torso
    d.line([hip, neck], fill=col, width=w)
    # arms
    for sgn in (1, -1):
        if pose == "open":
            a1, a2 = sgn * 1.75, sgn * 1.75
        elif pose == "slump":
            a1, a2 = sgn * 0.12 + 0.05, sgn * 0.05
        else:
            a1 = -swing * sgn * 0.9 + sgn * 0.12
            a2 = a1 * 0.7
        sh = (neck[0] - math.sin(lean) * 8 * sc, neck[1] + math.cos(lean) * 8 * sc)
        if pose == "open":
            e1 = (sh[0] + sgn * uarm * sc * 0.95, sh[1] - uarm * sc * 0.18)
            e2 = (e1[0] + sgn * farm * sc * 0.95, e1[1] - farm * sc * 0.28)
            d.line([sh, e1, e2], fill=col, width=w, joint="curve")
        else:
            ang = a1
            e1 = (sh[0] + math.sin(ang) * uarm * sc, sh[1] + math.cos(ang) * uarm * sc)
            e2 = (e1[0] + math.sin(ang * 0.6) * farm * sc, e1[1] + math.cos(ang * 0.6) * farm * sc)
            d.line([sh, e1, e2], fill=col, width=w, joint="curve")
    d.ellipse((head[0] - head_r, head[1] - head_r, head[0] + head_r, head[1] + head_r), fill=col)
    patch = patch.resize((pw, ph), Image.LANCZOS)
    draw_img.alpha_composite(patch, (int(x - pw / 2), int(y_ground - ph + 6)))


def make_reel(story, ending, handle, out_path, seed=0, workdir=".", use_recitation=False):
    rng = np.random.default_rng(seed + 21)
    recit = voice.recitation(ending["numbers"], workdir) if (use_recitation and ending.get("numbers")) else None
    bg = background()
    beam, beam_glow = beam_layer()
    serif = lambda s: theme.font("Amiri-Regular.ttf", s)       # noqa: E731
    # ---------------- scenes -> timeline
    scenes, t = [], 1.2
    for sc in story["scenes"]:
        words = len(sc["text"].split())
        dur = sc.get("dur") or (1.9 + words * 0.52)
        scenes.append(dict(sc, t0=t, t1=t + dur))
        t += dur
    end_t0 = t + 0.3
    if ending.get("arabic"):
        f_ar, l_ar, lh_ar = textkit.fit(ending["arabic"], theme.arabic, 600, 330, 64, 36, line_gap=1.8, rtl=True)
    else:
        f_ar, l_ar, lh_ar = None, [], 0
    f_en, l_en, lh_en = textkit.fit(ending["english"], lambda s: theme.font("Amiri-Regular.ttf", s), 620, 480 if not l_ar else 320, 50, 30, line_gap=1.4)
    words = len(ending["english"].split())
    rec_len = len(recit) / audio.SR if recit is not None else 0
    read = max(7.0, words / 1.9 + 3.0)
    end_dur = max(read, rec_len + 3.0 if recit is not None else 0)
    total = end_t0 + end_dur + 1.6

    # pre-render closing card layers
    end_lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    de = ImageDraw.Draw(end_lay)
    y = 190
    if l_ar:
        y = textkit.draw_block(de, W / 2, y, l_ar, f_ar, GOLD, lh_ar, rtl=True) + 26
    y = textkit.draw_block(de, W / 2, y, l_en, f_en, WARM, lh_en) + 24
    de.text((W / 2, y), ending["ref"], font=theme.poppins("medium", 22), fill=GOLD, anchor="ma")
    if recit is not None:
        de.text((W / 2, y + 40), f"Recitation: {voice.RECITER}", font=theme.poppins("light", 16), fill=DIM, anchor="ma")
    foot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    theme.spaced(ImageDraw.Draw(foot), (W / 2, 1180), "RUH CORNER", theme.poppins("medium", 20), GOLD, spacing=6)
    ImageDraw.Draw(foot).text((W / 2, 1214), handle, font=theme.poppins("light", 18), fill=DIM, anchor="ma")

    # scene text layers
    def text_layer(sc):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        f, lines, lh = textkit.fit(sc["text"], serif, 620, 240, 62, 40, line_gap=1.3)
        textkit.draw_block(ImageDraw.Draw(lay), W / 2, 190, lines, f, GOLD if sc.get("accent") else WARM, lh)
        return lay
    for sc in scenes:
        sc["layer"] = text_layer(sc)

    # dust specks
    dust = [(rng.uniform(80, 640), rng.uniform(40, HORIZON), rng.uniform(0.6, 2.2), rng.uniform(0, 6.28), rng.uniform(4, 14)) for _ in range(70)]

    # ---------------- audio
    events = []
    if recit is not None:
        events.append((end_t0 + 0.8, recit))
    last_step = -1
    for sc in scenes:
        if sc["pose"] == "walk" and sc["x"][0] != sc["x"][1]:
            tt = sc["t0"] + 0.3
            while tt < sc["t1"] - 0.2:
                events.append((tt, audio.footstep(rng)))
                tt += 0.6
        if sc.get("accent"):
            events.append((sc["t0"] + 0.2, audio.bowl(396, 3.2, 0.12)))
    events.append((end_t0, audio.bowl(432, 3.5, 0.13)))
    wav = f"{workdir}/story-audio.wav"
    audio.mix(events, total, wav, seed=seed, extra=audio.pad(total, 98.0, 0.05))

    cache = {}

    def lay(key, layer, a):
        q = round(max(0, min(1, a)) * 12) / 12
        if q <= 0:
            return None
        k = (key, q)
        if k not in cache:
            cache[k] = scale_alpha(layer, q)
        return cache[k]

    def scene_state(tm):
        for i, sc in enumerate(scenes):
            if sc["t0"] <= tm < sc["t1"]:
                return i, sc
        return None, None

    n_frames = int(total * FPS)

    def frames():
        beam_prev = 0.04
        beam_x = scenes[0]["x"][0] * W
        for fi in range(n_frames):
            tm = fi / FPS
            fr = bg.copy()
            i, sc = scene_state(tm)
            target = 0.04
            pose, xf, color = "stand", 0.5, WARM
            if sc is not None:
                u = (tm - sc["t0"]) / (sc["t1"] - sc["t0"])
                target = sc["beam"]
                pose = sc["pose"]
                xf = sc["x"][0] + (sc["x"][1] - sc["x"][0]) * u
            elif tm >= end_t0:
                target, pose, xf = 0.55, "stand", scenes[-1]["x"][1]
            elif scenes and tm >= scenes[-1]["t1"]:
                target, pose, xf = scenes[-1]["beam"], scenes[-1]["pose"], scenes[-1]["x"][1]
            else:
                pose, xf, target = scenes[0]["pose"], scenes[0]["x"][0], scenes[0]["beam"]
            beam_prev += (target - beam_prev) * 0.05
            b = beam_prev
            beam_x += (xf * W - beam_x) * 0.04
            left = int(W - beam_x)
            fr.alpha_composite(scale_alpha(beam.crop((left, 0, left + W, HORIZON)), min(1.0, b * 1.1)))
            fr.alpha_composite(scale_alpha(beam_glow.crop((left, 0, left + W, beam_glow.height)), min(1.0, b)), (0, HORIZON - 210))
            # dust
            d = ImageDraw.Draw(fr)
            for (dx, dy, r, ph, sp) in dust:
                yy = (dy - tm * sp) % HORIZON
                xx = dx + math.sin(tm * 0.4 + ph) * 10
                near = math.exp(-((xx - W / 2) / 130.0) ** 2)
                al = int(255 * (0.12 + 0.55 * near * min(1.0, b + 0.2)) * (0.6 + 0.4 * math.sin(tm * 1.7 + ph)))
                d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 232, 180, max(0, min(255, al))))
            # figure (fades to grey when beam is dim)
            grey = 0.45 + 0.55 * min(1.0, b * 1.4)
            col = tuple(int(c * grey) for c in WARM)
            if tm >= end_t0:
                fade_fig = max(0.0, 1.0 - (tm - end_t0) / 1.0)
            else:
                fade_fig = 1.0
            if fade_fig > 0:
                fig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                draw_figure(fig, xf * W, HORIZON, pose, tm, col, 1.75)
                if fade_fig < 1.0:
                    fig = scale_alpha(fig, fade_fig)
                fr.alpha_composite(fig)
            # scene text
            for k, s_ in enumerate(scenes):
                a = min((tm - s_["t0"]) / 0.9, (s_["t1"] - tm) / 0.6 if k < len(scenes) - 1 else (s_["t1"] + 0.3 - tm) / 0.6)
                x = lay(("sc", k), s_["layer"], a)
                if x is not None:
                    fr.alpha_composite(x)
            # closing card
            x = lay("end", end_lay, (tm - end_t0) / 1.2)
            if x is not None:
                fr.alpha_composite(x)
            xf_ = lay("foot", foot, (tm - end_t0) / 1.2)
            if xf_ is not None:
                fr.alpha_composite(xf_)
            out = fr.convert("RGB")
            fade = min(1.0, tm / 0.8 + 0.001, (total - tm) / 1.0)
            if fade < 1.0:
                out = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), out, max(0.0, fade))
            yield np.asarray(out)

    audio.encode_video(frames(), W, H, FPS, wav, out_path)
    return dict(total=round(total, 1), scenes=len(scenes), recitation=recit is not None)
