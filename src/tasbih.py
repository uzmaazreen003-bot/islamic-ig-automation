"""Tasbih reel: beads drop one by one into three glass jars while the dhikr counts up. Original artwork."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from . import audio, textkit, theme, voice

W, H, FPS = 720, 1280, 30
BEAD = 38
JAR_W, JAR_H = 196, 190
JAR_BOTTOM = 1010
JAR_X = (120, 360, 600)
NOZZLE_Y = 730
FALL = 0.8
INTERVAL = 2.4          # one bead every 2.4 s: time to hear the phrase and read it
GAP_BETWEEN_SETS = 1.1
INTRO = 1.4
OUTRO = 3.2


def bead_sprite(rgb, d=BEAD, ss=4):
    D = d * ss
    yy, xx = np.mgrid[0:D, 0:D]
    c = (D - 1) / 2
    r = D / 2 - ss * 0.6
    dx, dy = (xx - c) / r, (yy - c) / r
    rr = dx ** 2 + dy ** 2
    z = np.sqrt(np.clip(1 - rr, 0, 1))
    L = np.array([-0.42, -0.58, 0.69])
    L /= np.linalg.norm(L)
    diff = np.clip(dx * L[0] + dy * L[1] + z * L[2], 0, 1)
    hvec = L + np.array([0, 0, 1.0])
    hvec /= np.linalg.norm(hvec)
    spec = np.clip(dx * hvec[0] + dy * hvec[1] + z * hvec[2], 0, 1) ** 45
    base = np.array(rgb, dtype=float) / 255
    rim = 1 - 0.28 * np.clip(rr, 0, 1) ** 3
    col = base[None, None, :] * (0.50 + 0.62 * diff)[..., None] * rim[..., None]
    col = np.clip(col + spec[..., None] * 0.85, 0, 1)
    edge = np.clip((1 - np.sqrt(rr)) * r / (ss * 1.2), 0, 1)
    arr = np.dstack([col, edge])
    img = Image.fromarray((arr * 255).astype("uint8"), "RGBA")
    return img.resize((d, d), Image.LANCZOS)


def jar_layers(pal):
    """Return (back, front) RGBA images sized W x H holding all three jars."""
    ss = 2
    back = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    front = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    db, df = ImageDraw.Draw(back), ImageDraw.Draw(front)
    accent = pal["accent"]
    ink = pal["ink"]
    dark = pal["name"] == "night"
    tint = (255, 255, 255, 34 if dark else 120)
    edge = accent + (200,)
    for cx in JAR_X:
        x0, x1 = (cx - JAR_W / 2) * ss, (cx + JAR_W / 2) * ss
        y0, y1 = (JAR_BOTTOM - JAR_H) * ss, JAR_BOTTOM * ss
        db.rounded_rectangle((x0, y0, x1, y1), radius=34 * ss, fill=tint)
        df.rounded_rectangle((x0, y0, x1, y1), radius=34 * ss, outline=edge, width=3 * ss)
        # neck + lid rim
        nx0, nx1 = (cx - JAR_W * 0.36) * ss, (cx + JAR_W * 0.36) * ss
        df.rounded_rectangle((nx0, y0 - 16 * ss, nx1, y0 + 6 * ss), radius=7 * ss, outline=edge, width=3 * ss,
                             fill=accent + (60,))
        # glass highlight
        hl = (255, 255, 255, 120 if not dark else 70)
        df.rounded_rectangle((x0 + 12 * ss, y0 + 28 * ss, x0 + 22 * ss, y1 - 34 * ss), radius=5 * ss, fill=hl)
        df.rounded_rectangle((x1 - 20 * ss, y0 + 40 * ss, x1 - 15 * ss, y0 + 90 * ss), radius=3 * ss, fill=hl)
    return back.resize((W, H), Image.LANCZOS), front.resize((W, H), Image.LANCZOS)


def slot_positions(count):
    """Hex-packed bead slots inside a jar: rows of 4,3,4,3,... filled from the bottom."""
    pos = []
    row = 0
    inner_bottom = JAR_BOTTOM - 16
    while len(pos) < count:
        n = 4 if row % 2 == 0 else 3
        for k in range(n):
            if len(pos) >= count:
                break
            x = (k - (n - 1) / 2) * (BEAD + 0.5)
            y = inner_bottom - BEAD / 2 - row * (BEAD * 0.87)
            pos.append((x, y))
        row += 1
    return pos


def background(pal):
    bg = theme.gradient(W, H, pal["bg_top"], pal["bg_bot"]).convert("RGBA")
    bg.alpha_composite(theme.glow_layer(W, H, [(360, 300, 330, 0.55), (360, 980, 260, 0.35)], pal["glow"]))
    sky = theme.skyline(W, 260, pal["accent"], 46 if pal["name"] != "night" else 70)
    bg.alpha_composite(sky, (0, H - 260))
    moon = theme.crescent(76, pal["accent"], 235)
    bg.alpha_composite(moon, (596, 48))
    d = ImageDraw.Draw(bg)
    # shelf under the jars
    d.rounded_rectangle((38, JAR_BOTTOM, W - 38, JAR_BOTTOM + 14), radius=7, fill=pal["accent"] + (120,))
    d.rounded_rectangle((38, JAR_BOTTOM + 14, W - 38, JAR_BOTTOM + 22), radius=4, fill=pal["accent"] + (50,))
    return bg


def text_layer(item, pal):
    """Arabic + transliteration + meaning for one dhikr, as an RGBA layer."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    f, lines, lh = textkit.fit(item["ar"], theme.arabic, 600, 230, 120, 66, line_gap=1.75, rtl=True)
    y = 120 + (230 - len(lines) * lh) / 2
    textkit.draw_block(d, W / 2, y, lines, f, pal["ink"], lh, rtl=True)
    d.line((W / 2 - 46, 392, W / 2 + 46, 392), fill=pal["accent"] + (220,), width=2)
    f2, l2, lh2 = textkit.fit(item["tr"], lambda s: theme.poppins("bold", s), 640, 120, 46, 30, line_gap=1.25)
    textkit.draw_block(d, W / 2, 414, l2, f2, pal["ink"], lh2)
    f3, l3, lh3 = textkit.fit(item["en"], lambda s: theme.poppins("medium", s), 620, 90, 30, 22, line_gap=1.3)
    textkit.draw_block(d, W / 2, 414 + len(l2) * lh2 + 10, l3, f3, pal["soft"], lh3)
    return lay


