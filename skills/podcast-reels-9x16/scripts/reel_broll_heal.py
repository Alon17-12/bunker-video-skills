# -*- coding: utf-8 -*-
"""Re-join b-roll pieces that reel_ripple.py split around a silence cut: two adjacent segments of the same
material on the `broll` track become one (the dropped 0.15–0.25 s of source is simply played through — the
work copies carry a 0.4 s tail). Otherwise every split piece gets its own click from reel_sound.py and a
sub-frame jump inside the insert (0923 r5: 7 splits → 7 stray clicks). Run before reel_sound.py.
    python reel_broll_heal.py "<project>" [--write]
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); FR = US / d.get("fps", 60.0)
vm = {m["id"]: m for m in d["materials"]["videos"]}; track = next(t for t in d["tracks"] if t.get("name") == "broll")
segs = sorted(track["segments"], key=lambda s: s["target_timerange"]["start"]); out = []; n = 0
for s in segs:
    if out and out[-1]["material_id"] == s["material_id"] and abs(s["target_timerange"]["start"] - (out[-1]["target_timerange"]["start"] + out[-1]["target_timerange"]["duration"])) <= FR:
        p = out[-1]; L = p["target_timerange"]["duration"] + s["target_timerange"]["duration"]; src_end = p["source_timerange"]["start"] + L
        if src_end > vm[s["material_id"]]["duration"]: L = vm[s["material_id"]]["duration"] - p["source_timerange"]["start"]
        p["target_timerange"]["duration"] = L; p["source_timerange"]["duration"] = L
        for g in p.get("common_keyframes", []):
            ks = sorted(g["keyframe_list"], key=lambda k: k["time_offset"])
            if ks: ks[-1]["time_offset"] = p["source_timerange"]["start"] + L
        n += 1; print(f"  joined {vm[s['material_id']]['material_name']} at {s['target_timerange']['start']/US:.2f}s")
    else: out.append(s)
track["segments"] = out; print(f"joined {n} splits | broll {len(out)} segments")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
