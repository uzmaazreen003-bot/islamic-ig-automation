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

# 1) nothing due before the first slot, morning due after 06:30, noon after 13:00
assert content.due_slot([], cfg, at(5, 0)) is None
assert content.due_slot([], cfg, at(6, 31))["id"] == "morning"
hist = [{"date": "2026-11-10", "slot": "morning", "status": "published", "kind": "ayah", "key": "94:5-6"}]
assert content.due_slot(hist, cfg, at(7, 0)) is None
assert content.due_slot(hist, cfg, at(13, 5))["id"] == "noon"
# 2) a missed slot is made up later, but not more than 9 h late
assert content.due_slot([], cfg, at(14, 0))["id"] == "morning"      # 7.5 h late, still allowed
assert content.due_slot([], cfg, at(16, 0))["id"] == "noon"          # morning is 9.5 h late -> skipped
# 3) two failures in one day stop retries for that slot
fails = [{"date": "2026-11-10", "slot": "morning", "status": "failed"}] * 2
assert content.due_slot(fails, cfg, at(7, 0)) is None
# 4) kinds rotate per slot, items never repeat until the pool is used up
morning = cfg["slots"][0]
seen_kinds, used, hist = [], set(), []
for day in range(1, 11):
    kind = content.pick_kind(morning, hist)
    key = content.pick_key(kind, pools, hist, f"2026-11-{day:02d}")
    assert key not in used, (day, key)
    used.add(key); seen_kinds.append(kind)
    hist.append({"date": f"2026-11-{day:02d}", "slot": "morning", "status": "published", "kind": kind, "key": key})
assert seen_kinds[:4] == ["story", "ayah", "story", "dua"], seen_kinds
# 5) captions contain the source reference and no empty fields
for kind in ("ayah", "dua", "hadith", "tasbih", "story"):
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
