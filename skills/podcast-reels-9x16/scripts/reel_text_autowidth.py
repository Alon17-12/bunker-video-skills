# -*- coding: utf-8 -*-
"""Free the text box of caption / super materials: `fixed_width -1` (auto), like every caption project Alon
approved by hand (צומת 20 לקוח I, 0922 titles). Materials cloned from a CapCut auto-caption carry
`type subtitle` + `fixed_width 377.8` — a FIXED box that wraps at ≈ fixed_width × 1.2 canvas px (0923 r6:
«3 טיפים» at 516 px broke mid-word into «3 טיפי / ם»; 0922 captions had 617.4 → the "770 px wrap" that was
mistaken for a font calibration). With -1 the only wrap is `line_max_width` (0.82 × 1080 = 886 px).

    python reel_text_autowidth.py "<project>" [--tracks כתוביות,supers] [--write]
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--tracks", default="כתוביות,supers"); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); tm = {m["id"]: m for m in d["materials"]["texts"]}
names = [x.strip() for x in A.tracks.split(",")]; n = 0; seen = set()
for t in d["tracks"]:
    if t["type"] != "text" or (t.get("name") or "") not in names: continue
    for s in t["segments"]:
        m = tm[s["material_id"]]
        if m["id"] in seen: continue
        seen.add(m["id"])
        if m.get("fixed_width") != -1.0 or m.get("fixed_height") != -1.0: m["fixed_width"] = -1.0; m["fixed_height"] = -1.0; n += 1
    print(f"  track {t.get('name')!r}: {len(t['segments'])} segments")
print(f"fixed_width → -1 on {n} materials")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
