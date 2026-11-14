# -*- coding: utf-8 -*-
"""Shrink a portrait selfie inside the 9:16 frame and fill the rest with a blurred copy of itself — the
"blurred background" layout, for phone footage whose face is too big for a caption band.

Why (לקוח M, 04.10): WhatsApp selfies at 478×850 — head width 0.44 W, chin at 0.72–0.78 H. At scale 1.0 there
is no clear caption band, and Meta's Reels ad safe zone keeps the bottom ~35 % free of text. At 0.80 the head is
the house 0.355 W, the eye line goes to 0.34 H, the chin to ≈ 0.52 H, and captions sit at 0.63 H.

    python reel_blur_frame.py "<project>" --plate ccstudio-client-blurbg.mp4 --eyes 5:0.48,43.9:0.51,83.4:0.53 \
        [--scale 0.80] [--anchor 0.34] [--plate-scale 1.04] [--write]

--plate  a pre-blurred copy of the base camera's work copy (same duration, same clock), made with ffmpeg:
         `scale=270:480,gblur=sigma=14,scale=1080:1920,eq=brightness=-0.10:saturation=0.85`. Baked, because the
         CapCut `Blur` effect cannot be injected once its cache is cleared (devices.blur_effect raises).
--eyes   per reel: <reel footage start>:<source eye line as a fraction of the SOURCE height>, measured with YuNet.
Track 0 footage segments become the PLATE (material swapped, static at --plate-scale, volume 0, motion keys
dropped); a NEW video track `client sharp` right above it carries a copy of every footage segment — the original
material, volume, keyframes — with the whole layer mapped by s' = scale·s, T' = scale·T + dy (dy puts the eyes
at --anchor). Run it LAST among the camera stages (after ripple, framing, punches): a later ripple would split
both tracks fine, but punch scripts read track 0 only. Cards on track 0 are left alone. Idempotent per run:
refuses when a track named `client sharp` exists.
"""
import argparse, copy, json, os, re, subprocess, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
US = 1_000_000; FF = str(paths.FFMPEG); nid = lambda: str(uuid.uuid4()).upper()
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--plate", required=True); ap.add_argument("--eyes", required=True)
ap.add_argument("--scale", type=float, default=0.80); ap.add_argument("--anchor", type=float, default=0.34); ap.add_argument("--plate-scale", type=float, default=1.04)
ap.add_argument("--name", default="client sharp"); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]
assert not any(t.get("name") == A.name for t in d["tracks"]), f"a track named {A.name!r} exists — restore the base first"
vm = {m["id"]: m for m in mats["videos"]}; idx = capcut._materials_index(d)
eyes = sorted((float(a), float(b)) for a, b in (x.split(":") for x in A.eyes.split(",")))
CH = d["canvas_config"]["height"]
def dy_for(t):
    e = [b for a, b in eyes if a <= t + 0.01][-1]
    eye_px = CH / 2 + A.scale * (e * CH - CH / 2); return (eye_px - A.anchor * CH) / (CH / 2), e
def probe(p):
    r = subprocess.run([FF, "-i", str(p)], capture_output=True, text=True).stderr; m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r)
    wh = re.search(r"(\d{3,5})x(\d{3,5})", r); return int(wh.group(1)), int(wh.group(2)), int(round((int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) * US))
plate_path = D / A.plate; assert plate_path.exists(), plate_path; pw, ph, pdur = probe(plate_path)
t0 = d["tracks"][0]; foot = [s for s in t0["segments"] if vm[s["material_id"]].get("type") == "video" and vm[s["material_id"]].get("path")]
cam = vm[foot[0]["material_id"]]; assert all(s["material_id"] == cam["id"] for s in foot), "more than one camera material on track 0"
pm = copy.deepcopy(cam); pm.update({"id": nid(), "path": str(plate_path), "material_name": plate_path.name, "width": pw, "height": ph, "duration": pdur, "local_material_id": "",
                                     "material_id": "", "category_id": "", "category_name": "local", "source": 0, "check_flag": 63043327}); mats["videos"].append(pm)
