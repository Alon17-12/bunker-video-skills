#!/usr/bin/env python3
"""Per-moment face position + how hard every jump cut is (Alon, לקוח A 20.10.2026: «שהפנים של הדובר יהיו תמיד
ממורכזות» · «אם יש קאט גס — תציג לרגע את הצד השני»).

    face_track.py <session> <cam1.mp4> <cam2.mp4>        (cameras on the «מקור» clock; after refine_edges)

→ public/face_track.json  {"1": [[src_t, x, y], …], "2": …}   face centre 0–1 of the source frame, 2 samples/s over every clip
→ work/cut_diffs.json     {"rN": [{at, prev_src_end, src, diff1, diff2, dx1, dx2}, …]}  per cut: picture change on each camera
"""
import json, subprocess, sys
from pathlib import Path
import cv2, numpy as np
from rpaths import session_paths

S, RM, PUB, WORK = session_paths(sys.argv[:2])
CAMS = {"1": sys.argv[2], "2": sys.argv[3]}
FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
DET = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
PW, PH = 640, 360


def frames(path, t, dur, fps):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{max(0, t):.3f}", "-t", f"{dur:.3f}", "-i", path, "-vf", f"fps={fps},scale={PW}:{PH}",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    n = len(raw) // (PW * PH)
    return [np.frombuffer(raw[i * PW * PH:(i + 1) * PW * PH], np.uint8).reshape(PH, PW) for i in range(n)]


def face(g):
    f = DET.detectMultiScale(g, 1.1, 5, minSize=(50, 50))
    if not len(f):
        return None
    x, y, w, h = max(f, key=lambda r: r[2] * r[3])
    return (x + w / 2) / PW, (y + h / 2) / PH


track, diffs = {"1": [], "2": []}, {}
for f in sorted(PUB.glob("r[0-9]*.json"), key=lambda p: int(p.stem[1:])):
    cut = json.loads(f.read_text()); rows = []
    for i, c in enumerate(cut["clips"]):
        d = c["end"] - c["at"]
        for k, p in CAMS.items():
            for j, g in enumerate(frames(p, c["src"], d, 2)):
                r = face(g)
                if r:
                    track[k].append([round(c["src"] + (j + 0.5) / 2, 2), round(r[0], 4), round(r[1], 4)])
        if i:
            pc = cut["clips"][i - 1]; pe = pc["src"] + pc["end"] - pc["at"]
            row = {"at": c["at"], "prev_src_end": round(pe, 3), "src": c["src"]}
            for k, p in CAMS.items():
                a = frames(p, pe - 0.08, 0.05, 25)[:1]; b = frames(p, c["src"] + 0.02, 0.05, 25)[:1]
                if a and b:
                    row[f"diff{k}"] = round(float(np.abs(a[0].astype(int) - b[0].astype(int)).mean()), 2)
                    fa, fb = face(a[0]), face(b[0])
                    row[f"dx{k}"] = round(abs(fa[0] - fb[0]) + abs(fa[1] - fb[1]), 3) if fa and fb else None
            rows.append(row)
    diffs[f.stem] = rows
    print(f.stem, len(rows), "cuts", flush=True)
for k in track:
    track[k].sort()
(PUB / "face_track.json").write_text(json.dumps(track))
(WORK / "cut_diffs.json").write_text(json.dumps(diffs, indent=1))
print({k: len(v) for k, v in track.items()})
