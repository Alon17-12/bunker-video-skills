# -*- coding: utf-8 -*-
"""Keyword highlight inside the captions (ניסטור's yellow keyword, our accent): whole-word matches of the
given phrases get the accent colour as a per-range style; everything else stays white. Cards that sit under
an active super are left alone (one device per moment).

    python reel_caption_highlights.py "<project>" --phrases "עוגנים,קהל ברור,תיאום ציפיות" [--accent d01020] [--supers supers] [--write]

Idempotent: every card is rebuilt from its first style, so re-running with a new list replaces the old one.
"""
import argparse, copy, json, os, re, sys
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--phrases", default=""); ap.add_argument("--accent", default="d01020"); ap.add_argument("--supers", default="supers"); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]
ACC = [int(A.accent[i:i+2], 16) / 255 for i in (0, 2, 4)]; WHITE = [1.0, 1.0, 1.0]
phrases = [p.strip() for p in A.phrases.split(",") if p.strip()]   # empty = clear every highlight (Alon 23.09: «השינוי של הצבע באותו מבנה כתוביות סתם נראה מציק בעין»)
tm = {m["id"]: m for m in mats["texts"]}; cap = max((t for t in d["tracks"] if t["type"] == "text"), key=lambda t: len(t["segments"]))
sup = [(s["target_timerange"]["start"], s["target_timerange"]["start"] + s["target_timerange"]["duration"]) for t in d["tracks"] if t.get("name") == A.supers for s in t["segments"]]
n = 0; hits = []
for s in cap["segments"]:
    m = tm[s["material_id"]]; a = s["target_timerange"]["start"]; b = a + s["target_timerange"]["duration"]
    under = any(x < b and a < y for x, y in sup)
    for field in ("content", "base_content"):
        if not m.get(field): continue
        c = json.loads(m[field]); text = c["text"]; base = copy.deepcopy(c["styles"][0]); base["fill"]["content"]["solid"]["color"] = WHITE
        ranges = []
        if not under:
            for p in phrases:
                for mm in re.finditer(r"(?<!\S)" + re.escape(p) + r"(?!\S)", text): ranges.append((mm.start(), mm.end()))
        cuts = sorted({0, len(text)} | {x for r in ranges for x in r}); st = []
        for r0, r1 in zip(cuts, cuts[1:]):
            x = copy.deepcopy(base); x["range"] = [r0, r1]; x["fill"]["content"]["solid"]["color"] = ACC if any(p0 <= r0 < p1 for p0, p1 in ranges) else WHITE; st.append(x)
        c["styles"] = st; m[field] = json.dumps(c, ensure_ascii=False)
        if field == "content" and ranges: n += 1; hits.append(f"{a/US:.1f} {text}")
print(f"highlighted {n} cards:"); [print("  ", h) for h in hits]
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
