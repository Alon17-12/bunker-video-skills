#!/usr/bin/env python3
"""Find how far apart the cameras (and a separate audio recorder) of one podcast episode started, from their sound.

    sync_cams.py <reference> <other> [<other> ...] [--minutes 6]

The reference is the file whose clock the teaser uses (usually the clean audio WAV, or camera 1). For every other
file it prints the offset in seconds such that   time_in_other = time_in_reference + offset   and how sure it is
(z-score of the best lag; above ~10 is solid). Works on the first --minutes of each file at 8 kHz mono, FFT
cross-correlation of the onset envelopes (robust to different mics and room tone).

Output also lands in --out (default ./sync.json, run it from the project folder), which the teaser plan reads (`cams[i].offset`).
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

FFMPEG = str(Path.home() / "ffmpeg-bin" / "ffmpeg")
SR = 8000


def load(path: Path, minutes: float) -> np.ndarray:
    raw = subprocess.run([FFMPEG, "-v", "error", "-t", str(minutes * 60), "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    # onset envelope: frame energy (10 ms hops), log, positive differences — independent of mic colour/gain
    hop = SR // 100
    n = len(x) // hop
    e = np.log1p(1000 * np.square(x[: n * hop].reshape(n, hop)).mean(axis=1))
    d = np.maximum(0, np.diff(e, prepend=e[0]))
    return (d - d.mean()) / (d.std() + 1e-9)


def offset(ref: np.ndarray, other: np.ndarray):
    n = 1 << int(np.ceil(np.log2(len(ref) + len(other))))
    c = np.fft.irfft(np.fft.rfft(other, n) * np.conj(np.fft.rfft(ref, n)), n)
    lag = int(np.argmax(c))
    z = (c[lag] - c.mean()) / (c.std() + 1e-9)  # how far the best lag stands above all the others
    if lag > n // 2:
        lag -= n
    return lag / 100.0, float(z)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("others", nargs="+")
    ap.add_argument("--minutes", type=float, default=6)
    ap.add_argument("--out", default="sync.json", help="written in the project folder, never next to the raw files")
    a = ap.parse_args()
    ref = Path(a.reference)
    r = load(ref, a.minutes)
    out = {"reference": str(ref), "files": []}
    for o in map(Path, a.others):
        off, conf = offset(r, load(o, a.minutes))
        out["files"].append({"file": str(o), "offset": round(off, 2), "confidence": round(conf, 2)})
        print(f"{o.name}: offset {off:+.2f}s  (confidence {conf:.1f}{'' if conf >= 10 else '  ← weak, check by ear'})")
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
