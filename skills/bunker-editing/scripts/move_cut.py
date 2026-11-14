#!/usr/bin/env python3
"""Move one cut earlier/later without changing anything after it (25.10.2026: the cut after «בונקר אקספרס AI» joined two takes
inside the word «אולפן» — «או-» from the first take, «-לפן» from the retake). Every media segment that ends at T gets shorter
by D and every one that starts at T starts D earlier on the timeline AND in its source (it plays D more of its lead-in), so the
total length and every later clip stay where they are. Captions are not touched.

    move_cut.py "<project>" T D [--write]          T = the cut (s, ±50 ms), D = seconds to move it earlier (negative = later)
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402

name, T, D = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
P = capcut.DRAFTS_DIR / name; d = json.loads(capcut._draft_file(P).read_text())
B = int(T * 1e6); SH = int(round(round(D * 30) * 1e6 / 30))
for t in d["tracks"]:
    if t["type"] not in ("video", "audio"):
        continue
    for s in t["segments"]:
        a = s["target_timerange"]["start"]; e = a + s["target_timerange"]["duration"]
        if abs(e - B) <= 50_000 and a < B - SH:
            s["target_timerange"]["duration"] -= SH; s["source_timerange"]["duration"] -= SH
            print("shorter", t.get("name") or "", a / 1e6, e / 1e6, "→", (e - SH) / 1e6)
        elif abs(a - B) <= 50_000:
            s["target_timerange"] = {"start": a - SH, "duration": e - a + SH}
            s["source_timerange"]["start"] -= SH; s["source_timerange"]["duration"] = e - a + SH
            assert s["source_timerange"]["start"] >= 0
            for k in s.get("common_keyframes", []):           # keyframes are on the source clock: unchanged
                pass
            print("earlier", t.get("name") or "", a / 1e6, "→", (a - SH) / 1e6, "src", s["source_timerange"]["start"] / 1e6)
if "--write" in sys.argv:
    if capcut.capcut_running():
        raise SystemExit("⛔ CapCut פתוח")
    capcut._backup(P); capcut._atomic_write(P, d); print("✓ נכתב")
