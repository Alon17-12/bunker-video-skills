#!/usr/bin/env python3
"""A reel cut straight from source ranges — for restructuring a finished reel or cutting a new one out of it without the
EDL round (אלון+אייל+דולב 26.10.2026: «ליצור ריל חדש שמתחיל ב… וממשיך עד הסוף», «חסר הקטע שעליו מבוסס הנושא»).

    python3 build_ranges.py <session> <rid> <spec.json>
    spec: {"ranges": [[src_from, src_to], …], "text": {"<src t>": "new text"}, "drop": [src t, …]}

Words are the session transcript (work/words.json) inside each range; the speaker of each word is speakers.json, then
work/who.json overrides. "text" rewrites a caption word by its source start time (±0.05 s), "drop" hides a word from the
captions (its sound stays). Run fix_edges.py and mk_audio.py after.
"""
import json, sys
from pathlib import Path
from rpaths import session_paths

S, RM, PUB, WORK = session_paths(sys.argv[:2])
rid, spec = sys.argv[2], json.loads(Path(sys.argv[3]).read_text())
TW = json.loads((WORK / "words.json").read_text())
SP = json.loads((WORK / "speakers.json").read_text())["segments"]
OV = json.loads((WORK / "who.json").read_text()) if (WORK / "who.json").exists() else []
near = lambda d, t: next((v for k, v in d.items() if abs(float(k) - t) < 0.05), None)   # keys are the transcript's own start times
clips, words, t = [], [], 0.0
for ci, (a, b) in enumerate(spec["ranges"]):
    for i, w in enumerate(TW):
        mid = (w["t"] + w["end"]) / 2
        # a word belongs to the range by its middle — or, when Whisper starts it early, by its end (a soft «הוא» before the voice)
        if not (a - 0.02 <= mid <= b + 0.02 or (w["t"] < a < w["end"] - 0.06 and w["end"] - a > 0.5 * (w["end"] - w["t"]) - 0.1)):
            continue
        who = SP[i]["who"]
        for o in OV:
            if abs(o["at"] - w["t"]) < 0.2:
                who = o["who"]
        text = near(spec.get("text", {}), w["t"]) or w["w"]
        if any(abs(d - w["t"]) < 0.05 for d in spec.get("drop", [])):
            text = ""
            who = words[-1]["who"] if words else who   # a hidden interjection never pulls the camera to its speaker
        words.append({"text": text, "at": round(t + max(w["t"], a) - a, 3), "end": round(t + min(w["end"], b) - a, 3), "who": who, "clip": ci})
    clips.append({"at": round(t, 3), "end": round(t + b - a, 3), "src": round(a, 3), "cam": 1, "who": "host"})
    t += b - a
cut = {"duration": round(t, 3), "clips": clips, "words": words}
(PUB / f"{rid}.json").write_text(json.dumps(cut, ensure_ascii=False))
print(f"{rid}: {len(clips)} clips · {len(words)} words · {t:.1f}s")
