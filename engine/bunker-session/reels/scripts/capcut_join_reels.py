#!/usr/bin/env python3
"""Join two consecutive reels of one CapCut reels project into one (תוכן הבונקר לממומן, 24.10.2026: «הוק 2» is a separate
take — built as its own reel, then glued onto the body reel that follows it).

    capcut_join_reels.py "<project>" "<session with capcut-layout.json>" <reel index of the FIRST, 0-based> [--write]

The second reel's divider card (photo on the main track) and its title are removed and everything after them moves left by
the card's length on every track; the layout's two entries become one. CapCut must be closed.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402

US = 1_000_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("session"); ap.add_argument("first", type=int); ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    P = capcut.DRAFTS_DIR / a.project
    d = json.loads(capcut._draft_file(P).read_text())
    lp = Path(a.session) / "רילס/capcut-layout.json"
    lay = json.loads(lp.read_text())
    r1, r2 = lay["reels"][a.first], lay["reels"][a.first + 1]
    vids = {m["id"]: m for m in d["materials"]["videos"]}
    main_t = next(t for t in d["tracks"] if t["type"] == "video" and not t.get("name"))
    card = next(s for s in main_t["segments"] if vids.get(s["material_id"], {}).get("type") == "photo"
                and abs((s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / US - r2["start"]) < 0.05)
    c0, cd = card["target_timerange"]["start"], card["target_timerange"]["duration"]
    removed = 0
    for t in d["tracks"]:
        keep = []
        for s in t["segments"]:
            st = s["target_timerange"]["start"]
            if s is card or (t["type"] == "text" and t.get("name") == "כותרות" and c0 - 1000 <= st < c0 + cd):
                removed += 1; continue
            if st >= c0 + cd - 1000:
                s["target_timerange"]["start"] -= cd
            keep.append(s)
        t["segments"] = keep
    d["duration"] = int(d["duration"]) - cd
    sh = cd / US
    joined = dict(r1, end=round(r2["end"] - sh, 6), id=r1["id"] + "+" + r2["id"])
    rest = [dict(r, start=round(r["start"] - sh, 6), end=round(r["end"] - sh, 6)) for r in lay["reels"][a.first + 2:]]
    lay["reels"] = lay["reels"][:a.first] + [joined] + rest
    print(json.dumps({"removed": removed, "card_s": sh, "joined": [joined["start"], joined["end"]]}, ensure_ascii=False))
    if not a.write:
        return
    if capcut.capcut_running():
        raise SystemExit("⛔ CapCut פתוח")
    capcut._backup(P); capcut._atomic_write(P, d)
    lp.write_text(json.dumps(lay, ensure_ascii=False, indent=1), encoding="utf-8")
    print("✓ נכתב")


if __name__ == "__main__":
    main()
