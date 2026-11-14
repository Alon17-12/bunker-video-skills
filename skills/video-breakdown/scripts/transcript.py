#!/usr/bin/env python3
"""Turn platform captions into a clean, timed transcript with speech metrics.

YouTube's auto-captions come as a rolling VTT: every cue repeats the previous
line and adds new words with per-word <c> timestamps, so the raw file is three
times longer than the speech and unreadable. This keeps one copy of each word
with its time, then measures what a style book needs: speech rate, pauses, and
exactly what is said in the hook window.

Writes evidence/transcript.json and transcript.md.
usage: transcript.py <dir>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PAUSE_S = 0.8          # a gap between words long enough to be an editing beat
HOOK_S = 3.0
LANG_PRIORITY = ("he", "iw", "en")

TIME = re.compile(r"(\d+):(\d\d):(\d\d)\.(\d{3})")
WORD_TAG = re.compile(r"<(\d+:\d\d:\d\d\.\d{3})><c>\s*([^<]+?)\s*</c>")
CUE_HEADER = re.compile(r"^(\d+:\d\d:\d\d\.\d{3}) --> (\d+:\d\d:\d\d\.\d{3})")


def _seconds(stamp: str) -> float:
    h, m, s, ms = TIME.match(stamp).groups()
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _pick(directory: Path):
    files = {p.suffixes[-2].lstrip("."): p for p in directory.glob("source.*.vtt") if len(p.suffixes) >= 2}
    for lang in LANG_PRIORITY:
        if lang in files:
            return lang, files[lang]
    return (next(iter(files.items())) if files else (None, None))


def _parse(vtt: str):
    """Word-timed parse for auto-captions; cue-level fallback for manual subs."""
    words, cues = [], []
    start = end = None
    for line in vtt.splitlines():
        header = CUE_HEADER.match(line)
        if header:
            start, end = _seconds(header.group(1)), _seconds(header.group(2))
            continue
        if start is None or not line.strip() or line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        tags = WORD_TAG.findall(line)
        if tags:
            # The first word of the line carries the cue start, not a tag.
            lead = re.split(r"<", line, 1)[0].strip()
            if lead:
                words.append({"t": round(start, 2), "w": lead})
            words.extend({"t": round(_seconds(t), 2), "w": w} for t, w in tags)
        elif "<c>" not in line:
            text = re.sub(r"<[^>]+>", "", line).strip()
            if text and (not cues or cues[-1]["text"] != text):
                cues.append({"start": round(start, 2), "end": round(end, 2), "text": text})
    if not words:  # manual subtitles: spread each cue's words across its span
        for cue in cues:
            toks = cue["text"].split()
            step = (cue["end"] - cue["start"]) / max(len(toks), 1)
            words.extend({"t": round(cue["start"] + i * step, 2), "w": w} for i, w in enumerate(toks))
    return words


def _segments(words, span=5.0):
    """Readable lines: one every ~5 s, or at a pause."""
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

    lang, path = _pick(directory)
    if path is None:
        payload = {"available": False, "note": "no platform captions — transcribe from audio or use the listening pass"}
        (evidence / "transcript.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False)); return

    words = _parse(path.read_text(encoding="utf-8"))
    if not words:
        payload = {"available": False, "note": f"{path.name} parsed to zero words"}
        (evidence / "transcript.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False)); return

    spoken = words[-1]["t"] - words[0]["t"]
    pauses = [
        {"at_s": words[i - 1]["t"], "gap_s": round(words[i]["t"] - words[i - 1]["t"], 2)}
        for i in range(1, len(words)) if words[i]["t"] - words[i - 1]["t"] >= PAUSE_S
    ]
    segments = _segments(words)
    payload = {
        "available": True, "lang": lang, "source": path.name,
        "word_count": len(words),
        "first_word_s": words[0]["t"], "last_word_s": words[-1]["t"],
        "wpm": round(len(words) / spoken * 60, 1) if spoken > 0 else None,
        "pauses_over_0_8s": len(pauses),
        "longest_pause": max(pauses, key=lambda p: p["gap_s"]) if pauses else None,
        "hook_3s_text": " ".join(w["w"] for w in words if w["t"] < HOOK_S),
        "hook_10s_text": " ".join(w["w"] for w in words if w["t"] < 10.0),
        "segments": segments,
        "words": words,
    }
    (evidence / "transcript.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# transcript ({lang}) — {len(words)} words, {payload['wpm']} wpm", ""]
    for seg in segments:
        m, s = divmod(seg["start"], 60)
        lines.append(f"[{int(m):02d}:{s:05.2f}] {seg['text']}")
    (directory / "transcript.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({k: payload[k] for k in ("lang", "word_count", "wpm", "pauses_over_0_8s", "hook_3s_text")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
