# -*- coding: utf-8 -*-
"""Stage 5 — the vertical reframe, one static framing per camera per reel, from the faces.

    python frame_shots.py "<project>" [--every 1.0] [--head 0.355] [--face-x 0.355] [--anchor 0.30] [--cap 3.55] [--write]

The order in `references/framing.md`, made executable:
  1. scale from the HEAD WIDTH — the number that carries across episodes: head ≈ 33–38 % of the canvas
     width, so s = head_target / face_width_fraction, bounded to [fill, --cap] (the cap is per episode;
     3.55 was measured on אורח G and is only the default);
  2. y from the EYE ANCHOR — eyes at ≈30 % of the canvas height, clamped so the material still covers
     the canvas (qa25 check 7 measures exactly that coverage);
  3. x so the FACE CENTRE lands at --face-x of the canvas width (measured on the approved פרויקט-דוגמה N:
     0.49 host / 0.62 guest — the rules' 0.33–0.38 is the head WIDTH, not the centre), clamped to the pan budget
     so no black band tears open at the edge (|x| ≤ s − 1 for 16:9 material).
Faces are detected on the SOURCE frames of each camera's work copy (YuNet, the model the app ships),
sampled every --every seconds inside each reel's own source range; the median box per (camera, reel)
is the framing, because a locked-off tripod shot has one framing and a median cannot judder.
Both layers of the same camera range get the same numbers; keyframes are cleared (reel_motion adds the
push-in afterwards, starting from the clip scale). Read-only without --write.
"""
import argparse, json, os, re, subprocess, sys
import numpy as np, cv2
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut, paths

US = 1e6; CW, CH = 1080, 1920; FILL = 1920 / 607.5
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--every", type=float, default=1.0)
ap.add_argument("--head", type=float, default=0.355, help="rendered head width as a fraction of canvas width (house: 0.33–0.38)")
ap.add_argument("--face-x", type=float, default=0.50, help="face centre as a fraction of canvas width — measured 0.49 (host) / 0.62 (guest) on פרויקט-דוגמה N; the 0.33–0.38 figure in the rules is the HEAD WIDTH")
ap.add_argument("--anchor", type=float, default=0.30, help="eye line as a fraction of canvas height")
ap.add_argument("--cap", type=float, default=3.55, help="absolute scale ceiling for this episode")
ap.add_argument("--from", dest="t_from", type=float, default=None, help="only (camera, reel) groups whose reel starts at/after this project second — the rest keep their framing AND keyframes")
ap.add_argument("--write", action="store_true"); A = ap.parse_args()
D = capcut.DRAFTS_DIR / A.project; FF = str(paths.FFMPEG)
YUNET = os.path.expanduser("~/bunker-video-engine/models/face_detection_yunet_2023mar.onnx")
d = json.loads((D / "draft_info.json").read_text()); vm = {m["id"]: m for m in d["materials"]["videos"]}
det = cv2.FaceDetectorYN.create(YUNET, "", (640, 360), 0.7)

def res(p):
    raw = re.sub(r"##_draftpath_placeholder_[^#]+_##", "", p); local = os.path.join(D, os.path.basename(raw))
    return local if os.path.exists(local) else raw
def cam_of(path):
    m = re.search(r"cam\s*(\d)", os.path.basename(path)); return int(m.group(1)) if m else 0
def faces_at(path, t):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-vf", "scale=640:360", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    if len(raw) != 640 * 360 * 3: return []
    img = np.frombuffer(raw, np.uint8).reshape(360, 640, 3); det.setInputSize((640, 360)); _, f = det.detect(img)
    return [] if f is None else [((x + w / 2) / 640, y / 360, (y + h) / 360, w / 640) for x, y, w, h, *_ in f if w / 640 > 0.03]

