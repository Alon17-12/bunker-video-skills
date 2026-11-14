"""0910 round 2 — (a) intro zoom-out 5%→target over 1s on the first camera piece, eased;
(b) face-centred tracked PositionX keyframes from 0910_pan_plan.json; (c) captions lower;
(d) logo higher. Idempotent for (c)/(d); (a)/(b) rewrite the keyframe groups they own."""
import os
import sys, json
from pathlib import Path
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, reframe
SP = Path(__file__).parent; NAME = "0910"; US = 1_000_000
INTRO_ZOOM = 0.05; INTRO_S = 1.0; RATE = 0.012; IN_MAX = 0.11
CAP_Y = -0.19; LOGO_Y = -0.40
pid = capcut._capcut_pid()
if pid and f"{capcut.DRAFTS_DIR/NAME}/" in capcut._capcut_open_files(pid): raise SystemExit("draft open in CapCut")
if capcut.capcut_running(): raise SystemExit("CapCut running")
d = capcut.load_draft(NAME); vm = {m["id"]: m for m in d["materials"]["videos"]}
plan = json.load(open(SP / "0910_pan_plan.json"))
def kf(t, v, curve="Line"):
    return {"id": capcut._new_id(), "curveType": curve, "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0},
            "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def group(prop, keys): return {"id": capcut._new_id(), "material_id": "", "property_type": prop, "keyframe_list": keys}
pieces = [s for s in sorted(d["tracks"][0]["segments"], key=lambda s: s["target_timerange"]["start"]) if vm[s["material_id"]].get("type") != "photo"]

# (a) intro: first camera piece — 1.05×fill → fill in INTRO_S (eased), then the usual slow push-in
p0 = pieces[0]; fill = reframe.fill_scale(vm[p0["material_id"]].get("width") or 1920, vm[p0["material_id"]].get("height") or 1080)
src0, dur = p0["source_timerange"]["start"], p0["source_timerange"]["duration"]; L = dur / US
A = min(IN_MAX, RATE * (L - INTRO_S))
sk = [kf(src0, fill * (1 + INTRO_ZOOM), "CurveInOut"), kf(src0 + int(INTRO_S * US), fill, "CurveInOut"), kf(src0 + dur, fill * (1 + A))]
p0["common_keyframes"] = [g for g in p0["common_keyframes"] if g["property_type"] not in ("KFTypeScaleX", "KFTypeScaleY")]
p0["common_keyframes"] += [group("KFTypeScaleX", sk), group("KFTypeScaleY", [dict(k, id=capcut._new_id()) for k in sk])]
p0["clip"]["scale"] = {"x": fill * (1 + INTRO_ZOOM), "y": fill * (1 + INTRO_ZOOM)}
print(f"intro: {1+INTRO_ZOOM:.2f}× → 1.00× over {INTRO_S}s, then push to {1+A:.3f}× by {L:.2f}s")

# (b) tracked pan: x(t) = -s(t)·(2fx-1), clamped to ±(s-1), on the source clock
def s_at(seg, t_us):
    g = next((g for g in seg["common_keyframes"] if g["property_type"] == "KFTypeScaleX"), None)
    if g is None: return seg["clip"]["scale"]["x"]
    ks = sorted(g["keyframe_list"], key=lambda k: k["time_offset"])
    if t_us <= ks[0]["time_offset"]: return ks[0]["values"][0]
    if t_us >= ks[-1]["time_offset"]: return ks[-1]["values"][0]
    for a, b in zip(ks, ks[1:]):
        if a["time_offset"] <= t_us <= b["time_offset"]:
            f = (t_us - a["time_offset"]) / (b["time_offset"] - a["time_offset"]); return a["values"][0] + f * (b["values"][0] - a["values"][0])
nkeys = 0; xr = []
for s in pieces:
    pts = plan[s["id"]]; src0, dur = s["source_timerange"]["start"], s["source_timerange"]["duration"]
    # union with the scale keyframe times so the pan re-solves wherever the scale bends
    times = sorted({int(t) for t, _ in pts} | {g_k["time_offset"] for g in s["common_keyframes"] if g["property_type"] == "KFTypeScaleX" for g_k in g["keyframe_list"]})
    fx_at = lambda t: (lambda T, F: F[0] if t <= T[0] else F[-1] if t >= T[-1] else next(F[i] + (F[i+1]-F[i])*(t-T[i])/(T[i+1]-T[i]) for i in range(len(T)-1) if T[i] <= t <= T[i+1]))([p[0] for p in pts], [p[1] for p in pts])
    keys = []
    for t in times:
        t = min(max(t, src0), src0 + dur); sc = s_at(s, t); x = -sc * (2 * fx_at(t) - 1); x = max(-(sc - 1), min(sc - 1, x))
        keys.append(kf(t, x)); xr.append(x)
    s["common_keyframes"] = [g for g in s["common_keyframes"] if g["property_type"] != "KFTypePositionX"]
    s["common_keyframes"].append(group("KFTypePositionX", keys))
    s["clip"]["transform"]["x"] = keys[0]["values"][0]; nkeys += len(keys)
print(f"pan: {nkeys} PositionX keys over {len(pieces)} pieces | x range {min(xr):+.3f}…{max(xr):+.3f}")

# (c) captions lower, (d) logo higher
tt = next(t for t in d["tracks"] if t["type"] == "text")
for s in tt["segments"]: s["clip"]["transform"]["y"] = CAP_Y
lt = next(t for t in d["tracks"] if t.get("name") == "logo")
for s in lt["segments"]: s["clip"]["transform"]["y"] = LOGO_Y
print(f"captions y → {CAP_Y} ({len(tt['segments'])}) | logo y → {LOGO_Y} ({len(lt['segments'])})")
capcut._backup(capcut.DRAFTS_DIR / NAME); capcut._atomic_write(capcut.DRAFTS_DIR / NAME, d); print("written")
