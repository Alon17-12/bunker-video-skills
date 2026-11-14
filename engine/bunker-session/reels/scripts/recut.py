#!/usr/bin/env python3
"""A correction round on finished reel cuts, in place, without rebuilding them (אלון+אייל+דולב 26.10.2026: «החיתוכים לא
טובים. יש מלא קפיצות מוזרות וחיתוכי קול … ויש משפטים לא נחוצים»).

Rebuilding from the EDLs would lose every hand fix since (speaker overrides, retimes), so this works on public/rN.json:
  · drops   — words [i, j] (indices in the cut's words) leave the reel; the new edges land on the quietest 10 ms in the
              pause beside them, with breath kept (≥ 0.08 s) on the side that stays
  · merges  — two neighbouring clips whose source gap is ≤ MERGE s become one clip: the pause comes back instead of a
              jump cut on screen and a seam in the voice (most «קפיצות» were 0.1–0.5 s pauses cut out of a sentence)
  · who     — speaker overrides by word index (checked on the three mics)
Clips that play straight on in the source (gap ≈ 0) are always merged. Words keep their text, speaker and hot marks.

    python3 recut.py <session> <spec.json>      spec: {"r4": {"drop": [[45, 46]], "who": {"203-207": "host"}}, …}
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from rpaths import session_paths

S, RM, PUB, WORK = session_paths(sys.argv[:2])
SPEC = json.loads(Path(sys.argv[2]).read_text())
MERGE = 0.5
MAX_PAUSE = 0.95      # …unless the pause that comes back would be longer than this (then the cut stays, with a framing change)
FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
x = np.frombuffer(subprocess.run([FF, "-v", "error", "-i", str(WORK / "dialogue16k.wav"), "-f", "f32le", "-"],
                                 stdout=subprocess.PIPE, check=True).stdout, np.float32)
HOP = 160
env = 20 * np.log10(np.sqrt((x[: len(x) // HOP * HOP].reshape(-1, HOP) ** 2).mean(1)) + 1e-9)
fr = lambda t: int(round(t / 0.01))
TW = sorted(json.loads((WORK / "words.json").read_text()), key=lambda w: w["t"])   # whole transcript, source clock


def quiet(a, b):
    i, j = fr(a), max(fr(a) + 1, fr(b))
    return round((i + int(np.argmin(env[i:j]))) * 0.01, 3)


def spoken_between(a, b):
    """a transcript word (kept or not) inside the source gap (a, b) — then the gap is not just a pause"""
    return any(w["t"] > a + 0.02 and w["end"] < b - 0.02 and w["w"].strip() for w in TW)


for rid, spec in SPEC.items():
    f = PUB / f"{rid}.json"
    cut = json.loads(f.read_text())
    words = cut["words"]
    for c_i, c in enumerate(cut["clips"]):
        c["s"], c["e"] = c["src"], c["src"] + c["end"] - c["at"]
    for w in words:
        c = cut["clips"][w["clip"]]
        w["s"], w["e"] = c["src"] + w["at"] - c["at"], c["src"] + w["end"] - c["at"]
    for k, who in (spec.get("who") or {}).items():
        a, b = map(int, k.split("-"))
        for w in words[a:b + 1]:
            w["who"] = who
    # segments = (s, e, [words]) in source time
    segs = [{"s": c["s"], "e": c["e"], "w": [w for w in words if w["clip"] == i]} for i, c in enumerate(cut["clips"])]
    dropped = set()
    for a, b in spec.get("drop", []):
        dropped |= set(range(a, b + 1))
    out = []
    for g in segs:
        cur = None
        for w in g["w"]:
            i = words.index(w)
            if i in dropped:
                if cur is not None:   # close the running piece in the pause after its last word
                    last = cur["w"][-1]
                    cur["e"] = min(cur["e"], max(last["e"] + 0.08, quiet(last["e"] + 0.03, max(last["e"] + 0.05, w["s"] - 0.02))))
                    out.append(cur); cur = None
                continue
            if cur is None:
                prev = [x for x in g["w"] if words.index(x) < i]
                if prev and words.index(prev[-1]) in dropped:   # open after a dropped word, in the pause before this one
                    s = min(w["s"] - 0.08, quiet(prev[-1]["e"] + 0.02, max(prev[-1]["e"] + 0.04, w["s"] - 0.03)))
                    s = max(s, prev[-1]["e"] + 0.02)
                else:
                    s = g["s"]
                cur = {"s": s, "e": g["e"], "w": []}
            cur["w"].append(w)
        if cur is not None:
            out.append(cur)
    # merge pieces that play (almost) straight on in the source
    merged = [out[0]]
    for g in out[1:]:
        p = merged[-1]
        gap = g["s"] - p["e"]
        pause = (g["w"][0]["s"] if g["w"] else g["s"]) - (p["w"][-1]["e"] if p["w"] else p["e"])
        if -0.05 <= gap <= MERGE and pause <= MAX_PAUSE and not spoken_between(p["e"], g["s"]):
            p["e"] = max(p["e"], g["e"]); p["w"] += g["w"]
        else:
            merged.append(g)
    # back to the reel clock
    clips, nw, t = [], [], 0.0
    for ci, g in enumerate(merged):
        d = g["e"] - g["s"]
        old = cut["clips"][g["w"][0]["clip"]] if g["w"] else cut["clips"][0]
        clips.append({**{k: v for k, v in old.items() if k not in ("s", "e")}, "at": round(t, 3), "end": round(t + d, 3), "src": round(g["s"], 3)})
        for w in g["w"]:
            q = {k: v for k, v in w.items() if k not in ("s", "e")}
            q.update({"at": round(t + w["s"] - g["s"], 3), "end": round(t + w["e"] - g["s"], 3), "clip": ci})
            nw.append(q)
        t += d
    print(f"{rid}: {len(cut['clips'])} → {len(clips)} clips · {len(words)} → {len(nw)} words · {cut['duration']:.1f} → {t:.1f}s")
    cut.update({"clips": clips, "words": nw, "duration": round(t, 3)})
    f.write_text(json.dumps(cut, ensure_ascii=False))
