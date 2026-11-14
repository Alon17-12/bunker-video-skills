# -*- coding: utf-8 -*-
"""Split caption cards that would WRAP in CapCut into two cards, at the best word boundary, times proportional
to text length. A wrapped caption is a two-line card, and with a long word CapCut breaks inside the word
(0923 r4, Alon: «ירידת שורה באמצע מילה»). Width = PIL@60(text) × size/10 × clip scale (house calibration);
the caption wrap on 9:16 at size 20 is ≈ 770 px (house number), so --max-px defaults to 740 for margin.

    python reel_caption_width_split.py "<project>" [--max-px 740] [--track כתוביות] [--write]

Single-word cards over the limit are reported, not split (shrink them by hand or rephrase). Idempotent.
"""
import argparse, copy, json, os, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
from PIL import ImageFont
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--max-px", type=float, default=740); ap.add_argument("--track", default="כתוביות"); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR); nid = lambda: str(uuid.uuid4()).upper()
tm = {m["id"]: m for m in d["materials"]["texts"]}; track = next(t for t in d["tracks"] if t.get("name") == A.track)
segs = sorted(track["segments"], key=lambda s: s["target_timerange"]["start"]); c0 = json.loads(tm[segs[0]["material_id"]]["content"]); st = c0["styles"][0]
font = ImageFont.truetype(st["font"]["path"], 60); size = st["size"]
def px(t, sc): return font.getlength(t) * size / 10 * sc
byid = {}
for k, v in d["materials"].items():
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict) and "id" in m: byid[m["id"]] = (k, m)
def clone(seg, text, t0, L):
    m = copy.deepcopy(tm[seg["material_id"]]); m["id"] = nid(); c = json.loads(m["content"]); c["text"] = text
    for s_ in c.get("styles", []): s_["range"] = [0, len(text)]
    m["content"] = json.dumps(c, ensure_ascii=False); d["materials"]["texts"].append(m); tm[m["id"]] = m
    s = copy.deepcopy(seg); s["id"] = nid(); s["material_id"] = m["id"]; s["target_timerange"] = {"start": int(t0), "duration": int(L)}; s["source_timerange"] = None if seg.get("source_timerange") is None else {"start": 0, "duration": int(L)}
    refs = []
    for r in seg.get("extra_material_refs", []):
        if r in byid: k, mm = byid[r]; m2 = copy.deepcopy(mm); m2["id"] = nid(); d["materials"][k].append(m2); refs.append(m2["id"])
    s["extra_material_refs"] = refs; return s
out = []; n_split = 0; single = []
for s in segs:
    t = json.loads(tm[s["material_id"]]["content"])["text"]; sc = s["clip"]["scale"]["x"]; w = px(t, sc)
    if w <= A.max_px: out.append(s); continue
    words = t.split()
    if len(words) < 2: single.append((s["target_timerange"]["start"] / US, t, round(w))); out.append(s); continue
    best = min(range(1, len(words)), key=lambda i: abs(px(" ".join(words[:i]), sc) - px(" ".join(words[i:]), sc)))
    a, b = " ".join(words[:best]), " ".join(words[best:]); t0 = s["target_timerange"]["start"]; L = s["target_timerange"]["duration"]
    La = snap(L * len(a) / (len(a) + len(b))); La = max(int(0.30 * US), min(La, L - int(0.30 * US)))
    out += [clone(s, a, t0, La), clone(s, b, t0 + La, L - La)]; n_split += 1
    print(f"  {t0/US:7.2f} {w:4.0f}px «{t}» → «{a}» {La/US:.2f}s | «{b}» {(L-La)/US:.2f}s")
dead = {s["material_id"] for s in segs} - {s["material_id"] for s in out}
d["materials"]["texts"] = [m for m in d["materials"]["texts"] if m["id"] not in dead]
track["segments"] = sorted(out, key=lambda s: s["target_timerange"]["start"])
for a, t, w in single: print(f"  ⚠️ single word over limit, left alone: {a:7.2f} {w}px «{t}»")
print(f"split {n_split} cards | track now {len(track['segments'])} cards")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
