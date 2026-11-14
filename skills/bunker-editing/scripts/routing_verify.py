#!/usr/bin/env python3
"""What the episode project really shows around every routing patch — frame by frame, before and after each edge (Alon,
אלון+אייל+דולב 21.10.2026: «בפרק השלם בערך ב-0:40 הייתה קפיצה של הפריים בצורה לא נקייה וחדה … בכל מקום שהכנסת תיקון תוודא
לפני ואחרי שהפריימים רצים בצורה חלקה»).

    routing_verify.py <session> "<CapCut project name>" [--pad 0.6] [--json out.json]

For every edge of a segment on the «ניתוב» track (± --pad s, at the full frame rate) the frame CapCut shows is taken from the
file it shows (the patch's camera file, else «מקור» under it) and labelled camera 1 / 2 by matching it against both camera
files at that moment. Reported:
  flash  — a camera on screen for less than --flash s between two shots of the other camera (incl. 1–3 frame slivers
           where a patch edge misses the live cut by a frame or two);
  jump   — the camera stays the same across the edge but the picture jumps (patch file vs «מקור» out of sync / reframed);
  stutter— the same: the patch's camera file (with its source offset) is a frame or more off «מקור» at the edge;
  sync   — per camera, the frame offset between the camera file and «מקור» (information).
Exit 1 if anything is found.
"""
import argparse, json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
DRAFTS = Path.home() / "Movies/CapCut/User Data/Projects/com.lveditor.draft"
W, H = 96, 54
US = 1_000_000


