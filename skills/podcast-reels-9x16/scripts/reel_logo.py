# -*- coding: utf-8 -*-
"""One logo on a 9:16 reel project, over footage only (never over the white cards), on its own `logo` track.

    python reel_logo.py "<project>" --png /path/logo.png --scale 0.43 --y -0.40 [--x 0] [--name logo] [--write]

Geometry is the 0910 promo pair (Alon moved them on sight): captions y −0.19 and the logo y −0.40, a 4 %
gap, the mark ≈ 30 % of the canvas width; `references/brand-layer.md` has the two slots of the podcast
reels (38–40 % / 61–62 % W at 72 % H) for a show/guest pair. The file is copied into the draft folder
(`ccstudio-<name>.png`); the material is cloned from the project's own white-card photo so every field
CapCut expects comes along — with the online identity (`material_id`, `category_id`, `source`) cleared, otherwise CapCut
re-links the clone to the card's cached image on open and the logo renders as a white box (0923). Segments are the complement of the card spans on the base track. Idempotent:
tears its own track down first. Read-only without --write.
"""
import argparse, copy, json, os, shutil, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--png", required=True); ap.add_argument("--scale", type=float, required=True)
ap.add_argument("--x", type=float, default=0.0); ap.add_argument("--y", type=float, required=True); ap.add_argument("--name", default="logo"); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]
nid = lambda: str(uuid.uuid4()).upper()
byid = {}
for k, v in mats.items():
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict) and "id" in m: byid[m["id"]] = (k, m)
gone = [t for t in d["tracks"] if t.get("name") == A.name]
dead = {s["material_id"] for t in gone for s in t["segments"]} | {r for t in gone for s in t["segments"] for r in s.get("extra_material_refs", [])}
for k in list(mats):
    if isinstance(mats[k], list): mats[k] = [m for m in mats[k] if not (isinstance(m, dict) and m.get("id") in dead)]
d["tracks"] = [t for t in d["tracks"] if t not in gone]
vm = {m["id"]: m for m in mats["videos"]}
base = [t for t in d["tracks"] if t["type"] == "video"][0]
card = next(s for s in base["segments"] if vm[s["material_id"]].get("type") == "photo")
from PIL import Image
dst = D / f"ccstudio-{A.name}.png"; shutil.copy(A.png, dst); w, h = Image.open(dst).size
m = copy.deepcopy(vm[card["material_id"]]); m.update({"id": nid(), "path": str(dst), "material_name": dst.name, "width": w, "height": h, "duration": 10_800_000_000, "local_material_id": "",
          "material_id": "", "category_id": "", "category_name": "local", "source": 0, "check_flag": 63043327})   # a LOCAL photo: the card is an online material and CapCut re-links any clone of it to the cached white image on open (0923: the logo rendered as a white box)
mats["videos"].append(m)
def clone_refs(seg):
    out = []
    for r in seg.get("extra_material_refs", []):
        if r in byid and byid[r][0] != "material_animations":
            k, mm = byid[r]; m2 = copy.deepcopy(mm); m2["id"] = nid(); mats[k].append(m2); out.append(m2["id"])
    return out
# footage spans = complement of the card spans over the base track
segs = sorted(base["segments"], key=lambda s: s["target_timerange"]["start"]); spans = []
for s in segs:
    if vm[s["material_id"]].get("type") == "photo": continue
    a = s["target_timerange"]["start"]; b = a + s["target_timerange"]["duration"]
    if spans and abs(spans[-1][1] - a) <= 1: spans[-1][1] = b
    else: spans.append([a, b])
track = {"attribute": 0, "flag": 0, "id": nid(), "is_default_name": False, "name": A.name, "segments": [], "type": "video"}
ri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
for a, b in spans:
    s = copy.deepcopy(card); ri += 1
    s.update({"id": nid(), "material_id": m["id"], "extra_material_refs": clone_refs(card), "render_index": ri, "volume": 0.0, "last_nonzero_volume": 1.0, "keyframe_refs": [], "common_keyframes": [],
              "target_timerange": {"start": a, "duration": b - a}, "source_timerange": {"start": 0, "duration": b - a}})
    s["clip"] = {"scale": {"x": A.scale, "y": A.scale}, "rotation": 0.0, "transform": {"x": A.x, "y": A.y}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    track["segments"].append(s)
# above every video/adjust track, below the text tracks
pos = max(i for i, t in enumerate(d["tracks"]) if t["type"] in ("video", "adjust")) + 1; d["tracks"].insert(pos, track)
print(f"logo {dst.name} {w}x{h} · rendered width ≈ {1080*A.scale:.0f}px ({A.scale*100:.0f}% W) · {len(spans)} footage spans · tracks {[t.get('name') or t['type'] for t in d['tracks']]}")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
