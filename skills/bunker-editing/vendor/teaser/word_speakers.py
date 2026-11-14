#!/usr/bin/env python3
"""Who said each word — measured per WORD on the two lavalier/podcast mics, not from smoothed speaker segments.

    word_speakers.py --mic host=work/mic1.wav --mic guest=work/mic2.wav public/teaser.json public/reel1.json … [--dry]

Each word of a cut json ({clips:[{at,end,src}], words:[{text,at,end,clip,who}]}) is mapped back to the episode clock
(src + at - clip.at); the louder mic over the word's span (≥ --lead dB) owns it. A word where neither mic leads
(cross-talk, a breath) inherits its neighbour. The cut json is rewritten in place and the changes are printed.
Why: the 0.1 s-hop segments with run smoothing (speakers.py) swallowed short host interjections and gave the first
words of a turn to the previous speaker — Alon read that as "inaccurate routing" in the reels (11.10.2026).
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

FF = str(Path.home() / "ffmpeg-bin" / "ffmpeg")


def load(p):
    raw = subprocess.run([FF, "-v", "error", "-i", p, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cuts", nargs="+")
    ap.add_argument("--mic", action="append", required=True, help="who=path")
    ap.add_argument("--lead", type=float, default=6.0)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    mics = {}
    for m in a.mic:
        k, p = m.split("=", 1)
        mics[k] = load(p)
    names = list(mics)

    def db(x, t0, t1):
        i0, i1 = int(max(0, t0) * 16000), int(t1 * 16000)
        seg = x[i0:max(i1, i0 + 160)]
        return 10 * np.log10(np.mean(seg ** 2) + 1e-10)

    for f in a.cuts:
        cut = json.loads(Path(f).read_text(encoding="utf-8"))
        clips = cut["clips"]
        whos = []
        for w in cut["words"]:
            c = clips[w["clip"]]
            s0 = c["src"] + w["at"] - c["at"]
            s1 = c["src"] + w["end"] - c["at"]
            e = {k: db(mics[k], s0 + 0.02, s1 - 0.02) for k in names}
            best = max(e, key=e.get)
            other = min(e, key=e.get)
            whos.append(best if e[best] - e[other] >= a.lead else None)
        # undecided words inherit the nearest decided neighbour in the same clip
        for i, w in enumerate(cut["words"]):
            if whos[i] is None:
                for d in range(1, 6):
                    for j in (i - d, i + d):
                        if 0 <= j < len(whos) and whos[j] and cut["words"][j]["clip"] == w["clip"]:
                            whos[i] = whos[j]; break
                    if whos[i]: break
            whos[i] = whos[i] or w["who"]
        ch = [(w["at"], w["text"], w["who"], n) for w, n in zip(cut["words"], whos) if w["who"] != n]
        print(f"{f}: {len(ch)} of {len(whos)} words change speaker")
        for at, t, o, n in ch:
            print(f"   {at:7.2f}  {t:14} {o} → {n}")
        if not a.dry:
            for w, n in zip(cut["words"], whos):
                w["who"] = n
            Path(f).write_text(json.dumps(cut, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
