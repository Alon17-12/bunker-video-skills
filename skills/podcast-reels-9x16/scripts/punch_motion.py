"""Punch motion instead of drift (born on 0910). Alon: "פחות ריחוף, יותר תנועות שתופסות את העין —
פעם ב… זום אין/אאוט חד וחלק". Every shot holds STILL and, on sentence starts spaced ≥ PUNCH_GAP
apart, snaps between two levels over PUNCH_T with CurveInOut. Even shots live on {1.00, 1.08}×fill,
odd shots on {1.05, 1.113}×fill, so every cut still lands with a framing change. The intro
(first shot) keeps the 1.05→1.00 zoom-out over 1s. Then PositionX is re-solved from the pan plan."""
import os
import sys, json
from pathlib import Path
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, reframe
if len(sys.argv) < 4: raise SystemExit("usage: punch_motion.py <project> <words.json> <pan_plan.json>")
NAME = sys.argv[1]; US = 1_000_000
PUNCH_T = 0.45; PUNCH_GAP = 4.0; FIRST_AFTER = 1.5; LAST_BEFORE = 1.0; STATIC = 2.5
INTRO = 0.05; INTRO_S = 1.0; LEVELS = {0: (1.00, 1.08), 1: (1.05, 1.113)}   # ≤ ×1.123 of fill
WORDS = sys.argv[2]
pid = capcut._capcut_pid()
if pid and f"{capcut.DRAFTS_DIR/NAME}/" in capcut._capcut_open_files(pid): raise SystemExit("draft open in CapCut")
if capcut.capcut_running(): raise SystemExit("CapCut running")
d = capcut.load_draft(NAME); vm = {m["id"]: m for m in d["materials"]["videos"]}
ws = json.load(open(WORDS)); plan = json.load(open(sys.argv[3]))
starts = [ws[0]["start_s"]] + [ws[i+1]["start_s"] for i in range(len(ws)-1) if ws[i]["text"][-1:] in ".?!"]
def kf(t, v, curve="Line"):
    return {"id": capcut._new_id(), "curveType": curve, "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0},
            "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def group(prop, keys): return {"id": capcut._new_id(), "material_id": "", "property_type": prop, "keyframe_list": keys}
pieces = [s for s in sorted(d["tracks"][0]["segments"], key=lambda s: s["target_timerange"]["start"]) if vm[s["material_id"]].get("type") != "photo"]
n_punch = 0; n_still = 0
for k, s in enumerate(pieces):
    m = vm[s["material_id"]]; fill = reframe.fill_scale(m.get("width") or 1920, m.get("height") or 1080)
    src0, dur = s["source_timerange"]["start"], s["source_timerange"]["duration"]; t0 = s["target_timerange"]["start"]/US; L = dur/US
    lo, hi = LEVELS[k % 2]; cur = lo; keys = []
    if k == 0:
        keys += [kf(src0, fill*(1+INTRO), "CurveInOut"), kf(src0 + int(INTRO_S*US), fill, "CurveInOut")]; last = INTRO_S
    else:
        keys.append(kf(src0, fill*cur)); last = 0.0
    if L >= STATIC:
        for tw in starts:
            tl = tw - t0
            if tl < max(FIRST_AFTER, last + PUNCH_GAP) or tl > L - LAST_BEFORE: continue
            nxt = hi if cur == lo else lo
            keys += [kf(src0 + int(tl*US), fill*cur, "CurveInOut"), kf(src0 + int((tl+PUNCH_T)*US), fill*nxt, "CurveInOut")]
            cur = nxt; last = tl + PUNCH_T; n_punch += 1
    else: n_still += 1
    keys.append(kf(src0 + dur, fill*cur))
    s["common_keyframes"] = [g for g in s["common_keyframes"] if g["property_type"] not in ("KFTypeScaleX", "KFTypeScaleY")]
    s["common_keyframes"] += [group("KFTypeScaleX", keys), group("KFTypeScaleY", [dict(x, id=capcut._new_id()) for x in keys])]
    s["clip"]["scale"] = {"x": keys[0]["values"][0], "y": keys[0]["values"][0]}
    print(f"  {t0:7.2f} +{L:5.2f}s  levels {lo}/{hi}  punches {sum(1 for x in keys if x['curveType']=='CurveInOut')//2 - (1 if k==0 else 0)}")
print(f"punches {n_punch} | still shots {n_still} | pieces {len(pieces)}")
# re-solve the tracked pan against the new scale curve
def s_at(seg, t_us):
    g = next(g for g in seg["common_keyframes"] if g["property_type"] == "KFTypeScaleX")
    ks = sorted(g["keyframe_list"], key=lambda k: k["time_offset"])
    if t_us <= ks[0]["time_offset"]: return ks[0]["values"][0]
    if t_us >= ks[-1]["time_offset"]: return ks[-1]["values"][0]
    for a, b in zip(ks, ks[1:]):
        if a["time_offset"] <= t_us <= b["time_offset"]:
            f = (t_us - a["time_offset"]) / (b["time_offset"] - a["time_offset"]); return a["values"][0] + f * (b["values"][0] - a["values"][0])
nk = 0
for s in pieces:
    pts = plan[s["id"]]; src0, dur = s["source_timerange"]["start"], s["source_timerange"]["duration"]
    T = [p[0] for p in pts]; F = [p[1] for p in pts]
    def fx_at(t):
        if t <= T[0]: return F[0]
        if t >= T[-1]: return F[-1]
        for i in range(len(T)-1):
            if T[i] <= t <= T[i+1]: return F[i] + (F[i+1]-F[i])*(t-T[i])/(T[i+1]-T[i])
    times = sorted({int(t) for t in T} | {x["time_offset"] for g in s["common_keyframes"] if g["property_type"] == "KFTypeScaleX" for x in g["keyframe_list"]})
    keys = []
    for t in times:
        t = min(max(t, src0), src0 + dur); sc = s_at(s, t); x = -sc*(2*fx_at(t)-1); x = max(-(sc-1), min(sc-1, x)); keys.append(kf(t, x))
    s["common_keyframes"] = [g for g in s["common_keyframes"] if g["property_type"] != "KFTypePositionX"] + [group("KFTypePositionX", keys)]
    s["clip"]["transform"]["x"] = keys[0]["values"][0]; nk += len(keys)
print(f"pan keys {nk}")
capcut._backup(capcut.DRAFTS_DIR/NAME); capcut._atomic_write(capcut.DRAFTS_DIR/NAME, d); print("written")
