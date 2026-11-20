#!/usr/bin/env python3
"""Routing patches to the exact frame (Alon, אלון+אייל+דולב 21.10.2026: «בפרק השלם בערך ב-0:40 הייתה קפיצה של הפריים בצורה לא
נקייה וחדה»). routing_smooth.py placed some edges on the 0.5 s audit grid (up to 14 frames of the wrong camera after a patch)
and the camera files drift ±1 frame against «מקור» (a one-frame sliver / stutter where a patch meets the live mix).

    decode_small.py <מקור|1|2.mp4> <session>/.tmp/frames/{source,cam1,cam2}.npy      (once; 64x36 gray @30)
    routing_frames.py <session> --in <patches> --out <patches> [--min 0.5] [--min-patch 1.2]

1. Every frame of «מקור» gets a camera (1/2, matched against both camera files at offsets −3…+3 frames; 0 = neither)
   and, per camera, the offset at which that camera file lines up with «מקור» (median over 10 s).
2. On screen = the patches over that live labelling, frame by frame.
3. A shot shorter than --min between two shots of the same camera takes that camera; shorter than --min-patch when it
   touches a patch, too.
4. Patches = the frames where on screen ≠ live, edges on frame boundaries, each with the source offset that keeps its
   camera file in step with «מקור»: [cam, from, to, src_offset_s] (episode_repatch.py reads the 4th field).

Without --words a split screen in «מקור» (label 0) inherits the camera before it and gets patched away — every split of the episode goes,
and the wrong person is on screen whenever the speaker changed during one (אורח V, 1.11.2026: 38 % of the episode was split, 11.4 % wrong).
With --words <transcript.json> (word list on the «מקור» clock, each with its mic) a split stays only where it is an exchange — both speakers
talk inside ±--exch s, the quieter one at least --exch-min s — and in a monologue it becomes the speaker's camera (house rule: a split on
exchanges, never in a monologue). --mic-cam 1=1,2=2 maps mics to cameras.
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
    ap.add_argument("--min", type=float, default=0.5); ap.add_argument("--min-patch", type=float, default=1.2)
    ap.add_argument("--words"); ap.add_argument("--mic-cam", default="1=1,2=2"); ap.add_argument("--exch", type=float, default=4.0)
    ap.add_argument("--exch-min", type=float, default=0.8)
    a = ap.parse_args()
    F = Path(a.session) / ".tmp/frames"
    S, C = np.load(F / "source.npy"), {1: np.load(F / "cam1.npy"), 2: np.load(F / "cam2.npy")}
    n = min(len(S), len(C[1]), len(C[2]))
    R = 3
    best = {k: np.full(n, -1.0, np.float32) for k in (1, 2)}
    boff = {k: np.zeros(n, np.int8) for k in (1, 2)}
    CH = 20000
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
    # per-camera offset, smoothed: median of the offsets over ±5 s where live shows that camera
    offs = {}
    for k in (1, 2):
        o = np.zeros(n, np.int8); W = int(5 * FPS)
        idx = np.where(live == k)[0]
        vals = boff[k][idx]
        for i0 in range(0, n, int(FPS)):
            j = np.searchsorted(idx, [i0 - W, i0 + W])
            v = vals[j[0]:j[1]]
            o[i0:i0 + int(FPS)] = int(np.median(v)) if len(v) else 0
        offs[k] = o
    P = json.loads(Path(a.inp).read_text())
    patched = np.zeros(n, bool); screen = live.copy()
    for p in P:
        f, g = int(round(p[1] * FPS)), int(round(p[2] * FPS))
        screen[f:g] = p[0]; patched[f:g] = True
    if a.words:
        # a live split stays on an exchange; in a monologue it becomes the speaker's camera
        mc = {int(k): int(v) for k, v in (x.split("=") for x in a.mic_cam.split(","))}
        W = json.loads(Path(a.words).read_text())["words"]
        talk = {k: np.zeros(n + 1, np.float32) for k in mc}          # frames of speech per mic
        spk = np.zeros(n, np.int8)
        for w in W:
            if w.get("mic") not in mc: continue
            f, g = int(w["start_s"] * FPS), min(int(w["end_s"] * FPS) + 1, n)
            if f < g: talk[w["mic"]][f:g] = 1; spk[f:g] = w["mic"]
        cum = {k: np.r_[0, np.cumsum(v)] for k, v in talk.items()}
        R_ = int(a.exch * FPS)
        lo, hi = np.clip(np.arange(n) - R_, 0, n), np.clip(np.arange(n) + R_, 0, n)
        amount = np.array([cum[k][hi] - cum[k][lo] for k in sorted(mc)]) / FPS
        exch = amount.min(0) >= a.exch_min
        # the speaker of a silent frame = the next word within 1 s, else the last one
        last = 0; nearest = spk.copy()
        for i in range(n):
            if spk[i]: last = spk[i]
            else: nearest[i] = last
        nxt = 0; gap = 10 ** 9
        for i in range(n - 1, -1, -1):
            if spk[i]: nxt, gap = spk[i], 0
            else:
                gap += 1
                if gap <= FPS and nxt: nearest[i] = nxt
        zero = screen == 0
        cams = np.array([0] + [mc.get(k, 0) for k in range(1, max(mc) + 1)], np.int8)[np.clip(nearest, 0, max(mc))]
        drop = zero & ~exch & (cams > 0)
        screen[drop] = cams[drop]; patched[drop] = True
        view = screen.copy()
    else:
        # unknown live frames (label 0) keep the neighbouring camera for the shot logic
        view = screen.copy()
        for i in range(1, n):
            if view[i] == 0:
                view[i] = view[i - 1]

    def runs(v):
        cut = np.flatnonzero(np.diff(v)) + 1
        st = np.r_[0, cut]; en = np.r_[cut, len(v)]
        return list(zip(st, en))
    before = sum(1 for (s0, e0), (s1, e1), (s2, e2) in zip(*(runs(view)[i:] for i in range(3)))
                 if view[s0] == view[s2] and (e1 - s1) < a.min * FPS)
    changed = True
    while changed:
        changed = False
        rr = runs(view)
        for (s0, e0), (s1, e1), (s2, e2) in zip(rr, rr[1:], rr[2:]):
            d = e1 - s1
            if view[s0] == view[s2] and (d < a.min * FPS or (d < a.min_patch * FPS and patched[max(0, s0):e2].any())):
                view[s1:e1] = view[s0]; patched[s1:e1] = True; changed = True
        # one pass per loop is enough to converge
        if a.words and not changed:
            # a shot too short to read between two different framings takes the one before it, unless that fakes a split
            rr = runs(view)
            for (s0, e0), (s1, e1), (s2, e2) in zip(rr, rr[1:], rr[2:]):
                if (e1 - s1) < a.min_patch * FPS and patched[s1:e1].any() and view[s1] != view[s0]:
                    if view[s0] != 0:
                        view[s1:e1] = view[s0]; patched[s1:e1] = True; changed = True; break
                    if (live[s1:e1] == 0).all():      # a short monologue patch inside a split stays the split
                        view[s1:e1] = 0; changed = True; break
    if a.words:
        # nothing under --min on screen: a sliver joins the neighbouring camera, the longer one when both are cameras
        again = True
        while again:
            again = False
            rr = runs(view)
            for i in range(1, len(rr) - 1):
                s1, e1 = rr[i]
                if e1 - s1 >= a.min * FPS: continue
                nb = [rr[i - 1], rr[i + 1]]
                cand = [x for x in nb if view[x[0]] != 0 and view[x[0]] != view[s1]]
                if not cand: continue
                best_nb = max(cand, key=lambda x: x[1] - x[0])
                view[s1:e1] = view[best_nb[0]]; patched[s1:e1] = True; again = True; break
    after = sum(1 for (s0, e0), (s1, e1), (s2, e2) in zip(*(runs(view)[i:] for i in range(3)))
                if view[s0] == view[s2] and (e1 - s1) < a.min * FPS)
    # a frame that «מקור» shows as a camera cannot become a split: a split neighbour absorbed nothing, so it keeps its camera
    want = np.where((view != live) & (view > 0), view, 0)
    out = []
    for s0, e0 in runs(want):
        k = int(want[s0])
        if not k:
            continue
        o = int(np.median(offs[k][s0:e0]))
        out.append([k, round(s0 / FPS, 4), round(e0 / FPS, 4), round(o / FPS, 4)])
    Path(a.out).write_text(json.dumps(out))
    print(json.dumps({"frames": int(n), "live_unknown": int((live == 0).sum()), "patches_in": len(P), "patches_out": len(out),
                      "short_shots_before": before, "short_shots_after": after,
                      "offsets": {k: {int(v): int((offs[k] == v).sum()) for v in np.unique(offs[k])} for k in (1, 2)}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
