#!/usr/bin/env python3
"""Second decode of the reel windows with the full ivrit-ai large-v3 model (the session transcript is turbo).

    $PY qa_transcribe.py <session> 157-206 346-436 440-525 580-642    (reads work/dialogue16k.wav, writes work/qa.json)

Writes [{range, words:[{w,t,end}]}] on the «מקור» clock — read it next to the turbo words to fix captions by meaning.
"""
import json, sys
from pathlib import Path
from faster_whisper import WhisperModel
import numpy as np, subprocess

MODEL = Path.home() / "bunker-video-engine/models/ivrit-whisper-large-v3-ct2"
from rpaths import session_paths
S, RM, PUB, WORK = session_paths(sys.argv)
audio, out, ranges = str(WORK / "dialogue16k.wav"), str(WORK / "qa.json"), sys.argv[2:]
sr = 16000
x = np.frombuffer(subprocess.run([str(Path.home() / "ffmpeg-bin/ffmpeg"), "-v", "error", "-i", audio, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], stdout=subprocess.PIPE, check=True).stdout, dtype=np.float32)
m = WhisperModel(str(MODEL), device="cpu", compute_type="int8", cpu_threads=8)
res = []
for r in ranges:
    a, b = map(float, r.split("-"))
    seg, _ = m.transcribe(x[int(a * sr):int(b * sr)], language="he", word_timestamps=True, beam_size=5, vad_filter=False)
    ws = [{"w": w.word.strip(), "t": round(a + w.start, 3), "end": round(a + w.end, 3)} for s in seg for w in s.words]
    res.append({"range": [a, b], "words": ws})
    print(r, " ".join(w["w"] for w in ws), flush=True)
Path(out).write_text(json.dumps(res, ensure_ascii=False, indent=0))
