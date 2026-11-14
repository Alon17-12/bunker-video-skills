#!/usr/bin/env python3
"""Who is talking when — from one microphone per speaker (the Bunker records COMBO-1 / COMBO-2 next to Live-Mix).

    speakers.py mic1.wav mic2.wav [--names host guest] [--out speakers.json]

Each mic hears both people (bleed), but its own speaker is ~6–20 dB louder. Per 100 ms: RMS in dB per mic, the
louder mic wins when it leads by ≥ --lead dB and is above the noise floor; otherwise silence or "both" (overlap /
laughter). Runs shorter than --min are absorbed into their neighbours (hysteresis), so the camera never flickers.
Output: {"hop": 0.1, "segments": [{"from", "to", "who"}], "talk_share": {...}}. The camera plan cuts to the speaker's
camera on each segment start (and to the listener for a reaction on a long one).
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

FFMPEG = str(Path.home() / "ffmpeg-bin" / "ffmpeg")
SR, HOP = 16000, 0.1


def db(path):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], stdout=subprocess.PIPE, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    h = int(SR * HOP)
    n = len(x) // h
    return 10 * np.log10(np.mean(np.square(x[: n * h].reshape(n, h)), axis=1) + 1e-10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mic1")
    ap.add_argument("mic2")
    ap.add_argument("--names", nargs=2, default=["host", "guest"])
    ap.add_argument("--lead", type=float, default=6.0)
    ap.add_argument("--min", type=float, default=0.7)
    ap.add_argument("--out", default="speakers.json")
    a = ap.parse_args()
    d1, d2 = db(a.mic1), db(a.mic2)
    n = min(len(d1), len(d2))
    d1, d2 = d1[:n], d2[:n]
    floor1, floor2 = np.percentile(d1, 20) + 8, np.percentile(d2, 20) + 8  # "talking" = 8 dB over the room
    lab = np.full(n, "", dtype=object)
    for i in range(n):
        on1, on2 = d1[i] > floor1, d2[i] > floor2
        if not on1 and not on2:
            lab[i] = "silence"
        elif d1[i] - d2[i] >= a.lead:
            lab[i] = a.names[0]
        elif d2[i] - d1[i] >= a.lead:
            lab[i] = a.names[1]
        else:
            lab[i] = "both" if on1 and on2 else (a.names[0] if on1 else a.names[1])
    # runs of equal labels, then absorb the short ones
    runs = []
    for i, l in enumerate(lab):
        if runs and runs[-1][2] == l:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1, l])
    minlen = int(a.min / HOP)

    def merge_equal(rs):
        out = []
        for q in rs:
            if out and out[-1][2] == q[2]:
                out[-1][1] = q[1]
            else:
                out.append(list(q))
        return out

    # each pass hands every too-short run to its longer neighbour (O(n) per pass, a few passes)
    for _ in range(50):
        short = [k for k, r in enumerate(runs) if r[1] - r[0] < minlen]
        if not short or len(runs) == 1:
            break
        for k in short:
            r = runs[k]
            left = runs[k - 1] if k > 0 else None
            right = runs[k + 1] if k + 1 < len(runs) else None
            nb = left if right is None or (left is not None and left[1] - left[0] >= right[1] - right[0]) else right
            r[2] = nb[2]
        runs = merge_equal(runs)
    segs = [{"from": round(r[0] * HOP, 1), "to": round(r[1] * HOP, 1), "who": r[2]} for r in runs]
    total = sum(s["to"] - s["from"] for s in segs if s["who"] in a.names)
    share = {nm: round(sum(s["to"] - s["from"] for s in segs if s["who"] == nm) / max(total, 1e-9), 3) for nm in a.names}
    Path(a.out).write_text(json.dumps({"hop": HOP, "segments": segs, "talk_share": share}, ensure_ascii=False), encoding="utf-8")
    print(f"{len(segs)} segments · talk share {share}")


if __name__ == "__main__":
    main()
