#!/usr/bin/env python3
"""Fix single words of the episode transcript at a TIME, not by text — "אם" is right in one sentence and wrong in the next.

    apply_corrections.py work/words.json work/corrections.json      # corrections: [{"t": 3182.39, "from": "אם", "to": "עם"}]

Each correction finds the word whose text is `from` and whose start is within 0.2 s of `t`, and rewrites it. The first run
keeps the untouched transcript as words.orig.json; every run starts from that file, so corrections can be edited and
re-applied. Rebuild the cuts (build_cut.py) afterwards. Global, every-occurrence fixes stay in the FIX map of edit.tsx.
"""
import json
import shutil
import sys
from pathlib import Path

words, corr = Path(sys.argv[1]), Path(sys.argv[2])
orig = words.with_name(words.stem + ".orig.json")
if not orig.exists():
    shutil.copy(words, orig)
W = json.loads(orig.read_text(encoding="utf-8"))
n = 0
for c in json.loads(corr.read_text(encoding="utf-8")):
    hit = [w for w in W if w["w"] == c["from"] and abs(w["t"] - c["t"]) < 0.2]
    if len(hit) != 1:
        print(f"!! {c['t']} '{c['from']}': {len(hit)} matches"); continue
    hit[0]["w"] = c["to"]; n += 1
words.write_text(json.dumps(W, ensure_ascii=False), encoding="utf-8")
print(f"{n} corrections applied")
