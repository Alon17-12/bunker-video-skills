# -*- coding: utf-8 -*-
"""Repair the online-material trap: a video / photo material cloned from CapCut's white card («白», material_id
7106436387146108187, category «Trending», source 1) keeps the card's ONLINE identity, so CapCut re-links it to
the cached white image and the clip renders as a white box (0923 r4/r5: badges, titles, arrows; 0919: every
ccstudio b-roll, scrim, rule and logo — «הבירולס בכלל לא עובדים»). Anything with a real local file gets the
local identity: material_id "" · category_id "" · category_name "local" · source 0 · check_flag 63043327.

    python reel_localize_materials.py "<project>" [--write]

Read-only without --write; the card itself (no path / not on disk) is left alone. Idempotent.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text())
def resolve(p): return str(D / p.split("_##/", 1)[1]) if p.startswith("##_draftpath_placeholder") else p
fixed = []; skipped = []
for m in d["materials"]["videos"]:
    p = m.get("path") or ""
    online = m.get("source") == 1 or bool(m.get("material_id")) or (m.get("category_name") or "") not in ("", "local")
    if not online or (m.get("material_name") or "") == "白": continue   # the card IS the online material — leave it
    if not p or not os.path.exists(resolve(p)): skipped.append(m.get("material_name")); continue
    m.update({"material_id": "", "category_id": "", "category_name": "local", "source": 0, "check_flag": 63043327}); fixed.append(m.get("material_name"))
print(f"localized {len(fixed)} materials: {sorted(set(fixed))}")
print(f"left online (no local file): {sorted(set(skipped))}")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
