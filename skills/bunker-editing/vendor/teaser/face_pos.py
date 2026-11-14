#!/usr/bin/env python3
"""Where is the face in each camera? → the `face` prop of <Cam> (0–1 of the source frame).

    face_pos.py cam1.mp4 [cam2.mp4 ...] [--samples 40] [--from 0 --to 600]

Samples frames across the range, finds the largest frontal face (OpenCV Haar, the same detector video-breakdown
uses) and prints the median centre and size per file, plus a ready-to-paste FACE line. A two-person wide shot
reports the largest face only — crop such a camera per speaker by passing --side right|left.
"""
import argparse
import statistics as st
import subprocess
from pathlib import Path

import cv2

FFMPEG = str(Path.home() / "ffmpeg-bin" / "ffmpeg")
FACE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def duration(p: Path) -> float:
    out = subprocess.run([str(Path.home() / "ffmpeg-bin" / "ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True).stdout
    return float(out.strip() or 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--from", dest="t0", type=float, default=0)
    ap.add_argument("--to", dest="t1", type=float, default=0)
    ap.add_argument("--side", choices=["left", "right"], help="only faces on this half of the frame")
    a = ap.parse_args()
    lines = []
    for i, f in enumerate(map(Path, a.files), start=1):
        t1 = a.t1 or duration(f)
        xs, ys, hs = [], [], []
        for k in range(a.samples):
            t = a.t0 + (t1 - a.t0) * (k + 0.5) / a.samples
            cap = cv2.VideoCapture(str(f))
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            cap.release()
            if not ok:
                continue
            H, W = frame.shape[:2]
            s = 640 / W
            small = cv2.cvtColor(cv2.resize(frame, (640, int(H * s))), cv2.COLOR_BGR2GRAY)
            faces = FACE.detectMultiScale(small, scaleFactor=1.12, minNeighbors=6, minSize=(30, 30))
            if a.side:
                faces = [fc for fc in faces if (fc[0] + fc[2] / 2 > 320) == (a.side == "right")]
            if len(faces) == 0:
                continue
            x, y, w, h = max(faces, key=lambda fc: fc[3])
            xs.append((x + w / 2) / 640); ys.append((y + h / 2) / small.shape[0]); hs.append(h / small.shape[0])
        if not xs:
            print(f"{f.name}: no face found"); continue
        fx, fy, fh = st.median(xs), st.median(ys), st.median(hs)
        print(f"{f.name}: face x={fx:.3f} y={fy:.3f} (face height {fh:.0%} of frame, {len(xs)}/{a.samples} samples)")
        lines.append(f"{i}: {{ x: {fx:.3f}, y: {fy:.3f} }}")
    print("const FACE = { " + ", ".join(lines) + " };")


if __name__ == "__main__":
    main()
