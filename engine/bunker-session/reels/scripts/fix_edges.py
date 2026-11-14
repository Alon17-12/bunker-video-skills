#!/usr/bin/env python3
"""Every inner clip edge onto the real pause in the voice, from the envelope, not from Whisper's word times (אלון+אייל+דולב
26.10.2026: «חיתוכי קול» — 60 of 114 edges still carried speech in their last/first 30 ms: a syllable clipped, or a breath
of the next word leaking in).

  end of a clip:   walk forward from its last word to the first 30 ms under PAUSE, end AIR_T after it — never into the
                   next transcript word (kept or cut out). No pause there (cross-talk, words that run together) → the
                   quietest 10 ms between the two words.
  start of a clip: the same backwards from its first word, AIR_H before the first quiet frame.

    python3 fix_edges.py <session> [rN …]          (after recut.py; the plans' word anchors survive, times shift)
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from rpaths import session_paths

S, RM, PUB, WORK = session_paths(sys.argv[:2])
FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
x = np.frombuffer(subprocess.run([FF, "-v", "error", "-i", str(WORK / "dialogue16k.wav"), "-f", "f32le", "-"],
                                 stdout=subprocess.PIPE, check=True).stdout, np.float32)
env = 20 * np.log10(np.sqrt((x[: len(x) // 160 * 160].reshape(-1, 160) ** 2).mean(1)) + 1e-9)
PAUSE, AIR_T, AIR_H = -40.0, 0.07, 0.05
fr = lambda t: int(round(t / 0.01))
TW = sorted((w for w in json.loads((WORK / "words.json").read_text()) if w["w"].strip()), key=lambda w: w["t"])


def quiet(a, b):
    i, j = fr(a), max(fr(a) + 1, fr(b))
    return (i + int(np.argmin(env[i:j]))) * 0.01


def calm(i):  # 3 frames (30 ms) under the pause level
    return env[i:i + 3].max() < PAUSE


def tail(last_end):
    nxt = [w["t"] for w in TW if w["t"] > last_end - 0.02]
    hi = (nxt[0] if nxt else last_end + 0.6) - 0.03
    if hi - last_end < 0.06:
        return quiet(last_end - 0.03, last_end + 0.06)
    for i in range(fr(last_end - 0.04), fr(hi)):
        if calm(i):
            return min(hi, i * 0.01 + AIR_T)
    return quiet(last_end, hi)


def head(first):
    prv = [w["end"] for w in TW if w["end"] < first + 0.02]
    lo = (prv[-1] if prv else first - 0.6) + 0.03
    if first - lo < 0.06:
        return quiet(first - 0.06, first + 0.03)
    for i in range(fr(first + 0.03), fr(lo), -1):
        if calm(i - 3):
            return max(lo, i * 0.01 - 0.03 - AIR_H)
    return quiet(lo, first)


ids = sys.argv[2:] or [k for k in json.loads((PUB / "plans.json").read_text()) if not k.startswith("_")]
for rid in ids:
    f = PUB / f"{rid}.json"
    cut = json.loads(f.read_text())
    cl = cut["clips"]
    seg = []
    for i, c in enumerate(cl):
        ws = [w for w in cut["words"] if w["clip"] == i]
        s, e = c["src"], c["src"] + c["end"] - c["at"]
        sp = [w for w in ws if w["text"].strip()]
        if sp:
            if i > 0:
                s = head(c["src"] + sp[0]["at"] - c["at"])
            if i < len(cl) - 1:
                e = tail(c["src"] + sp[-1]["end"] - c["at"])
        seg.append((round(s, 3), round(e, 3), c, ws))
    t, moved = 0.0, 0
    for i, (s, e, c, ws) in enumerate(seg):
        if i and s < seg[i - 1][1] and s > seg[i - 1][0]:   # never re-play what the previous clip plays
            s = seg[i - 1][1]
        moved += (abs(s - c["src"]) > 0.005) + (abs(e - (c["src"] + c["end"] - c["at"])) > 0.005)
        for w in ws:
            for k in ("at", "end"):
                w[k] = round(t + (c["src"] + w[k] - c["at"]) - s, 3)
        c.update({"src": s, "at": round(t, 3), "end": round(t + e - s, 3)})
        t += e - s
    cut["duration"] = round(t, 3)
    f.write_text(json.dumps(cut, ensure_ascii=False))
    print(f"{rid}: {moved} edges moved · {t:.2f}s")
