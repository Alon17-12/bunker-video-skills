# -*- coding: utf-8 -*-
"""Full, accurate transcript of an EDITED CapCut project → external SRT.

Reads the project's own edited timeline (so cue times match the cut as it is
now), transcribes in fixed windows, and after EVERY window rewrites the whole
SRT-so-far to the Desktop atomically. Durable: a crash or session teardown
leaves everything transcribed so far on disk. Injects NOTHING.

Run it DETACHED so it survives the Claude session ending:
    cd ~/bunker-video-engine
    nohup .venv/bin/python full_transcript_srt.py "DRAFT NAME" \\
        > ~/Desktop/.transcribe.log 2>&1 & disown

Usage: full_transcript_srt.py "<draft name or unique substring>" [out.srt]
"""
import os
import sys, json, time, math
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut, transcribe as stt, ai, brain, server
from pathlib import Path

DRAFT = sys.argv[1]
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else \
    Path.home() / "Desktop" / f"{DRAFT} - תמלול מלא.srt"
PROG = OUT.with_name("." + OUT.stem + ".progress.json")
WINDOW_S = 600       # 10-minute durable checkpoints
MAX_WORDS = 7        # readable transcript lines; use 3 for reel-style captions
MAX_DUR = 4.5


def srt_time(us: int) -> str:
    ms = max(us, 0) // 1000
    return (f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:"
            f"{ms % 60000 // 1000:02d},{ms % 1000:03d}")


def write_srt(caps):
    caps = sorted(caps, key=lambda c: c["start_us"])
    blocks = [f"{i + 1}\n{srt_time(c['start_us'])} --> "
              f"{srt_time(c['start_us'] + c['duration_us'])}\n{c['text']}"
              for i, c in enumerate(caps)]
    tmp = OUT.with_suffix(".srt.tmp")
    tmp.write_text("\n\n".join(blocks) + "\n", encoding="utf-8-sig")
    tmp.replace(OUT)          # atomic — never a half-written file on the Desktop


def prog(**kw):
    kw["time"] = int(time.time())
    PROG.write_text(json.dumps(kw, ensure_ascii=False))


cfg = server._config()
# resolve the draft (exact, else unique substring)
names = [d["name"] for d in capcut.list_drafts()]
match = next((n for n in names if n == DRAFT), None) or \
    next((n for n in names if DRAFT in n), None)
if not match:
    raise SystemExit(f"draft not found: {DRAFT!r}")
DRAFT = match

draft = capcut.load_draft(DRAFT)
END_US = draft["duration"]
plan = capcut.audio_plan(draft, DRAFT)
prog(stage="building_audio", duration_min=round(END_US / 1e6 / 60, 1))

audio, warns = stt.build_timeline_audio(plan, END_US)
stt.ensure_model()

sr = stt.SAMPLE_RATE
n_win = max(1, math.ceil(len(audio) / sr / WINDOW_S))
prog(stage="transcribing", windows=n_win, done=0)

all_words = []
for wi in range(n_win):
    a = int(wi * WINDOW_S * sr)
    b = min(int((wi + 1) * WINDOW_S * sr), len(audio))
    piece = audio[a:b]
    if len(piece) and (piece ** 2).sum():
        words = stt.transcribe(piece)
        off = wi * WINDOW_S
        for w in words:
            w["start_s"] += off
            w["end_s"] += off
        all_words.extend(words)
    caps = stt.chunk_captions(all_words, max_words=MAX_WORDS, max_duration_s=MAX_DUR)
    write_srt(caps)
    prog(stage="transcribing", windows=n_win, done=wi + 1,
         cues=len(caps), covered_s=round(b / sr))

caps = stt.chunk_captions(all_words, max_words=MAX_WORDS, max_duration_s=MAX_DUR)
glossary = cfg.get("glossary", [])
if glossary and brain.backend() != "none":
    prog(stage="glossary", cues=len(caps))
    try:
        ai.fix_transcript(caps, glossary)   # fixes brand names in place
        write_srt(caps)
    except Exception as e:
        prog(stage="glossary_skipped", error=str(e)[:120])

write_srt(caps)
end = (max(c["start_us"] + c["duration_us"] for c in caps) / 1e6) if caps else 0
prog(stage="DONE", cues=len(caps), end_min=round(end / 60, 1), file=str(OUT))
print("DONE", len(caps), "cues ->", OUT)
