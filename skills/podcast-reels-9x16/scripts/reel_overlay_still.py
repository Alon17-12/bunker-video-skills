# -*- coding: utf-8 -*-
"""Lay a still PNG (alpha) over a reel at given times, on its own video track, with an eased entrance and a gentle pulse
— the CTA button «לפרטים והצטרפות ↓» over the arrow at «כאן למטה» (לקוח M החמוד, 04.10). Motion is CapCut keyframes,
not a rendered clip, so the button stays editable (swap the PNG, move it, retime it) by hand.

    python reel_overlay_still.py "<project>" --file ccstudio-client-cta.png --at 32.17:2.30,75.50:2.97 \
        [--width-px 600] [--y-px 1075] [--track cta] [--template ccstudio-arrow-down.png] [--write]

Geometry: a material w×h on the 1080×1920 canvas fills at scale 1.0 = min(1080/w, 1920/h); `--width-px` sets the
on-screen width from that. y is the CENTRE in canvas px (transform.y = (960 − y)/960). Keys (all eased, first
CurveIn — the house rule): 0.62 → 1.04 @0.25 s → 1.0 @0.42 s, then 1.0 → 1.03 → 1.0 across the rest (one breath).
The segment is cloned from an existing still on the timeline (`--template`, a photo segment) so every CapCut-internal
field comes along. Idempotent: a track named `--track` is torn down first. register_media.py --write afterwards.
"""
import argparse, copy, json, os, struct, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--file", required=True); ap.add_argument("--at", required=True)
ap.add_argument("--width-px", type=float, default=600); ap.add_argument("--y-px", type=float, default=1075); ap.add_argument("--track", default="cta")
ap.add_argument("--template", default="ccstudio-arrow-down.png"); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]
FR = US / d.get("fps", 30.0); snap = lambda t: int(round(t / FR) * FR); nid = lambda: str(uuid.uuid4()).upper()
vm = {m["id"]: m for m in mats["videos"]}
# tear down a previous run
old = [t for t in d["tracks"] if t.get("name") == A.track]; dead = {x for t in old for s in t["segments"] for x in (s["material_id"], *s.get("extra_material_refs", []))}
for k, v in mats.items():
    if isinstance(v, list): mats[k] = [m for m in v if not (isinstance(m, dict) and m.get("id") in dead)]
d["tracks"] = [t for t in d["tracks"] if t not in old]; vm = {m["id"]: m for m in mats["videos"]}
tpl = next(s for t in d["tracks"] if t["type"] == "video" for s in t["segments"] if vm.get(s["material_id"], {}).get("material_name") == A.template)
tpl_track = next(t for t in d["tracks"] if tpl in t["segments"])
p = D / A.file; assert p.exists(), p
with open(p, "rb") as f: head = f.read(24)
assert head[:8] == b"\x89PNG\r\n\x1a\n", "PNG only"; w, h = struct.unpack(">II", head[16:24])
fill = min(1080 / w, 1920 / h); S = A.width_px / (w * fill); Y = (960 - A.y_px) / 960
m = copy.deepcopy(vm[tpl["material_id"]]); m.update({"id": nid(), "material_name": p.name, "path": str(p), "width": w, "height": h, "local_material_id": "", "material_id": "", "category_id": "", "category_name": "local", "source": 0})
mats["videos"].append(m)
def kf(t, v, curve="CurveInOut"): return {"id": nid(), "curveType": curve, "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def group(pt, keys): return {"id": nid(), "material_id": "", "property_type": pt, "keyframe_list": keys}
track = copy.deepcopy(tpl_track); track.update({"id": nid(), "name": A.track, "segments": [], "is_default_name": False, "flag": 0, "attribute": 0})
ri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
for spec in A.at.split(","):
    t0, L = (float(x) for x in spec.split(":")); t0 = snap(t0 * US); L = snap(L * US)
    s = copy.deepcopy(tpl); ri += 1; refs = []
    for r in tpl.get("extra_material_refs", []):
        for k, v in mats.items():
            if isinstance(v, list):
                src = next((x for x in v if isinstance(x, dict) and x.get("id") == r), None)
                if src is not None: c = copy.deepcopy(src); c["id"] = nid(); v.append(c); refs.append(c["id"]); break
    a, b, mid = snap(0.25 * US), snap(0.42 * US), (snap(0.42 * US) + L) // 2
    sc = [kf(0, S * 0.62, "CurveIn"), kf(a, S * 1.04), kf(b, S)] + ([kf(mid, S * 1.03), kf(L, S)] if L > b + snap(0.6 * US) else [kf(L, S)])
    s.update({"id": nid(), "material_id": m["id"], "extra_material_refs": refs, "render_index": ri, "keyframe_refs": [], "volume": 0.0,
              "target_timerange": {"start": t0, "duration": L}, "source_timerange": {"start": 0, "duration": L}})
    s["clip"] = {"scale": {"x": S, "y": S}, "rotation": 0.0, "transform": {"x": 0.0, "y": Y}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    s["common_keyframes"] = [group("KFTypeScaleX", sc), group("KFTypeScaleY", [dict(k, id=nid()) for k in sc]),
                             group("KFTypePositionX", [kf(0, 0.0, "CurveIn"), kf(L, 0.0)]), group("KFTypePositionY", [kf(0, Y, "CurveIn"), kf(L, Y)])]
    track["segments"].append(s); print(f"  + {t0/US:7.2f} +{L/US:.2f}s  {p.name}  scale {S:.4f} (≈{A.width_px:.0f}px) y {Y:+.4f} (centre {A.y_px:.0f}px)  keys {len(sc)}")
d["tracks"].insert(d["tracks"].index(tpl_track) + 1, track)
ss = sorted(track["segments"], key=lambda s: s["target_timerange"]["start"])
assert all(b_["target_timerange"]["start"] >= a_["target_timerange"]["start"] + a_["target_timerange"]["duration"] for a_, b_ in zip(ss, ss[1:])), "overlap"
print(f"{A.track}: {len(ss)} segments · tracks {[t.get('name') or t['type'] for t in d['tracks']]}")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
