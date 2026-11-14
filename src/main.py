"""Entry point.

  python -m src.main plan  [--kind auto|tasbih|ayah|dua|hadith] [--format auto|reel|carousel] [--key REF] [--force]
  python -m src.main publish
  python -m src.main check

`plan` picks what is due, renders media into out/ and writes out/plan.json (history untouched).
`publish` posts out/plan.json to Instagram and records the result in data/history.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

from . import activity, boulder, world, carousel, explainer, narrate, cards, content, publish, story, story2, tasbih

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("IG_DATA_DIR") or os.path.join(ROOT, "data")
OUT = os.environ.get("IG_OUT_DIR") or os.path.join(ROOT, "out")


def load_json(name, default=None):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def gh_output(**kv):
    path = os.environ.get("GITHUB_OUTPUT")
    lines = "".join(f"{k}={v}\n" for k, v in kv.items())
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(lines)
    print("[output]", ", ".join(f"{k}={v}" for k, v in kv.items()))


def media_url(filename):
    base = os.environ.get("MEDIA_BASE_URL")
    if not base:
        repo = os.environ.get("GITHUB_REPOSITORY", "OWNER/REPO")
        base = f"https://raw.githubusercontent.com/{repo}/media"
    return f"{base.rstrip('/')}/{filename}"


def write_error(text):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "error.txt"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")


def cmd_plan(args):
    from PIL import features
    if not features.check("raqm"):
        write_error("Arabic text shaping (raqm/fribidi) is not available, so Arabic would render broken. "
                    "Install the system packages libraqm0 and libfribidi0.")
        print("[plan] raqm missing; refusing to render Arabic without it")
        return 1
    cfg = load_json("config.json")
    history = load_json("history.json", [])
    pools = content.load_pools(DATA)
    now = content.now_ist()
    today = now.strftime("%Y-%m-%d")

    if args.kind != "auto":
        slot = {"id": "manual", "kinds": [args.kind]}
    else:
        slot = None if args.force else content.due_slot(history, cfg, now)
        if slot is None and args.force:
            slot = {"id": "manual", "kinds": [cfg["slots"][0]["kinds"][0]]}
        if slot is None:
            print(f"[plan] nothing due right now ({now.strftime('%H:%M')} IST); today's posts are done or not yet due")
            gh_output(skip="true")
            return 0
    narrate.configure(cfg)
    kind = content.pick_kind(slot, history) if args.kind == "auto" else args.kind
    key = content.pick_key(kind, pools, history, today, args.key or None)
    item = pools[kind][key]
    fmt = args.format if args.format != "auto" else (slot.get("format") or content.default_format(kind))
    if kind in ("tasbih", "story", "quiz", "checklist", "explainer", "boulder", "world"):
        fmt = "reel"
    if kind == "hadith":
        fmt = "carousel"
    seed = len(content.published(history))
    handle = cfg["handle"]
    stem = f"{today}-{slot['id']}-{kind}-{key.replace(':', '_').replace('-', '_')}"

    os.makedirs(OUT, exist_ok=True)
    for old in os.listdir(OUT):
        p = os.path.join(OUT, old)
        if os.path.isfile(p):
            os.remove(p)
    print(f"[plan] {today} {now.strftime('%H:%M')} IST · slot {slot['id']} · {kind} · {key} · {fmt}")

    if kind == "tasbih":
        out = os.path.join(OUT, f"{stem}.mp4")
        with tempfile.TemporaryDirectory() as tmp:
            info = tasbih.make_reel(item, pools["dhikr_lib"], handle, out, seed=seed, workdir=tmp, voice_mode=cfg.get("dhikr_voice", "files"))
        files = [out]
    elif kind == "explainer":
        out = os.path.join(OUT, f"{stem}.mp4")
        with tempfile.TemporaryDirectory() as tmp:
            info = explainer.make_reel(item, handle, out, seed=seed, workdir=tmp, voice_on=cfg.get("story_voice", True))
        files = [out]
    elif kind == "world":
        out = os.path.join(OUT, f"{stem}.mp4")
        with tempfile.TemporaryDirectory() as tmp:
            info = world.make_reel(item, handle, out, seed=seed, workdir=tmp, count=cfg.get("boulder_count", 33), cycle=cfg.get("dhikr_seconds", 1.2))
        files = [out]
    elif kind == "boulder":
        out = os.path.join(OUT, f"{stem}.mp4")
        with tempfile.TemporaryDirectory() as tmp:
            info = boulder.make_reel(item, handle, out, seed=seed, workdir=tmp, count=cfg.get("boulder_count", 33), theme_name=item["theme"], cycle=cfg.get("dhikr_seconds", 1.2))
        files = [out]
    elif kind == "quiz":
        out = os.path.join(OUT, f"{stem}.mp4")
        with tempfile.TemporaryDirectory() as tmp:
            info = activity.make_quiz(item, story.ending_content(item["ending"], pools), handle, out, seed=seed, workdir=tmp, voice_on=cfg.get("story_voice", True))
        files = [out]
    elif kind == "checklist":
        out = os.path.join(OUT, f"{stem}.mp4")
        with tempfile.TemporaryDirectory() as tmp:
            info = activity.make_checklist(item, pools["dhikr_lib"], handle, out, seed=seed, workdir=tmp)
        files = [out]
    elif kind == "story":
        out = os.path.join(OUT, f"{stem}.mp4")
        with tempfile.TemporaryDirectory() as tmp:
            info = story2.make_reel(item, story.ending_content(item["ending"], pools), handle, out, seed=seed, workdir=tmp,
                                    voice_on=cfg.get("story_voice", True))
        files = [out]
    elif fmt == "reel":
        out = os.path.join(OUT, f"{stem}.mp4")
        with tempfile.TemporaryDirectory() as tmp:
            info = cards.make_reel(item, handle, out, seed=seed, workdir=tmp)
        files = [out]
    else:
        info = {}
        files = (carousel.hadith_slides if kind == "hadith" else carousel.ayah_slides)(item, handle, OUT, stem, seed=seed)
    print(f"[plan] rendered {fmt}: {info}")

    cap = content.caption(kind, item, cfg, pools["dhikr_lib"], pools)
    plan = {"date": today, "time_ist": now.strftime("%H:%M"), "slot": slot["id"], "kind": kind, "key": key, "format": fmt,
            "caption": cap, "files": files, "media_urls": [media_url(os.path.basename(f)) for f in files]}
    save_json(os.path.join(OUT, "plan.json"), plan)
    with open(os.path.join(OUT, "caption.txt"), "w", encoding="utf-8") as fh:
        fh.write(cap + "\n")
    gh_output(skip="false", format=fmt, kind=kind)
    print("---- caption ----")
    print(cap)
    return 0


def cmd_publish(args):
    cfg = load_json("config.json")
    history = load_json("history.json", [])
    with open(os.path.join(OUT, "plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    token = os.environ.get("IG_ACCESS_TOKEN", "")
    if not token:
        write_error("The GitHub secret IG_ACCESS_TOKEN is missing or empty.")
        return 1
    entry = {k: plan[k] for k in ("date", "time_ist", "slot", "kind", "key", "format")}
    try:
        media_id, permalink = publish.publish_plan(plan, cfg["ig_user_id"], token, cfg.get("video_method", "auto"))
    except publish.PublishError as exc:
        entry.update(status="failed", error=f"{exc.kind}: {exc}")
        history.append(entry)
        save_json(os.path.join(DATA, "history.json"), history)
        hint = {
            "token": "The Instagram access token was rejected (expired or revoked). In the Meta app dashboard: Use cases → Customize → "
                     "API setup with Unified login → Generate token for ruh_corner, then replace the IG_ACCESS_TOKEN secret.",
            "rate_limit": "Instagram's publishing limit was hit. The next scheduled run will try again.",
            "media_url": "Instagram could not download the media file from the repo's `media` branch.",
        }.get(exc.kind, "See the run log for details.")
        write_error(f"{exc}\n\n{hint}")
        print(f"[publish] FAILED: {exc}")
        return 1
    entry.update(status="published", media_id=media_id, permalink=permalink)
    history.append(entry)
    save_json(os.path.join(DATA, "history.json"), history)
    print(f"[publish] published {plan['format']} ({plan['kind']} {plan['key']}): {permalink or media_id}")
    return 0


def cmd_check(args):
    cfg = load_json("config.json")
    token = os.environ.get("IG_ACCESS_TOKEN", "")
    if not token:
        print("IG_ACCESS_TOKEN secret is empty or missing")
        return 1
    try:
        info = publish.call("GET", f"{publish.GRAPH}/{cfg['ig_user_id']}", token, params={"fields": "username,media_count"}, retries=1)
        used = publish.quota(cfg["ig_user_id"], token)
    except publish.PublishError as exc:
        print(f"Token check FAILED ({exc.kind}): {exc}")
        return 1
    print(f"OK: @{info.get('username')} · media_count={info.get('media_count')} · publishing quota used (24h)={used}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--kind", default="auto", choices=["auto", "tasbih", "ayah", "dua", "hadith", "story", "quiz", "checklist", "explainer", "boulder", "world"])
    p.add_argument("--format", default="auto", choices=["auto", "reel", "carousel"])
    p.add_argument("--key", default="")
    p.add_argument("--force", action="store_true")
    sub.add_parser("publish")
    sub.add_parser("check")
    args = ap.parse_args(argv)
    return {"plan": cmd_plan, "publish": cmd_publish, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