assert pdur >= cam["duration"] - 50000, f"plate {pdur/US:.2f}s shorter than the camera copy {cam['duration']/US:.2f}s"
def clone_refs(seg):
    out = []
    for r in seg.get("extra_material_refs", []):
        if r in idx: k, m = idx[r]; c = copy.deepcopy(m); c["id"] = nid(); mats[k].append(c); out.append(c["id"])
    return out
sharp = copy.deepcopy(next(t for t in d["tracks"] if t["type"] == "video")); sharp.update({"id": nid(), "segments": [], "name": A.name, "is_default_name": False, "flag": 0, "attribute": 0})
ri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
for s in foot:
    t = s["target_timerange"]["start"] / US; dy, e = dy_for(t)
    c = copy.deepcopy(s); ri += 1; c.update({"id": nid(), "extra_material_refs": clone_refs(s), "render_index": ri, "keyframe_refs": []})
    sc = c["clip"]["scale"]; tr = c["clip"]["transform"]
    c["clip"]["scale"] = {"x": sc["x"] * A.scale, "y": sc["y"] * A.scale}; c["clip"]["transform"] = {"x": tr["x"] * A.scale, "y": tr["y"] * A.scale + dy}
    for g in c.get("common_keyframes", []):
        g["id"] = nid()
        for k in g["keyframe_list"]:
            k["id"] = nid()
            if g["property_type"] in ("KFTypeScaleX", "KFTypeScaleY", "KFTypePositionX"): k["values"] = [k["values"][0] * A.scale]
            elif g["property_type"] == "KFTypePositionY": k["values"] = [k["values"][0] * A.scale + dy]
    has_y = any(g["property_type"] == "KFTypePositionY" for g in c.get("common_keyframes", []))
    if c.get("common_keyframes") and not has_y:   # scale keys but no position keys: pin y so the shift holds on every key
        src0 = c["source_timerange"]["start"]; L = c["source_timerange"]["duration"]
        c["common_keyframes"].append({"id": nid(), "material_id": "", "property_type": "KFTypePositionY", "keyframe_list": [
            {"id": nid(), "curveType": "CurveInOut", "time_offset": src0, "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [c["clip"]["transform"]["y"]], "string_value": "", "graphID": ""},
            {"id": nid(), "curveType": "CurveInOut", "time_offset": src0 + L, "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [c["clip"]["transform"]["y"]], "string_value": "", "graphID": ""}]})
    sharp["segments"].append(c)
    # the original becomes the plate: blurred copy, static, silent
    s["material_id"] = pm["id"]; s["common_keyframes"] = [g for g in s.get("common_keyframes", []) if g["property_type"] not in ("KFTypeScaleX", "KFTypeScaleY", "KFTypePositionX", "KFTypePositionY")]
    s["clip"]["scale"] = {"x": A.plate_scale, "y": A.plate_scale}; s["clip"]["transform"] = {"x": 0.0, "y": 0.0}; s["volume"] = 0.0
    print(f"  {t:7.2f} +{s['target_timerange']['duration']/US:5.2f}s  eyes src {e:.2f} → dy {dy:+.3f} · sharp scale {c['clip']['scale']['x']:.3f} · keys {len(c.get('common_keyframes', []))}")
d["tracks"].insert(1, sharp)
bottom = lambda dy: (CH / 2) * (1 + A.scale) - dy * CH / 2
print(f"shots {len(foot)} · plate {plate_path.name} {pw}x{ph} · sharp bottom edge {min(bottom(dy_for(a)[0]) for a, _ in eyes):.0f}–{max(bottom(dy_for(a)[0]) for a, _ in eyes):.0f} px · tracks {[t.get('name') or t['type'] for t in d['tracks']]}")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
