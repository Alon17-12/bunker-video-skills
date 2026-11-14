#!/usr/bin/env python3
"""Edit decision list → the teaser/reel timeline Remotion plays.

    build_cut.py <edl.json> <words.json> <speakers.json> <out.json> [--pad 0.06] [--gap 0.0]

edl.json: {"clips": [{"from": 633.96, "to": 640.12, "beat": "hook", "cam"?: 1|2}], "cams": {"host": 1, "guest": 2}}
  times are seconds in the EPISODE clock (cameras and mix are in sync — see sync_cams.py). Clips play in order,
  back to back; a clip cut on word boundaries gets --pad seconds of air on each side so no consonant is clipped.
The camera of a clip is the speaker who owns most of its words (speakers.py), unless the clip says "cam".
Output: {"duration", "clips": [{at, end, src, cam, who, beat}], "words": [{text, at, end, who, clip}]} — words already
in TEASER time, so captions and effects are cued from them (cue by text, never by hand-typed seconds).
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("words")
    ap.add_argument("speakers")
    ap.add_argument("out")
    ap.add_argument("--pad", type=float, default=0.06)
    ap.add_argument("--audio", help="episode mix: snap every cut to the quietest 10 ms near the word boundary (no clipped consonants)")
    a = ap.parse_args()
    edl = json.loads(Path(a.edl).read_text(encoding="utf-8"))
    W = json.loads(Path(a.words).read_text(encoding="utf-8"))
    S = json.loads(Path(a.speakers).read_text(encoding="utf-8"))["segments"]
    cams = edl.get("cams", {"host": 1, "guest": 2})

    def who(t):
        for s in S:
            if s["from"] <= t < s["to"]:
                return s["who"]
        return "silence"

    snap = lambda x, lo, hi: x
    if a.audio:
        import subprocess
        import numpy as np
        raw = subprocess.run([str(Path.home() / "ffmpeg-bin/ffmpeg"), "-v", "error", "-i", a.audio, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], stdout=subprocess.PIPE, check=True).stdout
        x = np.frombuffer(raw, dtype=np.float32)
        hop = 160  # 10 ms
        e = np.square(x[: len(x) // hop * hop].reshape(-1, hop)).mean(axis=1)
        def snap(t0, lo, hi):
            i0, i1 = max(0, int((t0 + lo) * 100)), min(len(e) - 1, int((t0 + hi) * 100))
            return (i0 + int(np.argmin(e[i0:i1 + 1]))) / 100.0 if i1 > i0 else t0

    t = 0.0
    clips, words = [], []
    for i, c in enumerate(edl["clips"]):
        # cut in the quietest spot just before the first word / just after the last one — but NEVER inside the
        # neighbouring word: the EDL "to" usually sits on the next word's start, and a +0.12 s snap played its first
        # syllable ("…ברור, יש", "סגרנו, ואז" + "ואז אני"). Alon, 11.10.2026: "יש מקומות שהמשפט נחתך".
        nxt = next((w["t"] for w in W if w["t"] >= c["to"] - 0.01), 1e9)
        prv = max((w.get("end", w["t"] + 0.2) for w in W if w.get("end", w["t"] + 0.2) <= c["from"] + 0.01), default=-1e9)
        hi = min(0.12 if a.audio else a.pad, nxt - 0.015 - c["to"])
        lo = max(-0.09 if a.audio else -a.pad, prv + 0.015 - c["from"])
        a0 = snap(c["from"], lo, min(0.01, max(lo, 0.01))) if a.audio else c["from"] + lo
        b0 = snap(c["to"], min(-0.01, hi), hi) if a.audio else c["to"] + max(hi, 0)
        ws = [w for w in W if c["from"] - 0.01 <= w["t"] < c["to"] - 0.01]
        owners = [who((w["t"] + w.get("end", w["t"] + 0.2)) / 2) for w in ws]
        tally = {k: owners.count(k) for k in ("host", "guest")}
        speaker = c.get("who") or max(tally, key=tally.get)
        cam = c.get("cam") or cams.get(speaker, 1)
        clips.append({"at": round(t, 3), "end": round(t + b0 - a0, 3), "src": round(a0, 3), "cam": cam, "who": speaker, "beat": c.get("beat", "")})
        for w, o in zip(ws, owners):
            words.append({"text": w["w"], "at": round(t + w["t"] - a0, 3), "end": round(t + w.get("end", w["t"] + 0.3) - a0, 3),
                          "who": o if o in ("host", "guest") else speaker, "clip": i})
        t += b0 - a0
    Path(a.out).write_text(json.dumps({"duration": round(t, 3), "clips": clips, "words": words}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(clips)} clips · {t:.1f}s · {len(words)} words")
    for c in clips:
        print(f"  {c['at']:6.2f}–{c['end']:6.2f}  cam{c['cam']} {c['who']:5}  {c['beat']}")


if __name__ == "__main__":
    main()
