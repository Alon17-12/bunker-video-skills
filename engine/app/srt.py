# -*- coding: utf-8 -*-
"""Tiny SRT parser — the client-marking side of the auto-reels flow.

An SRT here is BOTH things at once: its first→last cue span marks WHERE the
reel lives on the edited episode, and its cues are the captions to burn on it.
Times are in the edited episode's timeline (the anchor).
"""
from __future__ import annotations

import re
from pathlib import Path

_TIME = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")


def _us(h: str, m: str, s: str, ms: str) -> int:
    return ((int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms.ljust(3, "0"))) * 1000


def parse_srt(path: Path) -> list[dict]:
    """[{start_us, end_us, text}] sorted by start; tolerant of BOM/CRLF/blank cues."""
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    cues = []
    for block in re.split(r"\r?\n\r?\n+", raw):
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue
        ti = next((i for i, l in enumerate(lines) if _TIME.search(l)), None)
        if ti is None:
            continue
        m = _TIME.search(lines[ti])
        text = " ".join(lines[ti + 1:]).strip()
        if not text:
            continue
        a, b = _us(*m.groups()[:4]), _us(*m.groups()[4:])
        if b > a:
            cues.append({"start_us": a, "end_us": b, "text": text})
    cues.sort(key=lambda c: c["start_us"])
    return cues