def end_layer(pal, handle):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    veil = theme.gradient(W, H, pal["bg_top"], pal["bg_bot"]).convert("RGBA")
    veil.putalpha(252)
    lay.alpha_composite(veil)
    f = theme.arabic(150)
    d.text((W / 2, 250), "آمِين", font=f, fill=pal["ink"], anchor="ma", direction="rtl", language="ar")
    d.line((W / 2 - 50, 640, W / 2 + 50, 640), fill=pal["accent"] + (220,), width=2)
    d.text((W / 2, 676), "May Allah accept it from us", font=theme.poppins("medium", 32), fill=pal["ink"], anchor="ma")
    d.text((W / 2, 744), "Save this  ·  Share it with someone you love", font=theme.poppins("light", 24), fill=pal["soft"], anchor="ma")
    f4 = theme.poppins("bold", 30)
    theme.spaced(d, (W / 2, 830), handle.upper().replace("@", ""), f4, pal["accent"], spacing=5)
    return lay


def scale_alpha(layer, k):
    if k >= 0.999:
        return layer
    a = layer.getchannel("A").point(lambda v: int(v * k))
    out = layer.copy()
    out.putalpha(a)
    return out


def build_timeline(counts):
    """Per-set timing. counts: bead count per set (all sets share INTERVAL)."""
    sets = []
    t = INTRO
    for n in counts:
        starts = [t + i * INTERVAL for i in range(n)]
        lands = [s + FALL for s in starts]
        sets.append(dict(n=n, starts=starts, lands=lands, first=starts[0], last_land=lands[-1]))
        t = lands[-1] + GAP_BETWEEN_SETS - FALL * 0 - 0.1
    total = sets[-1]["last_land"] + OUTRO
    return sets, total


