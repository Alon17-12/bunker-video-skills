#!/usr/bin/env python3
"""Second-opinion transcription + word diff — the QA pass that runs BEFORE a
caption job is reported as done.

Why: one Whisper pass is one opinion. On 0830 (1) the first pass wrote
«לקוכב» (not a word — it was «לקוחה»), «משווים מטורפים» («מצבים מטורפים»),
«העולם שאימא» («שזה מה שאימא») and dropped «חד», «יום», «הבנת». A second pass
with different decoding (bigger beam, no VAD, no conditioning on the previous
window) disagrees with the first on exactly the words that are wrong, and
agrees on the ones that are right. 96–98% agreement is normal; every
disagreement is a place to read the context and decide.

Usage — from a reel_captions.py cache (the audio it transcribed + its words):
    caption_qa_tiebreak.py --cache "~/Movies/reel-captions-work/<project>_<range>"
or from files:
    caption_qa_tiebreak.py --audio timeline.npy|timeline.wav --words words.json

Prints agreement % and one line per disagreement (timeline seconds, pass-1
words, pass-2 words). It never writes to a draft. What to do with the output:

  * both passes agree but the word is odd  → it was said that way; do not touch
  * passes disagree, context decides       → fix the caption (text + style range)
  * passes disagree, context does not      → leave it, list it for a human ear
  * a non-word (final letter mid-word, «לקוכב») → the context almost always
    names the real word; the recording's subject matter is the tie-breaker
"""
import argparse, json, os, re, difflib, subprocess, sys
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import numpy as np
import transcribe, paths

ap = argparse.ArgumentParser()
ap.add_argument("--cache", help="reel_captions work key: <dir>/<key> (reads <key>-m1.npy + <key>-words.json)")
ap.add_argument("--audio", help="16 kHz mono float32 .npy, or any audio file (decoded via ffmpeg)")
ap.add_argument("--words", help="pass-1 words json: list of {text, start_s|s, ...}")
ap.add_argument("--beam", type=int, default=8)
ap.add_argument("--vad", action="store_true", help="keep VAD on (default off — the point is a different decode)")
ap.add_argument("--out", help="write pass-2 words json here")
A = ap.parse_args()

if A.cache:
    key = os.path.expanduser(A.cache)
    A.audio = A.audio or f"{key}-m1.npy"
    A.words = A.words or f"{key}-words.json"
if not (A.audio and A.words):
    ap.error("--cache or both --audio and --words")

if A.audio.endswith(".npy"):
    audio = np.load(A.audio).astype(np.float32)
else:
    raw = subprocess.run([str(paths.FFMPEG), "-v", "error", "-i", A.audio, "-ac", "1",
                          "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    audio = np.frombuffer(raw, np.float32)
print(f"audio: {len(audio)/16000:.1f}s", flush=True)

model = transcribe.load_model()
segs, _ = model.transcribe(audio, language="he", word_timestamps=True,
                           beam_size=A.beam, best_of=A.beam, vad_filter=A.vad,
                           condition_on_previous_text=False)
w2 = [{"text": w.word.strip(), "s": w.start, "e": w.end}
      for s in segs for w in (s.words or []) if w.word.strip()]
if A.out:
    json.dump(w2, open(A.out, "w"), ensure_ascii=False)

w1 = json.load(open(A.words))
if isinstance(w1, dict):                       # some caches wrap the list
    w1 = next((v for v in w1.values() if isinstance(v, list)), [])
tkey = next((k for k in ("start_s", "s", "start") if w1 and k in w1[0]), None)
norm = lambda t: re.sub(r"[^\w\"']", "", t)
a = [norm(w["text"]) for w in w1 if norm(w.get("text", ""))]
b = [norm(w["text"]) for w in w2 if norm(w["text"])]
sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
same = sum(bl.size for bl in sm.get_matching_blocks())
print(f"pass1 {len(a)} words | pass2 {len(b)} | agree {same} ({100*same/max(len(a),1):.1f}%)")
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == "equal":
        continue
    t = w1[i1][tkey] if (tkey and i1 < len(w1)) else (w2[j1]["s"] if j1 < len(w2) else 0.0)
    print(f"{t:8.2f}s {op:8} pass1={' '.join(a[i1:i2])!r:42} pass2={' '.join(b[j1:j2])!r}")
print("DONE")
