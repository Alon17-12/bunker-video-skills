#!/usr/bin/env python3
"""Every frame a camera is on screen → a patch from that camera's own file, so it can be reframed in one place (Alon,
אורח C 27.10.2026: «הראש של עומר ממצלמה 1 נכנס לפריים של מצלמה 2 … זום אין קבוע»). «מקור» shows that camera too
wherever it was live; those frames are only the spine and cannot be zoomed without splitting it, so they become patches.

    routing_cover.py <session> --in <frame patches> --out <patches> --cam 2
    episode_repatch.py "<project>" "<project> v3" <patches> --trim-in <s> --zoom 2=1.12:-0.12

Patches of the other camera stay as they are. Each new run keeps the camera file's offset against «מקור» (median over the run,
from the same matching as routing_frames.py), so the patch is frame-for-frame what «מקור» showed.
"""
import argparse, json
from pathlib import Path
import numpy as np

FPS = 30.0


def norm(x):
    x = x.astype(np.float32); x -= x.mean(1, keepdims=True)
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--cam", type=int, required=True)
    a = ap.parse_args()
    F = Path(a.session) / ".tmp/frames"
    S, C = np.load(F / "source.npy"), {1: np.load(F / "cam1.npy"), 2: np.load(F / "cam2.npy")}
    n = min(len(S), len(C[1]), len(C[2]))
    R, CH = 3, 20000
    best = {k: np.full(n, -1.0, np.float32) for k in (1, 2)}
    boff = {k: np.zeros(n, np.int8) for k in (1, 2)}
    for c0 in range(0, n, CH):
        c1 = min(n, c0 + CH)
        s = norm(S[c0:c1])
        for k in (1, 2):
            for o in range(-R, R + 1):
                lo, hi = max(c0, -o), min(c1, n - o)
                if hi <= lo:
                    continue
                r = np.einsum("ij,ij->i", s[lo - c0:hi - c0], norm(C[k][lo + o:hi + o]))
                seg = best[k][lo:hi]; m = r > seg
                seg[m] = r[m]; boff[k][lo:hi][m] = o
    live = np.where(np.maximum(best[1], best[2]) < 0.75, 0, np.where(best[1] >= best[2], 1, 2)).astype(np.int8)
    P = json.loads(Path(a.inp).read_text())
    screen = live.copy(); off = np.zeros(n, np.int16); patched = np.zeros(n, bool)
    for p in P:
        f, g = int(round(p[1] * FPS)), int(round(p[2] * FPS))
        screen[f:g] = p[0]; patched[f:g] = True
        off[f:g] = int(round((p[3] if len(p) > 3 else 0.0) * FPS))
    for i in range(1, n):                      # a frame «מקור» matched to neither camera keeps the shot it sits in
        if screen[i] == 0:
            screen[i] = screen[i - 1]
    k = a.cam
    cut = np.flatnonzero(np.diff(screen)) + 1
    out = [p for p in P if p[0] != k]
    added = 0
    for s0, e0 in zip(np.r_[0, cut], np.r_[cut, n]):
        if screen[s0] != k:
            continue
        live_k = (~patched[s0:e0]) & (live[s0:e0] == k)
        o = int(np.median(boff[k][s0:e0][live_k])) if live_k.any() else int(np.median(off[s0:e0]))
        out.append([k, round(s0 / FPS, 4), round(e0 / FPS, 4), round(o / FPS, 4)]); added += 1
    out.sort(key=lambda p: p[1])
    Path(a.out).write_text(json.dumps(out))
    print(json.dumps({"frames": int(n), "cam": k, "on_screen_s": round(float((screen == k).sum()) / FPS, 1),
                      f"cam{k}_runs": added, "patches_in": len(P), "patches_out": len(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
