# -*- coding: utf-8 -*-
"""A b-roll layer for a 9:16 reel project: full-frame clips (or framed stills) on ONE video track that
sits right above the adjust layer and below every text track, muted, hard cut in and out, a quick
1.08→1.0 settle on a clip and a slow 1.0→1.06 push on a still. Nothing else — no whoosh, no duck, no
inset: "one device per moment" (0919 v2.1 lesson), and the bed here is already 16 dB under the voice.

    python reel_broll.py "<project>" --items items.json [--write]

items.json: [{"file": "ccstudio-broll-r1-tenant.mp4", "t": 13.2, "dur": 4.0, "off": 0.3, "why": "«תבוא תתקן את הזה»"}, …]
An item with "overlay": {"scale": 0.5, "x": 0.6, "y": 0.25} is a small element beside the head (emoji / sticker PNG):
it pops in (0.6→1.06→1.0 over 0.36 s) and sits still; `scale` is the fraction of the canvas width it covers.
`file` is inside the draft folder (copied there beforehand — the Media panel wants it there too); a .png
is a photo material. Idempotent: an existing track named `broll` is torn down first (its materials too).
Every item is literal to the sentence it sits on — that is the rule that survived 0910 round 2
("רוב הבירולס לא מדויקים למה שנאמר") — and the `why` field is the record of which sentence.
"""
import argparse, copy, json, os, re, subprocess, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
US = 1_000_000; FF = str(paths.FFMPEG)
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--items", required=True); ap.add_argument("--name", default="broll", help="track name (r8: a second overlay track `titles` for rendered motion titles above the b-roll)"); ap.add_argument("--under-adjust", action="store_true", help="put the track BELOW the adjust layer so his LUT/grade applies to the b-roll too (0923 r4: phone footage next to graded footage)"); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; items = json.load(open(A.items))
d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]; FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR)
nid = lambda: str(uuid.uuid4()).upper()
byid = {}
for k, v in mats.items():
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict) and "id" in m: byid[m["id"]] = (k, m)
def probe(path):
    r = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r); dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0
    wh = re.search(r"(\d{3,5})x(\d{3,5})", r); return int(wh.group(1)), int(wh.group(2)), int(round(dur * US))
# tear down a previous run
gone = [t for t in d["tracks"] if t.get("name") == A.name]
dead = {s["material_id"] for t in gone for s in t["segments"]} | {r for t in gone for s in t["segments"] for r in s.get("extra_material_refs", [])}
for k in list(mats):
    if isinstance(mats[k], list): mats[k] = [m for m in mats[k] if not (isinstance(m, dict) and m.get("id") in dead)]
d["tracks"] = [t for t in d["tracks"] if t not in gone]
vm = {m["id"]: m for m in mats["videos"]}
vt = [t for t in d["tracks"] if t["type"] == "video" and t["segments"]]
foot = next(s for s in vt[0]["segments"] if vm[s["material_id"]].get("type") == "video"); fmat = vm[foot["material_id"]]
card = next((s for s in vt[0]["segments"] if vm[s["material_id"]].get("type") == "photo"), None); cmat = vm[card["material_id"]] if card else None
def clone_refs(seg):
    out = []
    for r in seg.get("extra_material_refs", []):
        if r in byid and byid[r][0] != "material_animations":
            k, m = byid[r]; m2 = copy.deepcopy(m); m2["id"] = nid(); mats[k].append(m2); out.append(m2["id"])
    return out
