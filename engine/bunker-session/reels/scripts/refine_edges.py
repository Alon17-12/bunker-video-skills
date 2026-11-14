#!/usr/bin/env python3
"""Every clip edge onto the real pause in the voice (Alon, לקוח A 20.10.2026: «יש כמה מקומות שהסאונד בהם נחתך»).

Whisper's word times drift by tens of ms, so an edge taken from them can sit inside a syllable (55 of 138 edges carried
speech energy). Per clip: walk the start back / the end forward on the dialogue envelope (10 ms) to the first frame
under the pause level, and stop there — never past that pause, so the neighbouring word does not leak in.

    python3 refine_edges.py <session> [rN.json …]      (after build_cuts.py; then make the plans again)
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from rpaths import session_paths

S, RM, PUB, WORK = session_paths(sys.argv)
FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
x = np.frombuffer(subprocess.run([FF, "-v", "error", "-i", str(WORK / "dialogue16k.wav"), "-f", "f32le", "-"],
                                 stdout=subprocess.PIPE, check=True).stdout, np.float32)
HOP = 160                                                   # 10 ms
env = 20 * np.log10(np.sqrt((x[: len(x) // HOP * HOP].reshape(-1, HOP) ** 2).mean(1)) + 1e-9)
PAUSE, SPEECH = -40.0, -32.0                                # dBFS on the -14 LUFS dialogue master
fr = lambda t: int(round(t / 0.01))
TW = sorted(json.loads((WORK / "words.json").read_text()), key=lambda w: w["t"])     # the whole transcript, source clock
loud = lambda a, b: env[max(0, fr(a)):max(fr(a) + 1, fr(b))].max()


def quiet(a, b):
    """the quietest 10 ms frame in [a, b] — the seam between two words that run together"""
    i, j = fr(a), max(fr(a) + 1, fr(b))
    return round((i + int(np.argmin(env[i:j]))) * 0.01, 3)


def head(s, first, lim=0.30):
    """start: if the first 30 ms carry speech, back up to the pause before it (≤ lim s) — unless that speech is the end of
    the word before, which was cut out on purpose: then the start goes forward to the seam, not back into that word"""
    if loud(s, s + 0.03) <= SPEECH:
        return s, False
    prev = [w for w in TW if w["t"] < first - 0.01]
    if prev and prev[-1]["end"] > s - 0.06:                 # «זה, | מה אני רוצה» — the edge sits on the word we dropped
        return quiet(s, first + 0.05), True
    lim = min(lim, s - prev[-1]["end"] + 0.05) if prev else lim
    for k in range(1, int(lim / 0.01) + 1):
        if env[fr(s) - k] < PAUSE:
            return round(s - k * 0.01 - 0.02, 3), True
    return s, False


def tail(e, last, lim=0.40):
    """end: if the last 30 ms carry speech, run on to the pause after it (≤ lim s) — unless that speech is the next
    word, which was cut out on purpose («אותי. | זה»): then the end comes back to the seam"""
    if loud(e - 0.03, e) <= SPEECH:
        return e, False
    nxt = [w for w in TW if w["t"] > last + 0.01]
    if nxt and nxt[0]["t"] < e + 0.06:
        return quiet(max(last + 0.08, nxt[0]["t"] - 0.15), e), True
    lim = min(lim, nxt[0]["t"] - e + 0.05) if nxt else lim
    for k in range(0, int(lim / 0.01) + 1):
        if env[fr(e) + k] < PAUSE:
            return round(e + k * 0.01 + 0.03, 3), True
    return e, False


AIR_T, AIR_H, GUARD = 0.10, 0.08, 0.05      # breath after the last word / before the first; margin from a dropped word


def snap(t, lo, hi):
    """the quietest 10 ms frame within ±30 ms of t, never outside [lo, hi]"""
    a, b = max(lo, t - 0.03), min(hi, t + 0.03)
    return round(t, 3) if b - a < 0.02 else quiet(a, b)


def breathe(s, e, first, last, lend):
    """air around the words (Alon, אלון+אייל+דולב 21.10.2026: «יש מקומות שיש בהם חיתוכים גסים מדיי» — 60 of 220 cuts
    left < 0.10 s of silence or started/ended inside a word): the end runs on ≥ AIR_T past the last word and the start
    backs up ≥ AIR_H before the first — bounded by the neighbouring transcript word (kept or dropped) minus GUARD, and only
    ever outward. The edge lands on the quietest frame nearby (the envelope never reaches PAUSE under crosstalk)."""
    nxt = [w for w in TW if w["t"] > last + 0.01]
    prv = [w for w in TW if w["end"] < first - 0.01]
    hi = nxt[0]["t"] - GUARD if nxt else e + 1.0
    lo = prv[-1]["end"] + GUARD if prv else s - 1.0
    e2 = e if e >= min(lend + AIR_T, hi) else snap(min(lend + AIR_T, hi), lend + 0.03, hi)
    s2 = s if s <= max(first - AIR_H, lo) else snap(max(first - AIR_H, lo), lo, first - 0.02)
    return min(s, s2), max(e, e2)


files = [Path(f) for f in sys.argv[2:]] or sorted(PUB.glob("r[0-9]*.json"), key=lambda p: int(p.stem[1:]))
for f in files:
    cut = json.loads(f.read_text())
    old = [dict(c) for c in cut["clips"]]
    moved, t = 0, 0.0
    for i, c in enumerate(cut["clips"]):
        s, e = c["src"], c["src"] + (c["end"] - c["at"])
        ws = [w for w in cut["words"] if w["clip"] == i]
        src = lambda w, k="at": c["src"] + w[k] - c["at"]
        s2, m1 = head(s, src(ws[0]) if ws else s)
        e2, m2 = tail(e, src(ws[-1]) if ws else e)
        if ws:
            b1, b2 = breathe(s2, e2, src(ws[0]), src(ws[-1]), src(ws[-1], "end"))
            m1, m2, s2, e2 = m1 or b1 < s2, m2 or b2 > e2, b1, b2
        if i and m1:                                        # don't re-play what the previous clip already plays
            p = cut["clips"][i - 1]
            pe = p["src"] + (p["end"] - p["at"])
            if pe > s2 and p["src"] < s2:
                s2 = max(s2, pe)
        moved += m1 + m2
        c.update({"src": round(s2, 3), "at": round(t, 3), "end": round(t + e2 - s2, 3)})
        t += e2 - s2
    for w in cut["words"]:
        o, c = old[w["clip"]], cut["clips"][w["clip"]]
        for k in ("at", "end"):
            w[k] = round(c["at"] + (o["src"] + (w[k] - o["at"]) - c["src"]), 3)
    cut["duration"] = round(t, 3)
    f.write_text(json.dumps(cut, ensure_ascii=False))
    print(f"{f.name}: {moved} edges moved · {t:.1f}s")
