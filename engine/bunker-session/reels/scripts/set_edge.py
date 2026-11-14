#!/usr/bin/env python3
"""Set one clip's source edge by hand (after fix_edges, which looks for a pause that a running voice may not have) and move
everything after it — for the cuts Alon names («המילה ״הזה״ … נחתכת»). Checked by decoding the window first.
Rebuilds the reel's own sound (mk_audio.py → public/a/<rN>.wav) at the end: the render plays that file, so a moved edge with
the old wav drifts the picture off the voice from the cut on (יירום v5, 29.10.2026: «הסאונד והמצלמה לא מדוייקים לאורך כל הסרטון»).

    python3 set_edge.py <session> <rN> <clip src start> [--end <src>] [--start <src>]
"""
import json, subprocess, sys
from pathlib import Path
from rpaths import session_paths
S, RM, PUB, WORK = session_paths(sys.argv[:2])
rid, key = sys.argv[2], float(sys.argv[3])
args = dict(zip(sys.argv[4::2], map(float, sys.argv[5::2])))
f = PUB / f"{rid}.json"
cut = json.loads(f.read_text())
ci = min(range(len(cut["clips"])), key=lambda i: abs(cut["clips"][i]["src"] - key))
c = cut["clips"][ci]
s0, e0 = c["src"], c["src"] + c["end"] - c["at"]
s1, e1 = args.get("--start", s0), args.get("--end", e0)
dh, dt = s0 - s1, e1 - e0          # more head / more tail, in seconds
for w in cut["words"]:
    if w["clip"] == ci:
        w["at"] = round(w["at"] + dh, 3); w["end"] = round(w["end"] + dh, 3)
    elif w["clip"] > ci:
        w["at"] = round(w["at"] + dh + dt, 3); w["end"] = round(w["end"] + dh + dt, 3)
c.update({"src": round(s1, 3), "end": round(c["end"] + dh + dt, 3)})
for x in cut["clips"][ci + 1:]:
    x["at"] = round(x["at"] + dh + dt, 3); x["end"] = round(x["end"] + dh + dt, 3)
cut["duration"] = round(cut["duration"] + dh + dt, 3)
f.write_text(json.dumps(cut, ensure_ascii=False))
print(f"{rid} clip {ci}: [{s0:.2f},{e0:.2f}] → [{s1:.2f},{e1:.2f}] · {cut['duration']:.2f}s")
subprocess.run([sys.executable, str(Path(__file__).with_name("mk_audio.py")), sys.argv[1], rid], check=True)
