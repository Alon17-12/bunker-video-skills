#!/usr/bin/env python3
"""Local Whisper transcript for videos with no platform captions (Instagram).

Runs on the caption studio's venv and its ivrit.ai Whisper (Hebrew-tuned,
large-v3-turbo, CTranslate2 int8) — the same engine HaKapitan uses for the
podcast captions. Writes the same transcript.json shape transcript.py does, so
run.py and the rubric need no special case; `source` says it came from Whisper.

usage: transcribe_local.py <dir>
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

STUDIO = Path.home() / "bunker-video-engine"
VENV_PY = STUDIO / ".venv" / "bin" / "python"
MODEL = STUDIO / "models" / "ivrit-whisper-large-v3-turbo-ct2"
FFMPEG = Path.home() / "ffmpeg-bin" / "ffmpeg"
PAUSE_S, HOOK_S = 0.8, 3.0

WORKER = r'''
import json, sys, numpy as np, subprocess
from faster_whisper import WhisperModel
video, model_dir, ffmpeg = sys.argv[1:4]
raw = subprocess.run([ffmpeg, "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                     stdout=subprocess.PIPE, check=True).stdout
audio = np.frombuffer(raw, dtype=np.float32)
model = WhisperModel(model_dir, device="cpu", compute_type="int8")
segments, info = model.transcribe(audio, language=None, word_timestamps=True, vad_filter=True, beam_size=5)
words = []
for seg in segments:
    for w in seg.words or []:
        words.append({"t": round(w.start, 2), "w": w.word.strip()})
print(json.dumps({"lang": info.language, "words": words}, ensure_ascii=False))
'''


def _segments(words, span=5.0):
    segs, cur = [], []
    for i, word in enumerate(words):
        gap = word["t"] - words[i - 1]["t"] if i else 0.0
        if cur and (gap >= PAUSE_S or word["t"] - cur[0]["t"] >= span):
            segs.append(cur); cur = []
        cur.append(word)
    if cur:
        segs.append(cur)
    return [{"start": s[0]["t"], "end": s[-1]["t"], "text": " ".join(w["w"] for w in s)} for s in segs]


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    directory = Path(sys.argv[1])
    evidence = directory / "evidence"
    evidence.mkdir(exist_ok=True)
    if not VENV_PY.exists() or not MODEL.exists():
        raise SystemExit(f"studio venv or model missing: {VENV_PY} / {MODEL}")

    result = subprocess.run([str(VENV_PY), "-c", WORKER, str(directory / "source.mp4"), str(MODEL), str(FFMPEG)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise SystemExit("whisper failed: " + result.stderr.strip().splitlines()[-1][:200])
    data = json.loads(result.stdout.strip().splitlines()[-1])
    words = [w for w in data["words"] if w["w"]]
    if not words:
        payload = {"available": False, "note": "whisper found no speech"}
    else:
        spoken = words[-1]["t"] - words[0]["t"]
        pauses = [{"at_s": words[i - 1]["t"], "gap_s": round(words[i]["t"] - words[i - 1]["t"], 2)}
                  for i in range(1, len(words)) if words[i]["t"] - words[i - 1]["t"] >= PAUSE_S]
        segments = _segments(words)
        payload = {
            "available": True, "lang": data["lang"], "source": "whisper ivrit-large-v3-turbo (local)",
            "word_count": len(words), "first_word_s": words[0]["t"], "last_word_s": words[-1]["t"],
            "wpm": round(len(words) / spoken * 60, 1) if spoken > 0 else None,
            "pauses_over_0_8s": len(pauses),
            "longest_pause": max(pauses, key=lambda p: p["gap_s"]) if pauses else None,
            "hook_3s_text": " ".join(w["w"] for w in words if w["t"] < HOOK_S),
            "hook_10s_text": " ".join(w["w"] for w in words if w["t"] < 10.0),
            "segments": segments, "words": words,
        }
        lines = [f"# transcript ({data['lang']}, whisper) — {len(words)} words, {payload['wpm']} wpm", ""]
        for seg in segments:
            m, s = divmod(seg["start"], 60)
            lines.append(f"[{int(m):02d}:{s:05.2f}] {seg['text']}")
        (directory / "transcript.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (evidence / "transcript.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: payload.get(k) for k in ("available", "lang", "word_count", "wpm", "pauses_over_0_8s", "hook_3s_text")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
