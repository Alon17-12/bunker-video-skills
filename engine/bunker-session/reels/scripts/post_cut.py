#!/usr/bin/env python3
"""After build_cut: speaker overrides by SOURCE time (work/who.json: [{"at": 169.22, "who": "guest"}]) — the mic lead
can lose a word to cross-talk; the override is checked by eye on the frames, then the routing follows it."""
import json, sys
from pathlib import Path
from rpaths import session_paths
S, RM, PUB, WORK = session_paths(sys.argv)
ov = json.loads((WORK / "who.json").read_text()) if (WORK / "who.json").exists() else []
for f in sys.argv[2:] or sorted(str(p) for p in PUB.glob("r*.json")):
    cut = json.loads(Path(f).read_text())
    n = 0
    for w in cut["words"]:
        c = cut["clips"][w["clip"]]
        src = c["src"] + (w["at"] - c["at"])
        for o in ov:
            if abs(o["at"] - src) < 0.2 and w["who"] != o["who"]:
                w["who"] = o["who"]; n += 1
    Path(f).write_text(json.dumps(cut, ensure_ascii=False))
    print(f"{f}: {cut['duration']:.1f}s · {len(cut['clips'])} clips · {len(cut['words'])} words · {n} speaker overrides")
