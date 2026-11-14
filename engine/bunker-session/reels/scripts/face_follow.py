#!/usr/bin/env python3
"""The camera follows the speaker's face (אורח B r2, 29.10.2026 — Alon: «התנועת מצלמה ממש טובה, תשמור אותה בסקיל»).

The engine holds one face position per camera (public/face.json); when a guest leans or shifts in the chair the face drifts off
centre — 0.48 vs 0.59 of the frame on r2, ~380 px at the reel's zoom. This samples every clip of a reel on the GRADED selects
(cam1s/cam2s.mp4 via selects.json) at 5 fps, finds the face (OpenCV Haar, the biggest one within 0.25 of the session position),
smooths it (running median of 5, then an EMA 0.7/0.3 so the frame glides and never jitters) and writes it into the reel's plan:
    plans.json → rN.follow = {"1": [[src, x, y], …], "2": …}
Reel.tsx's Cam reads it for the main shots (splits keep their static crops). A gap over 1.2 s holds the nearest sample.

    python3 face_follow.py <session> rN [rM …]          (after the cut is final; re-run after any recut / regrade)
"""
import json, subprocess, sys
from pathlib import Path
import cv2, numpy as np
from rpaths import session_paths

S, RM, PUB, WORK = session_paths(sys.argv[:2])
FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
DET = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
# YuNet (OpenCV's DNN face detector, ~/.cache/yunet/yunet.onnx) finds a face turned toward the other chair, which the Haar cascade
# misses — on Niv Beli it found 4 faces in a whole reel and the few false hits dragged the frame off him (2.11.2026)
YN = Path.home() / ".cache/yunet/yunet.onnx"
YUNET = cv2.FaceDetectorYN.create(str(YN), "", (640, 360), 0.7, 0.3, 5000) if YN.exists() else None
PW, PH, FPS = 640, 360, 5
sel = json.loads((PUB / "selects.json").read_text()); face = json.loads((PUB / "face.json").read_text())
plans = json.loads((PUB / "plans.json").read_text())

def selt(t):
    for w in sel:
        if w["from"] - 1e-3 <= t <= w["to"] + 1e-3: return w["at"] + t - w["from"]
    return None

for rid in sys.argv[2:]:
    cut = json.loads((PUB / f"{rid}.json").read_text()); out = {}
    for cam in ("1", "2"):
        pts = []
        for c in cut["clips"]:
            a, d = c["src"], c["end"] - c["at"]; s0 = selt(a)
            if s0 is None: continue
            raw = subprocess.run([FF, "-v", "error", "-ss", f"{s0:.3f}", "-t", f"{d:.3f}", "-i", str(PUB / f"cam{cam}s.mp4"), "-vf", f"fps={FPS},scale={PW}:{PH}",
                                  "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
            for i in range(len(raw) // (PW * PH)):
                g = np.frombuffer(raw[i * PW * PH:(i + 1) * PW * PH], np.uint8).reshape(PH, PW)
                if YUNET is not None:
                    _, yf = YUNET.detect(cv2.cvtColor(g, cv2.COLOR_GRAY2BGR))
                    f = [tuple(int(v) for v in r[:4]) for r in (yf if yf is not None else [])]
                else:
                    f = DET.detectMultiScale(g, 1.1, 5, minSize=(40, 40))
                if len(f):
                    x, y, w, h = max(f, key=lambda r: r[2] * r[3]); fx, fy = (x + w / 2) / PW, (y + h / 2) / PH
                    if abs(fx - face[cam]["x"]) < 0.25 and abs(fy - face[cam]["y"]) < 0.25: pts.append([a + i / FPS, fx, fy])
        pts.sort(); xs = [p[1] for p in pts]; ys = [p[2] for p in pts]; sm = []; ex = ey = None
        for i, p in enumerate(pts):
            mx, my = float(np.median(xs[max(0, i - 2):i + 3])), float(np.median(ys[max(0, i - 2):i + 3]))
            if ex is None or p[0] - sm[-1][0] > 1.0: ex, ey = mx, my
            else: ex, ey = ex * 0.7 + mx * 0.3, ey * 0.7 + my * 0.3
            sm.append([round(p[0], 2), round(ex, 4), round(ey, 4)])
        out[cam] = sm
        print(rid, "cam", cam, len(sm), "samples, x", round(min(xs), 3) if xs else "-", "…", round(max(xs), 3) if xs else "-", "(static", face[cam]["x"], ")")
    plans[rid]["follow"] = out
(PUB / "plans.json").write_text(json.dumps(plans, ensure_ascii=False, indent=1))
