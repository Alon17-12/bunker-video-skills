#!/usr/bin/env python3
"""Routing patches without flashes (Alon, אלון+אייל+דולב 21.10.2026: «תוודא שהקאטים שנוצרים בשילוב תיקוני הניתוב שלך לא
יוצרים קפיצת פריים אגרסיבית» — 290 of 330 shots ≤ 1 s in the patched episode came from a patch edge meeting a live cut).

    routing_smooth.py <session> [--in <patches>] [--out <patches>] [--min 1.2] [--min-live 0.6]

1. Every live cut of «מקור» (where routing_audit's 0.5 s samples change camera) is found to the frame: «מקור» against
   camera 1 and camera 2 at full rate around it.
2. What is on screen = the live cut, overlaid by the patches, at those exact edges.
3. A shot shorter than --min between two shots of the same camera, that touches a patch, takes that camera (the patch
   grows over it, or two patches join); a live director's flash shorter than --min-live does too.
4. The patches are written again as exactly "on screen ≠ live", so every patch edge is either a live cut or one of
   the original speech-based edges.
"""
import argparse, json, subprocess
from pathlib import Path
import numpy as np

FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
W, H = 64, 36


def grab(path, a, b):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(path), "-vf", f"scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], stdout=subprocess.PIPE, check=True).stdout
    x = np.frombuffer(raw, np.uint8).astype(np.float32).reshape(-1, W * H)
    x -= x.mean(1, keepdims=True)
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-6)


def exact_cut(ing, t0, t1, new, fps):
    """first frame in [t0, t1] where «מקור» matches camera `new` best"""
    a, b = t0 - 0.05, t1 + 0.05
    s, c1, c2 = grab(ing["source"], a, b), grab(ing["cam1"], a, b), grab(ing["cam2"], a, b)
    n = min(len(s), len(c1), len(c2))
    for i in range(n):
        r1, r2 = float(s[i] @ c1[i]), float(s[i] @ c2[i])
        best = 1 if r1 > r2 else 2
        if best == new and max(r1, r2) > 0.6:
            return round(a + i / fps, 3)
    return round((t0 + t1) / 2, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--in", dest="inp"); ap.add_argument("--out")
    ap.add_argument("--min", type=float, default=1.2); ap.add_argument("--min-live", type=float, default=0.6)
    a = ap.parse_args()
    S = Path(a.session)
    ing = json.loads((S / "ingest.json").read_text())
    fps = float(eval(subprocess.run([str(Path.home() / "ffmpeg-bin/ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                                     "-of", "csv=p=0", ing["source"]], capture_output=True, text=True).stdout.strip()))
    samples = json.loads((S / "פרק/ניתוב.json").read_text())["samples"]
    P = json.loads(Path(a.inp or S / "פרק/תיקוני-ניתוב.json").read_text())
    t_end = samples[-1]["t"] + 0.5
    # 1. live timeline at frame precision
    live = [[samples[0]["t"], samples[0]["air"]]]
    for p, q in zip(samples, samples[1:]):
        if q["air"] != p["air"]:
            t = exact_cut(ing, p["t"], q["t"], q["air"], fps) if q["air"] in (1, 2) else q["t"] - 0.25
            live.append([t, q["air"]])
    print(f"live cuts: {len(live) - 1}", flush=True)
    live_at = lambda t: next(c for x, c in reversed(live) if x <= t + 1e-6) if t >= live[0][0] else live[0][1]
    # 2. on screen
    edges = sorted({x for x, _ in live} | {x for _, f, g in P for x in (f, g)} | {t_end})
    patch_at = lambda t: next((c for c, f, g in P if f <= t < g), None)
    shots = []
    for x, y in zip(edges, edges[1:]):
        m = (x + y) / 2
        pc = patch_at(m); c = pc or live_at(m)
        if shots and shots[-1][2] == c and shots[-1][3] == (pc is not None):
            shots[-1][1] = y
        else:
            shots.append([x, y, c, pc is not None])
    # merge same camera (patched or not) into shots as the viewer sees them
    view = []
    for s in shots:
        if view and view[-1][2] == s[2]:
            view[-1][1] = s[1]; view[-1][3] |= s[3]
        else:
            view.append(list(s))
    before = sum(1 for i in range(1, len(view) - 1) if view[i][1] - view[i][0] < a.min and view[i - 1][2] == view[i + 1][2])
    # 3. absorb flashes
    changed = True
    while changed:
        changed = False
        for i in range(1, len(view) - 1):
            p, s, n = view[i - 1], view[i], view[i + 1]
            d = s[1] - s[0]
            if p[2] == n[2] and p[2] in (1, 2) and ((d < a.min and (p[3] or s[3] or n[3])) or d < a.min_live):
                p[1] = n[1]; p[3] = True
                del view[i:i + 2]; changed = True
                break
    after = sum(1 for i in range(1, len(view) - 1) if view[i][1] - view[i][0] < a.min and view[i - 1][2] == view[i + 1][2])
    # 4. patches = on screen ≠ live
    edges = sorted({x for x, _ in live} | {v[0] for v in view} | {t_end})
    out = []
    for x, y in zip(edges, edges[1:]):
        m = (x + y) / 2
        v = next(v for v in view if v[0] <= m < v[1])[2]
        if v in (1, 2) and v != live_at(m):
            if out and out[-1][0] == v and abs(out[-1][2] - x) < 1e-6:
                out[-1][2] = round(y, 3)
            else:
                out.append([v, round(x, 3), round(y, 3)])
    short = [v for v in view if v[1] - v[0] < 1.0]
    dst = Path(a.out or S / "פרק/תיקוני-ניתוב.json")
    dst.write_text(json.dumps(out))
    print(json.dumps({"patches_in": len(P), "patches_out": len(out), "flashes_before": before, "flashes_after": after,
                      "shots_under_1s": len(short), "out": str(dst)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
