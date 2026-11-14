# -*- coding: utf-8 -*-
"""Remaining pauses in a reel project's VOICE (base footage segments with volume > 0), as ripple cuts.

    python reel_pauses.py "<project>" [--min 0.6] [--keep 0.15] [--floor -45] [--skip-after-card 0.3] > cuts.txt

A pause = the voice under `--floor` dBFS (10 ms RMS) for at least `--min` s; the cut keeps `--keep` s on
each side (Alon, 0923 round 3: «לצמצם עוד קצת את זמן השקט ואז להחליף מצלמה / בירול / זום-אין»). Output:
`a:b,a:b,…` project seconds, ready for `reel_ripple.py --cuts`. Read-only.
"""
import argparse, json, os, re, subprocess, sys, numpy as np
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
US = 1_000_000; FF = str(paths.FFMPEG); SR = 16000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--min", type=float, default=0.6); ap.add_argument("--keep", type=float, default=0.15); ap.add_argument("--floor", type=float, default=-45.0); ap.add_argument("--skip-after-card", type=float, default=0.3)
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); vm = {m["id"]: m for m in d["materials"]["videos"]}
res = lambda p: re.sub(r"##_draftpath_placeholder_[^#]+_##", str(D), p)
base = sorted([t for t in d["tracks"] if t["type"] == "video"][0]["segments"], key=lambda s: s["target_timerange"]["start"]); cuts = []
for s in base:
    m = vm[s["material_id"]]
    if m.get("type") != "video" or s.get("volume", 1) <= 0: continue
    a = s["target_timerange"]["start"] / US; L = s["target_timerange"]["duration"] / US; src = s["source_timerange"]["start"] / US
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{src:.4f}", "-t", f"{L:.4f}", "-i", res(m["path"]), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout; x = np.frombuffer(raw, np.float32)
    hop = SR // 100; k = len(x) // hop; e = 20 * np.log10(np.sqrt((x[:k * hop].reshape(k, hop) ** 2).mean(1)) + 1e-9); q = e < A.floor; i = 0
    while i < k:
        if q[i]:
            j = i
            while j < k and q[j]: j += 1
            if (j - i) / 100 >= A.min:
                p0, p1 = a + i / 100, a + j / 100
                if p0 > a + A.skip_after_card and p1 < a + L - 0.05:   # not the head of a piece after a card, not the tail
                    cuts.append((round(p0 + A.keep, 2), round(p1 - A.keep, 2)))
            i = j
        else: i += 1
print(",".join(f"{a}:{b}" for a, b in cuts)); print(f"# {len(cuts)} pauses ≥ {A.min}s → −{sum(b - a for a, b in cuts):.2f}s", file=sys.stderr)