def make_reel(dhikr_set, dhikr_lib, handle, out_path, seed=0, workdir="."):
    pal = theme.palette_for(seed)
    items = [dict(dhikr_lib[k]) for k in dhikr_set["items"]]
    per = dhikr_set["count"]
    n_sets = len(items)
    sets, total = build_timeline([per] * n_sets)
    total_beads = per * n_sets
    sprites = [bead_sprite(c) for c in pal["jar"]]
    bg = background(pal)
    back, front = jar_layers(pal)
    layers = [text_layer(it, pal) for it in items]
    end = end_layer(pal, handle)
    slots = slot_positions(per)
    rng = np.random.default_rng(seed + 11)
    jitter = [[(rng.uniform(-3, 3), rng.uniform(-2, 2)) for _ in range(per)] for _ in range(n_sets)]
    f_head = theme.poppins("medium", 20)
    f_name = theme.poppins("medium", 22)
    f_cnt = theme.poppins("light", 19)
    f_foot = theme.poppins("light", 21)
    alpha_cache = {}

    def layer_at(k, a):
        q = round(a * 12) / 12
        key = (k, q)
        if key not in alpha_cache:
            alpha_cache[key] = scale_alpha(layers[k], q)
        return alpha_cache[key]

    # -------- audio
    rng_a = np.random.default_rng(seed + 5)
    clips = [voice.dhikr(it["ar"], workdir, f"{seed}-{i}") for i, it in enumerate(items)]
    events = [(0.35, audio.bowl(432, 3.0, 0.12))]
    for si, s in enumerate(sets):
        clip = clips[si]
        if clip is not None:
            clip = clip[: int((INTERVAL - 0.15) * audio.SR)]
        for st, ld in zip(s["starts"], s["lands"]):
            events.append((st + 0.02, audio.drop_ping(rng_a)))
            if clip is not None:
                events.append((st + 0.15, clip))
            events.append((ld - 0.01, audio.clink(rng_a, pitch=[1.0, 0.92, 1.1][si % 3])))
        events.append((s["last_land"] + 0.05, audio.bowl([528, 594, 660][si % 3], 2.4, 0.14)))
    end_t = sets[-1]["last_land"] + 1.0
    events.append((end_t, audio.bowl(396, 3.2, 0.16)))
    wav = f"{workdir}/tasbih-audio.wav"
    audio.mix(events, total, wav, seed=seed)

    n_frames = int(total * FPS)
    jar_label = [(JAR_X[i], 1042) for i in range(3)]

    def frames():
        for fi in range(n_frames):
            t = fi / FPS
            fr = bg.copy()
            # nozzle x follows the active set
            active = 0
            for si, s in enumerate(sets):
                if t >= s["first"] - 0.4:
                    active = si
            fr.alpha_composite(back)
            # landed / falling beads
            done_total = 0
            counts = [0] * 3
            for si, s in enumerate(sets):
                cx = JAR_X[si]
                for bi in range(s["n"]):
                    st, ld = s["starts"][bi], s["lands"][bi]
                    if t < st:
                        break
                    sx, sy = slots[bi]
                    jx, jy = jitter[si][bi]
                    tx, ty = cx + sx + jx * 0.25, sy + jy * 0.25
                    if t < ld:
                        u = (t - st) / FALL
                        y = NOZZLE_Y + (ty - NOZZLE_Y) * (u * u)
                        x = cx + (tx - cx) * (u ** 3) + math.sin(u * 5 + bi) * 0.8 * (1 - u)
                    else:
                        x, y = tx, ty
                        s_ = t - ld
                        if s_ < 0.16:
                            y -= 6 * math.sin(math.pi * s_ / 0.16) * (1 - s_ / 0.16)
                        counts[si] += 1
                        done_total += 1
                    sp = sprites[si]
                    fr.alpha_composite(sp, (int(round(x - BEAD / 2)), int(round(y - BEAD / 2))))
            fr.alpha_composite(front)
            d = ImageDraw.Draw(fr)
            # dhikr text with cross-fade
            for si, s in enumerate(sets):
                a_in = (t - (s["first"] - 0.55)) / 0.35
                nxt = sets[si + 1]["first"] - 0.55 if si + 1 < len(sets) else s["last_land"] + 0.9
                a_out = (min(s["last_land"] + 0.45, nxt) - t) / 0.3
                a = max(0.0, min(1.0, a_in, a_out))
                if a > 0:
                    fr.alpha_composite(layer_at(si, a))
            # header chip
            if t >= INTRO - 0.5:
                head = f"DHIKR {active + 1} OF {n_sets}   ·   {sum(counts)} / {total_beads}"
                theme.spaced(d, (W / 2, 72), head, f_head, dict_alpha(pal["soft"]), spacing=3)
            # nozzle
            nx = JAR_X[active]
            noz = nozzle_x(t, sets, active)
            draw_nozzle(d, noz, pal)
            # labels
            for si in range(3):
                if si >= n_sets:
                    continue
                name = items[si]["tr"]
                short = name if len(name) < 16 else name.split(" ")[0]
                col = pal["accent"] if si == active and counts[si] < per else pal["ink"]
                d.text((jar_label[si][0], jar_label[si][1]), short, font=f_name, fill=col, anchor="ma")
                d.text((jar_label[si][0], jar_label[si][1] + 30), f"{counts[si]} / {per}", font=f_cnt, fill=pal["soft"], anchor="ma")
                if counts[si] >= per:
                    cx_, cy_ = jar_label[si][0] + 52, jar_label[si][1] + 41
                    d.line([(cx_ - 6, cy_), (cx_ - 2, cy_ + 5), (cx_ + 7, cy_ - 6)], fill=pal["accent"], width=3)
            d.text((W / 2, 1218), handle, font=f_foot, fill=pal["soft"], anchor="ma")
            # ending card
            if t >= end_t - 0.4:
                a = min(1.0, (t - (end_t - 0.4)) / 0.6)
                fr.alpha_composite(layer_end(end, a))
            fade_out = min(1.0, (total - t) / 0.4)
            out = fr.convert("RGB")
            if fade_out < 1.0:
                out = Image.blend(Image.new("RGB", (W, H), pal["bg_bot"]), out, fade_out)
            yield np.asarray(out)

    audio.encode_video(frames(), W, H, FPS, wav, out_path)
    return dict(total=total, beads=total_beads, palette=pal["name"], voice=[c is not None for c in clips])


