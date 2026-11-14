# -*- coding: utf-8 -*-
"""Caption entrance = an eased overshoot pop written as scale keyframes on every card — the creator "pop"
(0.86 → 1.04 → 1.00 over ≈0.26 s, CurveInOut). Replaces the cached CapCut `Grow` preset, which Alon called
«רובוטית ומהירה» on 0923 r8 (a linear grow from nothing in 0.14 s). Keyframes on a text segment are seg-local
(`time_offset` from 0 — text has no source range), the pattern kinetic_headlines.py proved on 0910.

    python reel_caption_pop.py "<project>" [--track כתוביות] [--lo 0.86 --hi 1.04] [--t1 0.13 --t2 0.26] [--write]

Any animation wrapper (material_animations) the track's segments reference is dropped first — one device
per card. A card shorter than 1.6 × t2 gets its pop scaled to 60 % of its length. Idempotent.
"""
import argparse, json, os, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--track", default="כתוביות")
ap.add_argument("--lo", type=float, default=0.86); ap.add_argument("--hi", type=float, default=1.04); ap.add_argument("--t1", type=float, default=0.13); ap.add_argument("--t2", type=float, default=0.26); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]
FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR)
track = next(t for t in d["tracks"] if t.get("name") == A.track)
anim_ids = {m["id"] for m in mats.get("material_animations", [])}
dead = {r for s in track["segments"] for r in s.get("extra_material_refs", []) if r in anim_ids}
mats["material_animations"] = [m for m in mats.get("material_animations", []) if m["id"] not in dead]
def kf(t, v): return {"id": str(uuid.uuid4()).upper(), "curveType": "CurveInOut", "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def group(prop, keys): return {"id": str(uuid.uuid4()).upper(), "material_id": "", "property_type": prop, "keyframe_list": keys}
n = short = 0
for s in track["segments"]:
    s["extra_material_refs"] = [r for r in s.get("extra_material_refs", []) if r not in dead]
    L = s["target_timerange"]["duration"] / US; t1, t2 = A.t1, A.t2
    if L < 1.6 * t2: t2 = 0.6 * L; t1 = t2 * A.t1 / A.t2; short += 1
    keys = [(0.0, A.lo), (t1, A.hi), (t2, 1.0)]
    s["common_keyframes"] = [g for g in s.get("common_keyframes", []) if g["property_type"] not in ("KFTypeScaleX", "KFTypeScaleY")]
    s["common_keyframes"] += [group("KFTypeScaleX", [kf(snap(t * US), v) for t, v in keys]), group("KFTypeScaleY", [kf(snap(t * US), v) for t, v in keys])]
    s["clip"]["scale"] = {"x": A.lo, "y": A.lo}; n += 1
print(f"pop on {n} cards ({short} shortened) | dropped {len(dead)} animation wrappers | {A.lo}→{A.hi}→1.0 @ {A.t1}/{A.t2}s")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
