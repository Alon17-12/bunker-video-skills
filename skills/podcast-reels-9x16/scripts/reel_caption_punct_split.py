# -*- coding: utf-8 -*-
"""Split every caption card after a sentence mark inside it (Alon, 0923 round 3: «אחרי סימני ניקוד כמו . ? ! תמיד
לפצל כתוביות»). The mark stays on the card that ends the sentence (`?` `!` kept, a trailing `.` dropped — house
style); durations split in proportion to the characters, every piece ≥ --min s.

    python reel_caption_punct_split.py "<project>" [--min 0.30] [--write]
"""
import argparse, copy, json, os, re, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--min", type=float, default=0.30); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]; FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR); nid = lambda: str(uuid.uuid4()).upper()
tm = {m["id"]: m for m in mats["texts"]}; cap = max((t for t in d["tracks"] if t["type"] == "text"), key=lambda t: len(t["segments"])); out = []; n = 0
ri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
for s in sorted(cap["segments"], key=lambda s: s["target_timerange"]["start"]):
    m = tm[s["material_id"]]; text = json.loads(m["content"])["text"]
    parts = [p.strip() for p in re.split(r"(?<=[.?!])\s+", text) if p.strip()]
    if len(parts) < 2: out.append(s); continue
    t0 = s["target_timerange"]["start"]; L = s["target_timerange"]["duration"]; tot = sum(len(p) for p in parts)
    if L / US < A.min * len(parts): out.append(s); print(f"  · {t0/US:.2f} too short to split: {text}"); continue
    cur = t0
    for i, p in enumerate(parts):
        dur = snap(L * len(p) / tot) if i < len(parts) - 1 else t0 + L - cur; txt = p[:-1] if p.endswith(".") else p
        if i == 0: seg = s; capcut._set_text(m, txt, None)
        else:
            m2 = copy.deepcopy(m); m2["id"] = nid(); capcut._set_text(m2, txt, None); mats["texts"].append(m2); seg = copy.deepcopy(s); ri += 1; seg.update({"id": nid(), "material_id": m2["id"], "render_index": ri})
        seg["target_timerange"] = {"start": int(cur), "duration": int(dur)}; out.append(seg); cur += dur
    n += 1; print(f"  split {t0/US:7.2f}: {text!r} → {parts}")
cap["segments"] = sorted(out, key=lambda s: s["target_timerange"]["start"]); print(f"split {n} cards → {len(cap['segments'])} captions")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
