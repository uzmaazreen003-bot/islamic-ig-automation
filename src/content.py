"""Chooses what to post and builds captions. All Quran/hadith text comes from the data files (never generated)."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
MAX_HADITH_CHARS = 560


def now_ist():
    return datetime.now(IST)


def load_pools(data_dir):
    def rd(name):
        with open(os.path.join(data_dir, name), encoding="utf-8") as fh:
            return json.load(fh)

    quran = rd("quran.json")["items"]
    hadith_all = {h["key"]: h for h in rd("hadith.json")["items"]}
    hadith = {k: h for k, h in hadith_all.items() if len(h["text"]) <= MAX_HADITH_CHARS}
    dhikr = rd("dhikr.json")
    stories = {s["id"]: s for s in rd("stories.json")["stories"]}
    quizzes = {s["id"]: s for s in rd("quizzes.json")["quizzes"]}
    checklists = {s["id"]: s for s in dhikr["checklists"]}
    topics = {t["id"]: t for t in rd("explainers.json")["topics"]}
    themes = ["emerald", "maroon", "plum", "amber"]
    boulder = {k: dict(v, key=k, theme=themes[i % len(themes)]) for i, (k, v) in enumerate(dhikr["dhikr"].items())}
    worlds = {f"{sc}-{ph}": dict(dhikr["dhikr"][ph], key=f"{sc}-{ph}", scene=sc, closing=cl) for sc, ph, cl in (
        ("oasis", "astaghfirullah", "Little by little, the dry land turned green."),
        ("lanterns", "allahuakbar", "One by one, the light came back."),
        ("dawn", "alhamdulillah", "And the night gave way to morning."),
        ("oasis", "subhanallah", "Little by little, the dry land turned green."),
        ("lanterns", "salawat", "One by one, the light came back."),
        ("dawn", "hawqala", "And the night gave way to morning."))}
    return {
        "world": worlds,
        "explainer": topics,
        "boulder": boulder,
        "quiz": quizzes,
        "checklist": checklists,
        "ayah": {i["ref"]: i for i in quran if i["kind"] == "ayah"},
        "dua": {i["ref"]: i for i in quran if i["kind"] == "dua"},
        "hadith": hadith,
        "hadith_all": hadith_all,
        "tasbih": {s["id"]: s for s in dhikr["sets"]},
        "story": stories,
        "dhikr_lib": dhikr["dhikr"],
    }


# ------------------------------------------------------------------ scheduling

def published(history):
    return [h for h in history if h.get("status") == "published"]


def due_slot(history, cfg, now):
    """Earliest slot of today that has not been published yet and is due (not more than max_lateness hours late)."""
    today = now.strftime("%Y-%m-%d")
    done = {h.get("slot") for h in published(history) if h.get("date") == today}
    tries = {}
    for h in history:
        if h.get("date") == today and h.get("status") == "failed":
            tries[h.get("slot")] = tries.get(h.get("slot"), 0) + 1
    late = timedelta(hours=cfg.get("max_lateness_hours", 9))
    for slot in sorted(cfg["slots"], key=lambda s: s["time"]):
        if slot["id"] in done or tries.get(slot["id"], 0) >= 2:
            continue
        hh, mm = map(int, slot["time"].split(":"))
        start = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if start <= now <= start + late:
            return slot
    return None


def pick_kind(slot, history):
    n = sum(1 for h in published(history) if h.get("slot") == slot["id"])
    return slot["kinds"][n % len(slot["kinds"])]


def _h(s):
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)


def pick_key(kind, pools, history, today, force_key=None):
    """Least recently used item of the pool; never-used items first, shuffled by date so the order is not predictable."""
    if force_key:
        return force_key
    keys = list(pools[kind].keys())
    last = {}
    for i, h in enumerate(published(history)):
        if h.get("kind") == kind or (kind in ("ayah", "dua") and h.get("kind") in ("ayah", "dua")):
            last[h.get("key")] = i
    keys.sort(key=lambda k: (last.get(k, -1), _h(k + today)))
    return keys[0]


def default_format(kind):
    return {"tasbih": "reel", "story": "reel", "quiz": "reel", "checklist": "reel", "explainer": "reel", "boulder": "reel", "world": "reel", "hadith": "carousel"}.get(kind, "reel")


# ------------------------------------------------------------------ captions

def hashtags(kind, cfg):
    h = cfg["hashtags"]
    tags = h.get(kind, []) + h["base"]
    seen, out = set(), []
    for t in tags:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return " ".join(out[: cfg.get("max_hashtags", 11)])


def caption(kind, item, cfg, dhikr_lib=None, pools=None):
    handle = cfg["handle"]
    tags = hashtags(kind, cfg)
    cta = f"Save this and share it with someone you love 🤍\nFollow {handle} for a daily reminder."
    if kind == "tasbih":
        names = [dhikr_lib[k]["tr"] for k in item["items"]]
        n = item["count"]
        body = f"{item['title']} 🤍\n\nCount along with the beads:\n" + "\n".join(f"{n}× {x}" for x in names)
        if item.get("source"):
            body += f"\n\nThe sunnah is 33 of each after every prayer: repeat this 3 times ({item['source']})."
    elif kind == "explainer":
        refs = [ch["quote"]["ref"] for ch in item["chapters"] if ch.get("quote")]
        steps = [ch["heading"] for ch in item["chapters"][1:-1]]
        body = f"{item['title']} ✨\n\n" + "\n".join(f"• {s}" for s in steps) + "\n\nSources: " + ", ".join(refs) + "\n\nWhich one do you need most today? Tell us below 👇"
    elif kind == "world":
        body = (f"{item['tr']} — {item['en']}\n\nWatch the world change with every dhikr. Say it slowly and count along (33).\n"
                "The sunnah is 33 each after every prayer (Sahih Muslim 597).")
    elif kind == "boulder":
        body = (f"{item['tr']} — {item['en']}\n\nOne small strike at a time. Say it slowly and count along with the reel (33).\n"
                "The sunnah is 33 each after every prayer (Sahih Muslim 597).")
    elif kind == "checklist":
        body = f"{item['title']} ✅\n\nSay each one slowly and tick along:\n" + "\n".join(f"✔ {pools['dhikr_lib'][k]['tr']} — {pools['dhikr_lib'][k]['en']}" for k in item["items"])
    elif kind == "quiz":
        from .story import ending_content
        e = ending_content(item["ending"], pools)
        quote = e["english"] if e["english"].startswith("“") else f"“{e['english']}”"
        body = f"{item['scenario']} {item['ask']}\n\nA, B or C? Tell us below 👇\n\n{quote}\n— {e['ref']}"
    elif kind == "story":
        from .story import ending_content
        e = ending_content(item["ending"], pools)
        quote = e["english"] if e["english"].startswith("“") else f"“{e['english']}”"
        body = f"{item['hook']}\n\n{quote}\n— {e['ref']}"
    elif kind in ("ayah", "dua"):
        head = f"{item['title']}\n\n" if item.get("title") else ""
        body = f"{head}{item['english']}\n\n— Surah {item['surah_name']} ({item['ref']}), Saheeh International"
    else:
        from .carousel import split_hadith
        _, text = split_hadith(item["text"])
        src = " · ".join(item.get("sources") or [])
        body = f"“{text}”\n\n— {item['collection']}, Hadith {item['number']}" + (f" ({src})" if src else "")
    return f"{body}\n\n{cta}\n\n{tags}"