_end_cache = {}


def layer_end(layer, a):
    q = round(a * 10) / 10
    key = (id(layer), q)
    if key not in _end_cache:
        _end_cache[key] = scale_alpha(layer, q)
    return _end_cache[key]


def dict_alpha(rgb):
    return tuple(rgb)


def nozzle_x(t, sets, active):
    """Nozzle glides to the next jar just before its first bead."""
    cur = JAR_X[active]
    if active == 0:
        return cur
    start = sets[active]["first"] - 0.6
    u = max(0.0, min(1.0, (t - start) / 0.45))
    u = u * u * (3 - 2 * u)
    return JAR_X[active - 1] + (JAR_X[active] - JAR_X[active - 1]) * u


def draw_nozzle(d, x, pal):
    a = pal["accent"]
    d.polygon([(x - 34, NOZZLE_Y - 62), (x + 34, NOZZLE_Y - 62), (x + 10, NOZZLE_Y - 16), (x - 10, NOZZLE_Y - 16)], fill=a + (230,))
    d.rounded_rectangle((x - 10, NOZZLE_Y - 18, x + 10, NOZZLE_Y - 2), radius=4, fill=a + (255,))
    d.rounded_rectangle((x - 40, NOZZLE_Y - 70, x + 40, NOZZLE_Y - 58), radius=6, fill=a + (255,))
