# -*- coding: utf-8 -*-
"""Repoint materials whose `path` still names the white card's cached image at the file of the same
material_name in the draft folder. 0919 (29.09): every ccstudio material was cloned from «白» and kept the
card's path in CapCut's online cache, so the clip was literally the white image — a local identity alone
(reel_localize_materials.py) does not fix that. Paths are written absolute into the draft folder, the way
a hand-imported file is stored.

    python reel_repoint_materials.py "<project>" [--write]
"""
import argparse, json, os, re, subprocess, sys
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text())
def resolve(p): return str(D / p.split("_##/", 1)[1]) if p.startswith("##_draftpath_placeholder") else p
def probe(p):
    r = subprocess.run([str(paths.FFMPEG), "-hide_banner", "-i", p], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r); dur = (int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])) if m else None
    w = re.search(r"Video: .*?, (\d{2,5})x(\d{2,5})", r); return dur, (int(w[1]), int(w[2])) if w else None
fixed = []
for m in d["materials"]["videos"]:
    n = m.get("material_name") or ""; p = m.get("path") or ""; local = D / n
    if n == "白" or not local.exists(): continue
    if os.path.realpath(resolve(p)) == os.path.realpath(str(local)): continue
    m["path"] = str(local); dur, wh = probe(str(local))
    if m.get("type") == "video" and dur: m["duration"] = int(round(dur * 1e6))
    if wh: m["width"], m["height"] = wh
    fixed.append((n, p[:60], dur, wh))
for n, p, dur, wh in sorted(set(fixed)): print(f"  {n:34} was → {p}… now draft-local, dur {dur} {wh}")
print(f"repointed {len(fixed)} materials")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
