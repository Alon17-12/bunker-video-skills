"""0910 — plan a face-centred, tracked horizontal pan per camera piece (read-only).
Samples the SOURCE at 4 fps, YuNet face → fx (fraction of source width), smooths, and
emits PositionX keyframes on the source clock so the face sits at canvas x = 0.5 (t=0.5):
    x(t) = -s(t)·(2·fx(t)-1)        (framing.md, target 0.5)   clamped to ±(s-1)
Output: <scratch>/0910_pan_plan.json  {segment_id: [[time_offset_us, fx], ...]}  (x derived at apply time)"""
import sys, os, json, subprocess, tempfile, shutil
from pathlib import Path
import numpy as np, cv2
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut, reframe, paths
SP = Path(os.environ.get("PAN_OUT", Path.home() / "Movies" / "reel-captions-work")); SP.mkdir(parents=True, exist_ok=True); NAME = "0910"; US = 1_000_000
FPS = 4; STEP = 0.5; TOL = 0.006   # keyframe every 0.5s max, dropped when linear interp is within TOL (in x units)
d = capcut.load_draft(NAME); vm = {m["id"]: m for m in d["materials"]["videos"]}
def s_at(seg, t_us):
    g = next((g for g in seg["common_keyframes"] if g["property_type"] == "KFTypeScaleX"), None)
    if g is None: return seg["clip"]["scale"]["x"]
    ks = sorted(g["keyframe_list"], key=lambda k: k["time_offset"])
    if t_us <= ks[0]["time_offset"]: return ks[0]["values"][0]
    if t_us >= ks[-1]["time_offset"]: return ks[-1]["values"][0]
    for a, b in zip(ks, ks[1:]):
        if a["time_offset"] <= t_us <= b["time_offset"]:
            f = (t_us - a["time_offset"]) / (b["time_offset"] - a["time_offset"]); return a["values"][0] + f * (b["values"][0] - a["values"][0])
plan = {}; report = []
for seg in sorted(d["tracks"][0]["segments"], key=lambda s: s["target_timerange"]["start"]):
    m = vm[seg["material_id"]]
    if m.get("type") == "photo": continue
    src0, dur = seg["source_timerange"]["start"], seg["source_timerange"]["duration"]
    tmp = Path(tempfile.mkdtemp(prefix="pan-"))
    subprocess.run([str(paths.FFMPEG), "-v", "error", "-nostdin", "-ss", f"{src0/US:.3f}", "-t", f"{dur/US:.3f}", "-i", m["path"],
                    "-vf", f"fps={FPS},scale=640:-2", "-q:v", "4", str(tmp / "f%04d.jpg")], check=True)
    frames = sorted(tmp.glob("*.jpg")); fx = []
    for fp in frames:
        faces = reframe._detect(cv2.imread(str(fp)))
        fx.append(max(faces, key=lambda f: f["w"])["x"] if faces else np.nan)
    shutil.rmtree(tmp, ignore_errors=True)
    fx = np.array(fx, dtype=float); n = len(fx); t = src0 + (np.arange(n) / FPS) * US
    if np.isnan(fx).all(): fx[:] = 0.5
    else:
        idx = np.arange(n); ok = ~np.isnan(fx); fx = np.interp(idx, idx[ok], fx[ok])
    # smooth: median (1.25s) then mean (1.75s) — follows a lean, ignores a head turn
    k = 5; fx = np.array([np.median(fx[max(0,i-k//2):i+k//2+1]) for i in range(n)])
    k = 7; fx = np.array([np.mean(fx[max(0,i-k//2):i+k//2+1]) for i in range(n)])
    s = np.array([s_at(seg, tt) for tt in t]); x = -s * (2 * fx - 1); x = np.clip(x, -(s - 1), s - 1)
    # keyframe selection: greedy — keep a point when the straight line from the last kept point misses by > TOL
    keep = [0]
    while keep[-1] < n - 1:
        i0 = keep[-1]; j = i0 + 1; last_ok = j
        while j < n:
            seg_ok = all(abs(x[i0] + (x[j]-x[i0])*(t[q]-t[i0])/(t[j]-t[i0]) - x[q]) <= TOL for q in range(i0+1, j))
            if not seg_ok or (t[j]-t[i0]) > 8*US: break
            last_ok = j; j += 1
        keep.append(last_ok)
    # never sparser than every 0.5s where the face is moving, never denser than 0.25s (sampling)
    kfs = [[int(t[i]), float(fx[i])] for i in keep]
    kfs[-1][0] = src0 + dur; kfs[0][0] = src0
    plan[seg["id"]] = kfs
    report.append(f"  {seg['target_timerange']['start']/US:7.2f}s  frames {n:3d}  fx {np.nanmin(fx):.3f}–{np.nanmax(fx):.3f} (med {np.median(fx):.3f})  x {x.min():+.3f}…{x.max():+.3f}  keys {len(kfs)}")
json.dump(plan, open(SP / f"{NAME}_pan_plan.json", "w"))
print("\n".join(report)); print("pieces", len(plan), "| total keys", sum(len(v) for v in plan.values()))
