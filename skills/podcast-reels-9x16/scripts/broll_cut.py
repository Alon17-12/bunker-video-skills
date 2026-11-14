# -*- coding: utf-8 -*-
"""Cut b-roll work copies from catalogued raw clips (broll_catalog.py) straight into a draft folder, and
emit the items.json that reel_broll.py takes.

    python broll_cut.py "<project>" --catalog <catalog_dir> --plan plan.json --items out_items.json [--only 3,7]

plan.json: [{"i": 372, "t": 9.65, "dur": 2.8, "off": 1.8, "name": "b1-arrive", "why": "«שמגיעים לאולפן»"}, …]
   i     catalog index (or "file": a path relative to the catalog root)
   t     project time the item starts at; "off" is the offset INTO THE RAW CLIP; "dur" the on-screen length
   any other keys (overlay, x, y) are copied through to the item
Output: ccstudio-broll-<name>.mp4 in the draft folder — 1080×1920 cover-crop, H.264 CRF 18, no audio, source
fps kept, dur + 0.4 s of tail so reel_broll's snap never reads past the file. iPhone HDR (HLG / PQ, bt2020)
is tone-mapped to bt709 SDR with zscale+tonemap(hable); without that the clip renders washed-out and grey
in CapCut next to SDR footage. Items get "off": 0 (the offset is baked into the copy). Idempotent per name.
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
FF = str(paths.FFMPEG)
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--catalog", required=True); ap.add_argument("--plan", required=True); ap.add_argument("--items", required=True); ap.add_argument("--only", default="")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; cat = json.loads((Path(A.catalog).expanduser() / "catalog.json").read_text()); root = Path(cat["root"]); byi = {it["i"]: it for it in cat["items"]}
plan = json.load(open(A.plan)); only = {int(x) for x in A.only.split(",") if x}
def info(p):
    r = subprocess.run([FF, "-hide_banner", "-i", str(p)], capture_output=True, text=True).stderr
    hdr = bool(re.search(r"arib-std-b67|smpte2084|bt2020", r)); return hdr
items = []
for k, it in enumerate(plan):
    src = root / (it["path"] if "path" in it else byi[it["i"]]["path"]); name = it["name"]; out = D / f"ccstudio-broll-{name}.mp4"
    if only and k not in only: pass
    elif out.exists() and it.get("keep_existing", True) and not it.get("recut"): print(f"  = {out.name} exists")
    else:
        hdr = info(src); off = float(it.get("off", 0.0)); L = float(it["dur"]) + 0.4
        cx = float(it.get("cx", 0.5))   # horizontal crop centre (0..1) for wide sources — the subject is rarely in the middle of a 16:9 frame
        vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:(iw-1080)*{cx:.3f}:(ih-1920)/2"
        if hdr: vf = "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p," + vf
        else: vf += ",format=yuv420p"
        cmd = [FF, "-y", "-loglevel", "error", "-ss", f"{off:.3f}", "-i", str(src), "-t", f"{L:.3f}", "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-an", "-movflags", "+faststart", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode: print(f"  ✗ {name}: {r.stderr.strip()[-300:]}"); continue
        print(f"  ✓ {out.name:40} from {src.name:18} off {off:5.1f} +{L:.1f}s {'HDR→SDR' if hdr else 'SDR'}")
    item = {kk: v for kk, v in it.items() if kk not in ("i", "path", "name", "off", "recut", "keep_existing", "cx", "anchor")}; item.update({"file": out.name, "off": 0.0}); items.append(item)
json.dump(items, open(A.items, "w"), ensure_ascii=False, indent=1); print(f"items {len(items)} → {A.items}")