# footage segments grouped by (camera, reel span of the base track)
vt = [t for t in d["tracks"] if t["type"] == "video" and t["segments"]]
groups = {}                                                                   # (cam, base_start_us) -> [segments]
base = vt[0]
for tk in vt:
    for s in tk["segments"]:
        m = vm[s["material_id"]]
        if m.get("type") != "video" or not m.get("path"): continue
        cam = cam_of(m["path"]);
        if not cam: continue
        a = s["target_timerange"]["start"]
        # a reel = the footage between two cards; silence cuts split it into pieces that must share ONE framing
        reel0 = None
        for b in sorted(base["segments"], key=lambda b: b["target_timerange"]["start"]):
            if b["target_timerange"]["start"] > a: break
            if vm[b["material_id"]].get("type") == "photo": reel0 = None
            elif reel0 is None: reel0 = b["target_timerange"]["start"]
        key = (cam, reel0 if reel0 is not None else a)
        if A.t_from is not None and key[1] / US < A.t_from - 0.01: continue
        groups.setdefault(key, []).append(s)

plan = {}
for (cam, span0), segs in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    s0 = min(segs, key=lambda s: s["target_timerange"]["start"]); m = vm[s0["material_id"]]; path = res(m["path"])
    src_a = s0["source_timerange"]["start"] / US; src_b = max(s["source_timerange"]["start"] + s["source_timerange"]["duration"] for s in segs) / US
    boxes = []
    t = src_a + 0.3
    while t < src_b:
        f = faces_at(path, t)
        if f: boxes.append(max(f, key=lambda b: b[3]))                     # the biggest face in the frame is the speaker
        t += A.every
    if not boxes: print(f"  !! cam{cam} @{span0/US:.1f}: no face found — left at fill/centre"); plan[(cam, span0)] = (FILL, 0.0, 0.0, None); continue
    B = np.array(boxes, dtype=float); fx, ftop, fchin, fw = (float(v) for v in np.median(B, axis=0))
    s = float(min(max(A.head / fw, FILL), A.cap))                             # 1. head width → scale, bounded
    eye = ftop + 0.40 * (fchin - ftop); mat_top = A.anchor * CH - eye * 607.5 * s
    mat_top = min(0.0, max(CH - 607.5 * s, mat_top)); y = (960 - mat_top - 607.5 * s / 2) / 960        # 2. eye anchor, clamped to cover
    x = (A.face_x * CW - 540 - 540 * s * (2 * fx - 1)) / 540; x = max(1 - s, min(s - 1, x))          # 3. face centre → x, within the pan budget
    chin_c = (960 - 960 * y + (fchin - 0.5) * 607.5 * s) / CH; eye_c = (960 - 960 * y + (eye - 0.5) * 607.5 * s) / CH
    face_x_c = (540 + 540 * x + (fx - 0.5) * 1080 * s) / CW
    plan[(cam, span0)] = (s, x, y, {"faces": len(boxes), "fw": round(float(fw), 3), "head_px": round(float(fw * 1080 * s)), "eye_c": round(float(eye_c), 3), "chin_c": round(float(chin_c), 3), "face_x_c": round(float(face_x_c), 3)})
    print(f"  cam{cam} reel@{span0/US:7.2f}: {len(boxes):3} faces | fw {fw:.3f} → s {s:.3f} ({s/FILL:.3f}× fill) | x {x:+.3f} y {y:+.3f} | head {fw*1080*s:.0f}px ({fw*s:.3f}W) eyes {eye_c:.3f}H chin {chin_c:.3f}H face_x {face_x_c:.3f}W")

if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
n = 0
for (cam, span0), segs in groups.items():
    s, x, y, _ = plan[(cam, span0)]
    for sg in segs:
        sg["clip"]["scale"] = {"x": s, "y": s}; sg["clip"]["transform"] = {"x": x, "y": y}; sg["common_keyframes"] = []; sg["keyframe_refs"] = []; n += 1
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json")
json.dump({f"cam{c}@{t/US:.2f}": {"scale": s, "x": x, "y": y, **(info or {})} for (c, t), (s, x, y, info) in plan.items()}, open(D / "ccstudio-framing.json", "w"), ensure_ascii=False, indent=1)
print(f"✓ framed {n} segments in {len(plan)} (camera, reel) groups")
