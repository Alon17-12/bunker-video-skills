#!/usr/bin/env python3
"""Word-level Hebrew transcript of a full episode, windowed and checkpointed (survives a session teardown).

    ~/bunker-video-engine/.venv/bin/python transcribe_episode.py <audio.wav> <words.json> [--window 600]

Uses the caption studio's ivrit-ai large-v3-turbo (CTranslate2 int8). After every window the full words-so-far are
written atomically to <words.json> ([{"w", "t", "end"}], seconds in the episode clock) and progress to <words.json>.progress.
Re-running resumes after the last finished window. Launch it detached for an hour-long episode:
    nohup <venv>/bin/python transcribe_episode.py mix.wav words.json > tr.log 2>&1 & disown
Then run the QA layer from hakapitan-captions (second decode + reading for meaning) on the moments you will use.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

STUDIO = Path.home() / "bunker-video-engine"
MODEL = STUDIO / "models" / "ivrit-whisper-large-v3-turbo-ct2"
FFMPEG = str(Path.home() / "ffmpeg-bin" / "ffmpeg")
SR = 16000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("out")
    ap.add_argument("--window", type=float, default=600)
    a = ap.parse_args()
    out = Path(a.out)
    prog = out.with_suffix(".progress")
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", a.audio, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], stdout=subprocess.PIPE, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32)
    dur = len(audio) / SR
    words = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
    start = json.loads(prog.read_text())["done_until"] if prog.exists() else 0.0
    model = WhisperModel(str(MODEL), device="cpu", compute_type="int8")
    t0 = start
    while t0 < dur - 0.5:
        t1 = min(dur, t0 + a.window)
        # cut at the quietest 0.5 s within the last 20 s of the window, so no word is split
        if t1 < dur:
            seg = audio[int((t1 - 20) * SR): int(t1 * SR)]
            hop = SR // 2
            e = [float(np.mean(seg[i:i + hop] ** 2)) for i in range(0, len(seg) - hop, hop)]
            t1 = t1 - 20 + (int(np.argmin(e)) * hop + hop / 2) / SR
        chunk = audio[int(t0 * SR): int(t1 * SR)]
        segments, _ = model.transcribe(chunk, language="he", word_timestamps=True, vad_filter=True, beam_size=5, condition_on_previous_text=False)
        for s in segments:
            for w in s.words or []:
                if w.word.strip():
                    words.append({"w": w.word.strip(), "t": round(t0 + w.start, 2), "end": round(t0 + w.end, 2)})
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
        tmp.replace(out)
        prog.write_text(json.dumps({"done_until": round(t1, 2), "duration": round(dur, 2), "words": len(words)}))
        print(f"{t1 / 60:.1f}/{dur / 60:.1f} min · {len(words)} words", flush=True)
        t0 = t1
    print("TRANSCRIPT_DONE", flush=True)


if __name__ == "__main__":
    main()
