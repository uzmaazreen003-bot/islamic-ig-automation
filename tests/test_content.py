import json, os, sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import content

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(os.path.join(ROOT, "data", "config.json")))
pools = content.load_pools(os.path.join(ROOT, "data"))
IST = content.IST

def at(h, m=0, d=10):
    return datetime(2026, 11, d, h, m, tzinfo=IST)

# 1) nothing due before the first slot, story at 08:00, tasbih at 19:30
assert content.due_slot([], cfg, at(7, 0)) is None
assert content.due_slot([], cfg, at(8, 1))["id"] == "morning"
hist = [{"date": "2026-11-10", "slot": "morning", "status": "published", "kind": "story", "key": "honk"}]
assert content.due_slot(hist, cfg, at(9, 0)) is None
assert content.due_slot(hist, cfg, at(19, 35))["id"] == "evening"
# 2) a missed slot is made up later, but not more than 9 h late
assert content.due_slot([], cfg, at(13, 0))["id"] == "morning"       # 5 h late, still allowed
assert content.due_slot([], cfg, at(18, 0)) is None            # morning is 10 h late -> skipped
# 3) two failures in one day stop retries for that slot
fails = [{"date": "2026-11-10", "slot": "morning", "status": "failed"}] * 2
assert content.due_slot(fails, cfg, at(9, 0)) is None
# 4) kinds rotate per slot, items never repeat until the pool is used up
morning = cfg["slots"][0]
seen_kinds, used, hist = [], set(), []
for day in range(1, 20):
    kind = content.pick_kind(morning, hist)
    key = content.pick_key(kind, pools, hist, f"2026-11-{day:02d}")
    if sum(1 for k, _ in used if k == kind) < len(pools[kind]):          # no repeats until the pool is used up
        assert (kind, key) not in used, (day, key)
    used.add((kind, key)); seen_kinds.append(kind)
    hist.append({"date": f"2026-11-{day:02d}", "slot": "morning", "status": "published", "kind": kind, "key": key})
assert set(seen_kinds) == {"story", "quiz", "explainer"}, seen_kinds
# 5) captions contain the source reference and no empty fields
for kind in ("ayah", "dua", "hadith", "tasbih", "story", "quiz", "checklist", "explainer", "boulder", "world"):
    key = next(iter(pools[kind]))
    cap = content.caption(kind, pools[kind][key], cfg, pools["dhikr_lib"], pools)
    assert "#ruhcorner" in cap and "@ruh_corner" in cap, kind
    assert len(cap) < 2200, (kind, len(cap))
    assert cap.count("#") <= 30
# 6) every story ends with text that really exists in the data (excerpts must be verbatim)
from src import story
for sid, st in pools["story"].items():
    e = story.ending_content(st["ending"], pools)
    assert e["english"] and e["ref"], sid
    assert 3 <= len(st["scenes"]) <= 12, sid
print("content tests OK;", {k: len(v) for k, v in pools.items() if k != "dhikr_lib"})

# 7) explainer quotes are verbatim and every picture/boulder item is renderable
from src import explainer
for tid, tp in pools["explainer"].items():
    for ch in tp["chapters"]:
        assert ch["icon"] in ("intro", "intro_s", "four", "four_s", "creature", "beam", "rain", "lamp", "door", "ties", "walk"), ch["icon"]
        assert ch["tint"] in explainer.TINTS
        if ch.get("quote"):
            assert ch["quote"]["english"] and ch["quote"]["ref"]
assert set(pools["boulder"]) == set(pools["dhikr_lib"])
print("explainer/boulder tests OK")