def grab(path, a, n, fps):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{max(0, a):.4f}", "-i", str(path), "-frames:v", str(n), "-vf",
                          f"fps={fps},scale={W}:{H},format=gray", "-f", "rawvideo", "-"], stdout=subprocess.PIPE, check=True).stdout
    x = np.frombuffer(raw, np.uint8).astype(np.float32).reshape(-1, W * H)
    x = x - x.mean(1, keepdims=True)
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("project")
    ap.add_argument("--pad", type=float, default=0.6); ap.add_argument("--flash", type=float, default=0.5)
    ap.add_argument("--jump", type=float, default=0.80, help="consecutive-frame match below this on the same camera = jump")
    ap.add_argument("--json")
    a = ap.parse_args()
    ing = json.loads((Path(a.session) / "ingest.json").read_text())
    P = DRAFTS / a.project
    d = json.loads((P / "draft_info.json").read_text())
    mats = {m["id"]: m for k, v in d["materials"].items() if isinstance(v, list) for m in v if isinstance(m, dict) and "id" in m}
    base = next(t for t in d["tracks"] if t["type"] == "video" and any("מקור" in mats[s["material_id"]]["path"] for s in t["segments"]))
    bseg = base["segments"][0]
    off = (bseg["source_timerange"]["start"] - bseg["target_timerange"]["start"]) / US        # source = timeline + off
    tr = next(t for t in d["tracks"] if t.get("name") == "ניתוב")
    segs = []
    for s in tr["segments"]:
        p = re.sub(r"##_draftpath_placeholder_[0-9A-F-]+_##", str(P), mats[s["material_id"]]["path"])
        a0 = s["target_timerange"]["start"] / US
        segs.append((a0, a0 + s["target_timerange"]["duration"] / US, 1 if p.endswith(" 1.mp4") else 2,
                     s["source_timerange"]["start"] / US - a0))
    fps = 30.0
    files = {0: ing["source"], 1: ing["cam1"], 2: ing["cam2"]}
    edges = sorted({round(x, 4) for s in segs for x in (s[0], s[1])})
    # windows: merge overlapping edge windows
    wins = []
    for e in edges:
        f0, f1 = int(np.floor((e - a.pad) * fps)), int(np.ceil((e + a.pad) * fps))
        if wins and f0 <= wins[-1][1]:
            wins[-1][1] = max(wins[-1][1], f1)
        else:
            wins.append([f0, f1])

    def on_screen(t):
        for s in segs:
            if s[0] <= t < s[1]:
                return s[2], s[3]
        return 0, off

    M = 4                                  # extra frames grabbed each side of a camera file (patch offsets ±M)

    def check(w):
        f0, f1 = w
        n = f1 - f0
        t0 = f0 / fps
        src = {0: grab(files[0], t0 + off, n, fps)}
        for k in (1, 2):
            src[k] = grab(files[k], t0 + off - M / fps, n + 2 * M, fps)
        n = min(len(src[0]), len(src[1]) - 2 * M, len(src[2]) - 2 * M)
        live_cam = lambda k, i, d=0: src[k][i + M + d]
        frames, labels, srcmis, stutter = [], [], [], []
        for i in range(n):
            t = t0 + (i + 0.5) / fps
            k, o = on_screen(t)
            d = int(round((o - off) * fps)) if k else 0
            if abs(d) > M:
                srcmis.append(round(t, 3)); d = 0
            f = src[0][i] if not k else live_cam(k, i, d)
            r1, r2 = float(f @ live_cam(1, i)), float(f @ live_cam(2, i))
            frames.append(f); labels.append((1 if r1 >= r2 else 2, k, round(max(r1, r2), 3), d))
        # same camera across a layer change: the camera file (with the patch's shift) must line up with «מקור» there
        for i in range(1, n):
            (c0, k0, _, d0), (c1, k1, _, d1) = labels[i - 1], labels[i]
            if c0 == c1 and k0 != k1:
                kk, dd = (k1, d1) if k1 else (k0, d0)
                lo, hi = max(0, i - 4), min(n, i + 4)
                sc = [np.mean([float(src[0][j] @ live_cam(kk, j, dd + e)) for j in range(lo, hi)]) for e in range(-2, 3)
                      if abs(dd + e) <= M]
                es = [e for e in range(-2, 3) if abs(dd + e) <= M]
                if es[int(np.argmax(sc))] != 0:
                    stutter.append({"t": round((f0 + i) / fps, 3), "cam": c1, "off_by_frames": es[int(np.argmax(sc))]})
        return f0, frames, labels, srcmis, stutter

    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(check, wins))
    flashes, jumps, misclock, low = [], [], [], []
    stutters = []
    for f0, frames, labels, srcmis, st in res:
        misclock += srcmis; stutters += st
        cams = [l[0] for l in labels]
        # runs
        runs, i = [], 0
        while i < len(cams):
            j = i
            while j < len(cams) and cams[j] == cams[i]:
                j += 1
            runs.append((i, j, cams[i])); i = j
        for (pi, pj, pc), (i, j, c), (ni, nj, nc) in zip(runs, runs[1:], runs[2:]):
            if pc == nc and (j - i) / fps < a.flash:
                flashes.append({"t": round((f0 + i) / fps, 3), "frames": j - i, "cam": c, "around": pc})
        for i in range(1, len(frames)):
            if cams[i] == cams[i - 1] and labels[i][1] != labels[i - 1][1]:      # same camera, the layer changed
                r = float(frames[i] @ frames[i - 1])
                if r < a.jump:
                    jumps.append({"t": round((f0 + i) / fps, 3), "match": round(r, 3), "cam": cams[i]})
        for i, l in enumerate(labels):
            if l[2] < 0.6:
                low.append(round((f0 + i) / fps, 3))
    # sync: where «מקור» shows camera k, the offset (frames) at which camera k's file matches best
    sync = {1: [], 2: []}
    for t in np.linspace(60, min(1200, edges[-1]), 24):
        m = grab(files[0], t + off, 1, fps)
        best = max(((k, c @ m[0]) for k in (1, 2) for c in [grab(files[k], t + off - 5 / fps, 11, fps)]), key=lambda kr: kr[1].max())
        if best[1].max() > 0.9:
            sync[best[0]].append(int(np.argmax(best[1])) - 5)
    out = {"project": a.project, "edges": len(edges), "flashes": flashes, "jumps": jumps, "stutters": stutters, "sync_offsets": sync,
           "patch_offset_over_4f": misclock[:20], "unmatched_frames": len(low)}
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: (v if not isinstance(v, list) or len(v) < 30 else f"{len(v)} items") for k, v in out.items()}, ensure_ascii=False, indent=1))
    sys.exit(1 if flashes or jumps or stutters else 0)


if __name__ == "__main__":
    main()
