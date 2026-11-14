# -*- coding: utf-8 -*-
"""Fast caption pass over ONLY the first N minutes of a CapCut project, then
inject with the default style. For "stage 1, just the opening" asks.

Builds captions first (no CapCut lock needed — reading only), then injects.
Injection needs the draft NOT open in CapCut: it polls draft_locked and waits,
so tell the user to step out to the CapCut home screen. For a FRESH draft
(0 existing captions) replace_existing=True is a clean write; if the draft
already has captions you want to keep, inject a NEW track with
replace_existing=False instead and verify the old track is untouched.

Usage: first_minutes.py "<draft name or unique substring>" [minutes]
"""
import os
import sys, time
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut, transcribe as stt, ai, brain, server

DRAFT_ARG = sys.argv[1]
MINUTES = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
WINDOW_US = int(MINUTES * 60 * 1e6)

cfg = server._config()
MAX_WORDS = cfg.get("settings", {}).get("max_words", 3)

names = [d["name"] for d in capcut.list_drafts()]
DRAFT = next((n for n in names if n == DRAFT_ARG), None) or \
    next((n for n in names if DRAFT_ARG in n), None)
if not DRAFT:
    raise SystemExit(f"draft not found: {DRAFT_ARG!r}")

draft = capcut.load_draft(DRAFT)
plan = capcut.audio_plan(draft, DRAFT)

# keep segments that start before the window; clip the straddling one
win = []
for s in plan:
    if s["target_start_us"] >= WINDOW_US:
        continue
    s = dict(s)
    end = s["target_start_us"] + s["target_duration_us"]
    if end > WINDOW_US:
        overflow = end - WINDOW_US
        s["target_duration_us"] -= overflow
        s["source_duration_us"] = int(s["target_duration_us"] * s["speed"])
    win.append(s)

audio, _warns = stt.build_timeline_audio(win, WINDOW_US)
stt.ensure_model()
words = stt.transcribe(audio)
caps = stt.chunk_captions(words, max_words=MAX_WORDS)

glossary = cfg.get("glossary", [])
if glossary and brain.backend() != "none":
    try:
        ai.fix_transcript(caps, glossary)
    except Exception as e:
        print("glossary skipped:", str(e)[:120])

style = (next((x for x in cfg["styles"] if x["id"] == cfg.get("default_style")), None)
         or (cfg["styles"][-1] if cfg.get("styles") else None))
if not style:
    raise SystemExit("no default caption style configured")

deadline = time.time() + 150
while True:
    if not capcut.draft_locked(DRAFT):
        r = capcut.inject_captions(DRAFT, caps, style["style"], replace_existing=True)
        print("INJECTED:", r)
        break
    if time.time() > deadline:
        print("STILL_LOCKED: exit the draft to the CapCut home screen, then re-run.")
        raise SystemExit(3)
    print("draft open in CapCut — waiting 10s...")
    time.sleep(10)
