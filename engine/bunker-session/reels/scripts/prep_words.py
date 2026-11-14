#!/usr/bin/env python3
"""Session transcript → words.json + speakers.json for tighten_edl / build_cut (ai-reel-remotion track ד׳).

    prep_words.py <session dir>        → <session>/רילס/remotion/work/{words,speakers}.json

words.json   [{w, t, end}] on the «מקור» clock (session transcript, with work/fixes.json applied by time)
speakers.json {segments:[{from,to,who}]} — one segment per word; who = the mic that is ≥ 6 dB louder over the word
              (mic clock = source + offsets.mic_src), else the mic the transcript window came from.
mic 1 = host (camera 1), mic 2 = guest (camera 2) — confirmed per session from the frames (אפיון.json speakers).
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np

FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
from rpaths import session_paths
S, _RM, _PUB, out = session_paths(sys.argv)
out.mkdir(parents=True, exist_ok=True)
ing = json.loads((S / "ingest.json").read_text())
off = float(ing["offsets"].get("mic_src", 0.0))
load = lambda p: np.frombuffer(subprocess.run([FF, "-v", "error", "-i", p, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], stdout=subprocess.PIPE, check=True).stdout, dtype=np.float32)
mics = [load(p) for p in ing["mics"][:2]]
db = lambda x, a, b: 10 * np.log10(np.mean(np.square(x[max(0, int(a * 16000)):max(int(a * 16000) + 1, int(b * 16000))])) + 1e-12)

W = json.loads((S / "תמלול/transcript.json").read_text())["words"]
fixes = json.loads((out / "fixes.json").read_text()) if (out / "fixes.json").exists() else []
words, segs, flips = [], [], 0
for w in W:
    t, e = w["start_s"], w["end_s"]
    text = w["text"]
    for f in fixes:  # {"at": seconds, "from": "טוכניין", "to": "תוכן"} — positional, never a global replace
        if abs(f["at"] - t) < 0.25 and f["from"] == text:
            text = f["to"]
            t, e = f.get("t", t), f.get("end", e)  # a retime: the word really sits elsewhere (a stutter cut before it)
    # an emptied word stays in the timeline (its sound is kept, tighten_edl must not cut there) — the caption skips it
    d1, d2 = db(mics[0], t + off, e + off), db(mics[1], t + off, e + off)
    who = "host" if d1 - d2 >= 6 else "guest" if d2 - d1 >= 6 else ("host" if w.get("mic") == 1 else "guest")
    if (who == "host") != (w.get("mic") == 1):
        flips += 1
    words.append({"w": text, "t": round(t, 3), "end": round(e, 3)})
    segs.append({"from": round(t, 3), "to": round(e, 3), "who": who})
(out / "words.json").write_text(json.dumps(words, ensure_ascii=False))
(out / "speakers.json").write_text(json.dumps({"segments": segs}, ensure_ascii=False))
print(f"{len(words)} words · {flips} speaker flips vs the transcript windows · mic offset {off}")
