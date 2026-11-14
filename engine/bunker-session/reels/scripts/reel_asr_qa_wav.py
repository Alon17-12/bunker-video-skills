#!/usr/bin/env python3
"""Second decode of the RENDERED reel vs its caption words (tsomet-20 "caption_qa_tiebreak --audio"): every insert or
delete near a cut is a clipped word or a leftover syllable.   reel_asr_qa.py <session> v2 [r1,r2,…]   (renders in <session>/רילס/remotion/out)"""
import difflib, json, subprocess, sys
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel
FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
m = WhisperModel(str(Path.home() / "bunker-video-engine/models/ivrit-whisper-large-v3-turbo-ct2"), device="cpu", compute_type="int8")
bare = lambda s: "".join(ch for ch in s if ch.isalnum())
from rpaths import session_paths
S, RM, PUB, WORK = session_paths(sys.argv)
ver = sys.argv[2] if len(sys.argv) > 2 else "v1"
ids = sys.argv[3].split(",") if len(sys.argv) > 3 else sorted(p.stem for p in PUB.glob("r[0-9]*.json"))
for vid, cj in ((str(PUB / "a" / f"{i}.wav"), str(PUB / f"{i}.json")) for i in ids):
    cut = json.loads(Path(cj).read_text())
    x = np.frombuffer(subprocess.run([FF, "-v", "error", "-i", vid, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], stdout=subprocess.PIPE, check=True).stdout, dtype=np.float32)
    seg, _ = m.transcribe(x, language="he", word_timestamps=True, beam_size=5)
    heard = [(w.word.strip(), w.start) for s in seg for w in s.words]
    ref = [(w["text"], w["at"]) for w in cut["words"] if w["text"]]
    cuts = [c["at"] for c in cut["clips"]]
    sm = difflib.SequenceMatcher(a=[bare(a) for a, _ in ref], b=[bare(b) for b, _ in heard], autojunk=False)
    print(f"\n## {vid}: {len(ref)} caption words · {len(heard)} heard · match {sm.ratio():.2f}")
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        t = ref[i1][1] if i1 < len(ref) else heard[j1][1]
        near = min((abs(t - c) for c in cuts), default=9)
        print(f"  {op:7s} @{t:6.2f}{' ⚠ cut' if near < 0.6 else ''}  captions: {' '.join(a for a, _ in ref[i1:i2]) or '—'}  |  heard: {' '.join(b for b, _ in heard[j1:j2]) or '—'}")
