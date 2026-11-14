#!/usr/bin/env python3
"""Replace a word inside the captions of a CapCut project, keeping every colour range right (ranges are character
offsets — a shorter word shifts all the ranges after it).   caption_replace.py "<project>" "<old>" "<new>" [--write]"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402
proj, old, new = sys.argv[1:4]; write = "--write" in sys.argv
P = capcut.DRAFTS_DIR / proj; d = json.loads(capcut._draft_file(P).read_text()); n = 0
for m in d["materials"].get("texts", []):
    c = json.loads(m["content"]); t = c["text"]; i = t.find(old)
    while i >= 0:
        dl = len(new) - len(old)
        t = t[:i] + new + t[i + len(old):]
        for st in c.get("styles", []):
            a, b = st["range"]
            if a >= i + len(old): a += dl
            if b >= i + len(old): b += dl
            elif b > i: b = max(a, b + dl)
            st["range"] = [a, b]
        n += 1; i = t.find(old, i + len(new))
    c["text"] = t; m["content"] = json.dumps(c, ensure_ascii=False)
    if "words" in m and isinstance(m["words"], dict): pass
print(proj, "replaced", n)
if write and n:
    if capcut.capcut_running(): raise SystemExit("⛔ CapCut פתוח")
    capcut._backup(P); capcut._atomic_write(P, d)
