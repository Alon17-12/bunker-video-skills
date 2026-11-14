#!/usr/bin/env python3
"""Second decode for caption QA — turbo, beam 8, no conditioning, 30 s windows, one reel at a time, saved after each
(the full large-v3 decode ran ~9x real time under load and lost everything when stopped; reels.md 20.10.2026).

    $PY qa_turbo.py <session> [<session> …]     → each <session>/רילס/remotion/work/qa_turbo.json {rN: [{w,t,end}]} + a diff print
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel

MODEL = Path.home() / "bunker-video-engine/models/ivrit-whisper-large-v3-turbo-ct2"
SR = 16000
m = WhisperModel(str(MODEL), device="cpu", compute_type="int8", cpu_threads=6)
for s in sys.argv[1:]:
    S = Path(s); work = S / "רילס/remotion/work"; out = work / "qa_turbo.json"
    res = json.loads(out.read_text()) if out.exists() else {}
    x = np.frombuffer(subprocess.run([str(Path.home() / "ffmpeg-bin/ffmpeg"), "-v", "error", "-i", str(work / "dialogue16k.wav"), "-ac", "1", "-ar", "16000",
                                      "-f", "f32le", "-"], stdout=subprocess.PIPE, check=True).stdout, dtype=np.float32)
    for p in sorted(json.loads((S / "רילס/רילס.json").read_text()), key=lambda p: p["n"]):
        rid = f"r{p['n']}"
        if rid in res:
            continue
        a0, b0 = p["start"] - 1.0, p["end"] + 1.0
        ws = []
        t = a0
        while t < b0:
            b = min(t + 30.0, b0)
            seg, _ = m.transcribe(x[int(t * SR):int(b * SR)], language="he", word_timestamps=True, beam_size=8,
                                  condition_on_previous_text=False, vad_filter=False)
            ws += [{"w": w.word.strip(), "t": round(t + w.start, 3), "end": round(t + w.end, 3)} for sg in seg for w in sg.words]
            t = b - 1.0 if b < b0 else b
        res[rid] = ws
        out.write_text(json.dumps(res, ensure_ascii=False))
        print(S.name[-12:], rid, len(ws), "words", flush=True)