def kf(t, v, curve="CurveInOut"): return {"id": nid(), "curveType": curve, "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def group(prop, keys): return {"id": nid(), "material_id": "", "property_type": prop, "keyframe_list": keys}
track = {"attribute": 0, "flag": 0, "id": nid(), "is_default_name": False, "name": A.name, "segments": [], "type": "video"}
ri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
for it in items:
    path = D / it["file"]
    if not path.exists(): print("  ⚠️ missing:", it["file"]); continue
    w, h, dur_us = probe(path); is_photo = path.suffix.lower() in (".png", ".jpg", ".jpeg")
    tpl_seg, tpl_mat = (card, cmat) if is_photo and card else (foot, fmat)
    m = copy.deepcopy(tpl_mat); m.update({"id": nid(), "path": str(path), "material_name": path.name, "width": w, "height": h, "duration": dur_us if not is_photo else 10_800_000_000,
                                          "type": "photo" if is_photo else "video", "local_material_id": "", "has_audio": False, "crop_scale": 1.0,
                                          "crop": {"upper_left_x": 0.0, "upper_left_y": 0.0, "upper_right_x": 1.0, "upper_right_y": 0.0, "lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0, "lower_right_y": 1.0}})
    if m.get("matting"): m["matting"] = {"flag": 0, "has_use_quick_brush": False, "has_use_quick_eraser": False, "interactiveTime": [], "path": "", "strokes": []}
    if is_photo: m.update({"material_id": "", "category_id": "", "category_name": "local", "source": 0, "check_flag": 63043327})   # a LOCAL photo: the card is an online material and CapCut re-links any clone of it to the cached white image (0923 r4: every badge / title / arrow rendered as a white square)
    mats["videos"].append(m)
    t0 = snap(it["t"] * US); L = snap(it["dur"] * US); off = snap(it.get("off", 0.0) * US)
    if not is_photo and off + L > dur_us: L = dur_us - off
    s = copy.deepcopy(tpl_seg); ri += 1
    s.update({"id": nid(), "material_id": m["id"], "extra_material_refs": clone_refs(tpl_seg), "render_index": ri, "speed": 1.0, "volume": 0.0, "last_nonzero_volume": 1.0, "keyframe_refs": [],
              "target_timerange": {"start": t0, "duration": L}, "source_timerange": {"start": off, "duration": L}})
    # a 1080×1920 asset fills the canvas at scale 1; anything else is scaled to cover
    cover = max(1080 / w, 1920 / h) / min(1080 / w, 1920 / h) if (w, h) != (1080, 1920) else 1.0
    ov = it.get("overlay")   # {"scale": 0.5, "x": 0.6, "y": 0.25}: a small element beside the head (emoji pop, sticker) — pops 0.6→1.06→1.0, sits still, no cover scaling
    if ov: base_sc = ov["scale"] * (1080 / w); px, py = ov.get("x", 0.0), ov.get("y", 0.0); sc = [kf(off, base_sc * 0.6, "CurveOut"), kf(off + snap(0.22 * US), base_sc * 1.06, "CurveInOut"), kf(off + snap(0.36 * US), base_sc, "CurveInOut"), kf(off + L, base_sc)]
    elif is_photo: px, py = it.get("x", 0.0), it.get("y", 0.0); sc = [kf(off, cover * 1.0, "CurveIn"), kf(off + L, cover * 1.06)]
    else: px, py = it.get("x", 0.0), it.get("y", 0.0); sc = [kf(off, cover * 1.08, "CurveOut"), kf(off + snap(0.5 * US), cover * 1.0, "CurveOut"), kf(off + L, cover * 1.0)]   # "x"/"y": pan a cover-scaled wide clip onto the subject (Alon 23.09: a wide two-shot cropped to nothing; and he wants the position draggable in CapCut — so the clip stays wide, the pan is a transform)
    s["clip"] = {"scale": {"x": sc[0]["values"][0], "y": sc[0]["values"][0]}, "rotation": 0.0, "transform": {"x": px, "y": py}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    s["common_keyframes"] = [group("KFTypeScaleX", sc), group("KFTypeScaleY", [dict(k, id=nid()) for k in sc]), group("KFTypePositionX", [kf(off, px), kf(off + L, px)]), group("KFTypePositionY", [kf(off, py), kf(off + L, py)])]
    track["segments"].append(s); print(f"  broll {t0/US:7.2f} +{L/US:.1f}s  {path.name:36} {'photo' if is_photo else 'video'} {w}x{h}  — {it.get('why', '')}")
ss = sorted(track["segments"], key=lambda s: s["target_timerange"]["start"])
ov = sum(1 for a, b in zip(ss, ss[1:]) if b["target_timerange"]["start"] < a["target_timerange"]["start"] + a["target_timerange"]["duration"])
adj = next(i for i, t in enumerate(d["tracks"]) if t["type"] == "adjust")
if A.name != "broll" and any(t.get("name") == "broll" for t in d["tracks"]): pos = next(i for i, t in enumerate(d["tracks"]) if t.get("name") == "broll") + 1   # a second overlay track sits right above the b-roll
else: pos = adj if A.under_adjust else adj + 1
d["tracks"].insert(pos, track)
print(f"broll {len(track['segments'])} items | overlaps {ov} | tracks {[t.get('name') or t['type'] for t in d['tracks']]}")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
