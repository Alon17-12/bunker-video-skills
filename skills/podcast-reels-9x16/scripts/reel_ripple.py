# -*- coding: utf-8 -*-
"""Ripple-delete timeline ranges — the silence cuts Alon makes by hand inside a reel — across every track.

    python reel_ripple.py "<project>" --cuts 195.9:196.65,198.9:199.4,… [--write]

Ranges are project seconds, [a, b). For each track: a segment entirely inside a cut is dropped; footage
(camera layers, b-roll) that straddles a cut is SPLIT into two segments around it (source stays honest —
that is what his own cuts look like: reel 3 became five pieces); adjust, beds and titles that straddle a
cut are TRIMMED (their source keeps running, as CapCut's ripple does); captions are trimmed at the edge
and shifted. Everything later moves left by the cut's length. Keyframes live on source time: a straddling
footage segment keeps its keys, each piece gets an interpolated key on the new boundary (eased).

Where the cuts come from (0922 reel 5): pauses where BOTH mics sit under floor + 8 dB for ≥ 0.5 s, cut down
to ≈ 0.25 s (0.12 s kept before the cut, 0.13 s after) — Alon's own cuts on reels 1–4 removed pauses of
0.5–1.2 s whole, landing inside the silence. Read-only without --write.
"""
import argparse, copy, json, os, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--cuts", required=True); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project
d = json.loads((D / "draft_info.json").read_text()); FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR); nid = lambda: str(uuid.uuid4()).upper()
vm = {m["id"]: m for m in d["materials"]["videos"]}
cuts = sorted((snap(float(a) * US), snap(float(b) * US)) for a, b in (c.split(":") for c in A.cuts.split(",")))
for (a0, b0), (a1, b1) in zip(cuts, cuts[1:]): assert b0 <= a1, "cuts overlap"

def interp(keys, t):
    ks = sorted(keys, key=lambda k: k["time_offset"])
    if t <= ks[0]["time_offset"]: return ks[0]["values"][0]
    if t >= ks[-1]["time_offset"]: return ks[-1]["values"][0]
    for k0, k1 in zip(ks, ks[1:]):
        if k0["time_offset"] <= t <= k1["time_offset"]:
            f = (t - k0["time_offset"]) / max(1, k1["time_offset"] - k0["time_offset"]); return k0["values"][0] + f * (k1["values"][0] - k0["values"][0])
def kf(t, v): return {"id": nid(), "curveType": "CurveInOut", "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def trim_keys(seg, s0, s1):
    """keyframes of seg restricted to source [s0, s1] with eased boundary keys; clip set to the value at s0"""
    groups = []
    for g in seg.get("common_keyframes", []):
        v0 = interp(g["keyframe_list"], s0); v1 = interp(g["keyframe_list"], s1)
        inner = [dict(k, id=nid()) for k in g["keyframe_list"] if s0 < k["time_offset"] < s1]
        groups.append({"id": nid(), "material_id": "", "property_type": g["property_type"], "keyframe_list": [kf(s0, v0)] + inner + [kf(s1, v1)]})
        if g["property_type"] == "KFTypeScaleX": seg["clip"]["scale"] = {"x": v0, "y": v0}
        if g["property_type"] == "KFTypePositionX": seg["clip"]["transform"]["x"] = v0
        if g["property_type"] == "KFTypePositionY": seg["clip"]["transform"]["y"] = v0
    seg["common_keyframes"] = groups
def is_footage(tr, seg):
    m = vm.get(seg["material_id"]); return tr["type"] == "video" and m is not None and m.get("type") == "video"

def apply_cut(a, b):
    L = b - a
    for tr in d["tracks"]:
        out = []
        for s in sorted(tr["segments"], key=lambda s: s["target_timerange"]["start"]):
            t0 = s["target_timerange"]["start"]; t1 = t0 + s["target_timerange"]["duration"]; has_src = bool(s.get("source_timerange"))
            if t1 <= a: out.append(s); continue
            if t0 >= b: s["target_timerange"]["start"] = t0 - L; out.append(s); continue
            if t0 >= a and t1 <= b: continue                                         # entirely inside → gone
            if is_footage(tr, s):
                src0 = s["source_timerange"]["start"]
                if t0 < a:
                    p = copy.deepcopy(s); p["id"] = nid(); p["target_timerange"] = {"start": t0, "duration": a - t0}; p["source_timerange"] = {"start": src0, "duration": a - t0}
                    trim_keys(p, src0, src0 + (a - t0)); out.append(p)
                if t1 > b:
                    q = copy.deepcopy(s); q["id"] = nid(); q["target_timerange"] = {"start": a, "duration": t1 - b}; q["source_timerange"] = {"start": src0 + (b - t0), "duration": t1 - b}
                    trim_keys(q, src0 + (b - t0), src0 + (t1 - t0)); out.append(q)
            else:                                                                     # adjust / bed / title / caption: trim, keep the source running
                new0 = min(t0, a); new1 = (t1 - L) if t1 > b else a
                s["target_timerange"] = {"start": new0, "duration": new1 - new0}
                if has_src: s["source_timerange"]["duration"] = new1 - new0
                if new1 - new0 > 0: out.append(s)
        tr["segments"] = out
    d["duration"] -= L
before = d["duration"]
for a, b in reversed(cuts): apply_cut(a, b)                                          # right to left, so earlier ranges stay valid
removed = sum(b - a for a, b in cuts)
print(f"cuts {len(cuts)} · removed {removed/US:.2f}s · duration {before/US:.2f} → {d['duration']/US:.2f}")
for tr in d["tracks"]:
    ss = sorted(tr["segments"], key=lambda s: s["target_timerange"]["start"])
    ov = sum(1 for x, y in zip(ss, ss[1:]) if y["target_timerange"]["start"] < x["target_timerange"]["start"] + x["target_timerange"]["duration"] - 1)
    print(f"  {tr['type']:7} {tr.get('name') or '':10} {len(ss):3} segs · overlaps {ov}")
ids = [s["id"] for tr in d["tracks"] for s in tr["segments"]]; assert len(ids) == len(set(ids))
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json")
mp = D / "draft_meta_info.json"
if mp.exists() and capcut._capcut_pid() is None:
    import time; meta = json.loads(mp.read_text()); meta["tm_duration"] = d["duration"]; meta["tm_draft_modified"] = int(time.time() * US); mp.write_text(json.dumps(meta, ensure_ascii=False))
print("✓ written")
