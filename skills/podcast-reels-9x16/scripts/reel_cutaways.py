# -*- coding: utf-8 -*-
"""Reaction cutaways on the OVER layer of a two-camera reel: short windows where the listener's camera
(the hidden layer, alpha 0) is shown — "רואים אותי מהנהן ומגיב" — without touching the base layer.

    python reel_cutaways.py "<project>" --windows 8.60:10.40,21.50:23.30,... [--top 1] [--write]

Each window splits the over-layer segment it falls in into [before][cut][after]; the cut piece gets
alpha 1 and sits STILL at the framing interpolated at its first frame (a shot under 2.5 s does not
move — house rule), the outer pieces keep their keyframes, trimmed to their own source range with an
interpolated key on the new boundary (keyframe `time_offset` is absolute source time, so a key left
outside its piece would still pull on it). Fresh uuids on every key. Read-only without --write.

Where the windows come from (0922): a YuNet pass over the hidden camera at 10 fps scored 2 s windows by
the vertical motion of the face (a nod), filtered to moments the speaker's mic owns (mic1 − mic2 <
−5 dB: the host is listening, not talking), one per third of the reel, snapped to the start of the
speaker's nearest pause (a cut on a breath), and kept clear of the b-roll windows and of the reel's
first 3 s / last 2.5 s. The client's note «המצלמה יותר מדי קופצת» is why they are 1.8 s and only three.
"""
import argparse, copy, json, os, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--windows", required=True, help="a:b,a:b,… project seconds")
ap.add_argument("--top", type=int, default=1, help="index of the over layer among the video tracks"); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project
d = json.loads((D / "draft_info.json").read_text()); FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR)
nid = lambda: str(uuid.uuid4()).upper()
vt = [t for t in d["tracks"] if t["type"] == "video" and t["segments"]]; top = vt[A.top]
wins = sorted((snap(float(a) * US), snap(float(b) * US)) for a, b in (w.split(":") for w in A.windows.split(",")))

def interp(keys, t):
    """value of a keyframe list at absolute source time t (linear between neighbours; clamped)"""
    ks = sorted(keys, key=lambda k: k["time_offset"])
    if t <= ks[0]["time_offset"]: return ks[0]["values"][0]
    if t >= ks[-1]["time_offset"]: return ks[-1]["values"][0]
    for k0, k1 in zip(ks, ks[1:]):
        if k0["time_offset"] <= t <= k1["time_offset"]:
            f = (t - k0["time_offset"]) / max(1, k1["time_offset"] - k0["time_offset"]); return k0["values"][0] + f * (k1["values"][0] - k0["values"][0])
def kf(t, v): return {"id": nid(), "curveType": "CurveInOut", "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def piece(seg, s0, s1, alpha, still):
    """a copy of seg covering source [s0, s1) (absolute source us) with keyframes trimmed to it"""
    p = copy.deepcopy(seg); p["id"] = nid(); off = seg["target_timerange"]["start"] - seg["source_timerange"]["start"]
    p["source_timerange"] = {"start": int(s0), "duration": int(s1 - s0)}; p["target_timerange"] = {"start": int(s0 + off), "duration": int(s1 - s0)}
    p["clip"]["alpha"] = alpha; groups = []
    for g in seg.get("common_keyframes", []):
        v0 = interp(g["keyframe_list"], s0); v1 = interp(g["keyframe_list"], s1)
        if still: keys = [kf(s0, v0), kf(s1, v0)]
        else:
            inner = [dict(k, id=nid()) for k in g["keyframe_list"] if s0 < k["time_offset"] < s1]
            keys = [kf(s0, v0)] + inner + [kf(s1, v1)]
        groups.append({"id": nid(), "material_id": "", "property_type": g["property_type"], "keyframe_list": keys})
        if g["property_type"] == "KFTypeScaleX": p["clip"]["scale"] = {"x": v0, "y": v0}
        if g["property_type"] == "KFTypePositionX": p["clip"]["transform"]["x"] = v0
        if g["property_type"] == "KFTypePositionY": p["clip"]["transform"]["y"] = v0
    p["common_keyframes"] = groups; return p

out = []; n_cut = 0
for seg in sorted(top["segments"], key=lambda s: s["target_timerange"]["start"]):
    t0 = seg["target_timerange"]["start"]; t1 = t0 + seg["target_timerange"]["duration"]; off = t0 - seg["source_timerange"]["start"]
    mine = [w for w in wins if t0 <= w[0] and w[1] <= t1]
    if not mine or seg["clip"]["alpha"] >= 0.99: out.append(seg); continue
    cur = t0
    for a, b in mine:
        if a > cur: out.append(piece(seg, cur - off, a - off, 0.0, False))
        out.append(piece(seg, a - off, b - off, 1.0, True)); n_cut += 1; cur = b
        print(f"  cutaway {a/US:7.2f}–{b/US:7.2f} ({(b-a)/US:.2f}s) in over seg {t0/US:.2f}–{t1/US:.2f}")
    if cur < t1: out.append(piece(seg, cur - off, t1 - off, 0.0, False))
top["segments"] = out
missed = [w for w in wins if not any(s["target_timerange"]["start"] <= w[0] and w[1] <= s["target_timerange"]["start"] + s["target_timerange"]["duration"] and s["clip"]["alpha"] >= 0.99 for s in out)]
ri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
for s in out:
    if "render_index" not in s: ri += 1; s["render_index"] = ri
ss = sorted(out, key=lambda s: s["target_timerange"]["start"])
gaps = [(a["target_timerange"]["start"] + a["target_timerange"]["duration"], b["target_timerange"]["start"]) for a, b in zip(ss, ss[1:])]
print(f"cutaways placed {n_cut}/{len(wins)} | over layer now {len(out)} pieces | overlaps {sum(1 for x, y in gaps if y < x)} | missed {[(a/US, b/US) for a, b in missed]}")
ids = [k["id"] for s in out for g in s.get("common_keyframes", []) for k in g["keyframe_list"]] + [s["id"] for s in out]; assert len(ids) == len(set(ids))
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
