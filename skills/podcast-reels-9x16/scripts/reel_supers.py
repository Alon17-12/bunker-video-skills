# -*- coding: utf-8 -*-
"""Keyword supers for a 9:16 reel project — the creator grammar (creator-styles.md §2/3): ONE huge keyword
in the brand's accent colour, white for the rest, in the top band where the face isn't, Grow in / Fade Out,
on its own text track `supers`. Also hook supers, name cards (two lines) and CTA supers — same mechanism.

    python reel_supers.py "<project>" --plan supers.json [--y 0.78] [--y-name 0.80] [--accent d01020] [--max-px 900] [--write]

plan: [{"t0": 5.0, "t1": 8.4, "text": "אל תפיקו פודקאסט", "hl": ["אל תפיקו"], "kind": "super"}, …]
kind: super (hl in accent) · cta (all accent) · name (two lines "\\n", line 2 accent) · hook (= super) · title ("01\\nkeyword": accent kicker at 0.6× over a white keyword, 26–36).
Style donor = the caption material (font, stroke, shadow); size fits the line to --max-px (default 860: CapCut wraps
at `line_max_width` 0.82 × 1080 = 886 px — Alon's 0922 titles prove it) using px = PIL@60(txt) × size/10, clamped to [22, 40] (one line only: two 34-size lines would reach
the hairline). Idempotent: tears its own track down. Read-only without --write.
"""
import argparse, copy, json, os, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
from PIL import ImageFont
US = 1_000_000; SP = os.path.dirname(os.path.abspath(__file__)); AN = json.load(open(os.path.join(SP, "..", "references", "text_anim_donors.json")))
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--plan", required=True); ap.add_argument("--y", type=float, default=0.78); ap.add_argument("--y-name", type=float, default=0.80)
ap.add_argument("--accent", default="d01020"); ap.add_argument("--max-px", type=float, default=860); ap.add_argument("--name", default="supers"); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]; FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR)
nid = lambda: str(uuid.uuid4()).upper(); plan = json.load(open(A.plan))
ACC = [int(A.accent[i:i+2], 16) / 255 for i in (0, 2, 4)]; WHITE = [1.0, 1.0, 1.0]
# teardown
gone = [t for t in d["tracks"] if t.get("name") == A.name]
dead = {s["material_id"] for t in gone for s in t["segments"]} | {r for t in gone for s in t["segments"] for r in s.get("extra_material_refs", [])}
for k in list(mats):
    if isinstance(mats[k], list): mats[k] = [m for m in mats[k] if not (isinstance(m, dict) and m.get("id") in dead)]
d["tracks"] = [t for t in d["tracks"] if t not in gone]
tm = {m["id"]: m for m in mats["texts"]}
cap = max((t for t in d["tracks"] if t["type"] == "text"), key=lambda t: len(t["segments"])); dseg = cap["segments"][0]; dmat = tm[dseg["material_id"]]
font = json.loads(dmat["content"])["styles"][0]["font"]["path"]; F60 = ImageFont.truetype(font, 60)
def fit(text, cap_size=40.0):
    w = max(F60.getlength(line) for line in text.split("\n")); return max(22.0, min(cap_size, round(A.max_px / w * 10 * 2) / 2))
def styled(m, text, ranges, size, colour_default):
    for field in ("content", "base_content"):
        if not m.get(field): continue
        c = json.loads(m[field]); base = copy.deepcopy(c["styles"][0]); base["size"] = size
        cuts = sorted({0, len(text)} | {x for r in ranges for x in (r[0], r[1])}); st = []
        for r0, r1 in zip(cuts, cuts[1:]):
            s = copy.deepcopy(base); s["range"] = [r0, r1]; hit = next((r for r in ranges if r[0] <= r0 < r[1]), None); col = hit[2] if hit else colour_default
            s["fill"]["content"]["solid"]["color"] = col; s["size"] = (hit[3] if hit and len(hit) > 3 else size); st.append(s)
        c["text"] = text; c["styles"] = st; m[field] = json.dumps(c, ensure_ascii=False)
    m["font_size"] = size; m["text_size"] = size if "text_size" in m else m.get("text_size")
def anim_wrapper(kinds):
    w = copy.deepcopy(AN["wrapper"]); w["id"] = nid(); w["animations"] = []
    for key, dur in kinds:
        a = copy.deepcopy(AN["anims"][key]); a["duration"] = int(dur * US); w["animations"].append(a)
    mats.setdefault("material_animations", []).append(w); return w["id"]
track = {"attribute": 0, "flag": 0, "id": nid(), "is_default_name": False, "name": A.name, "segments": [], "type": "text"}
ri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
vm = {m["id"]: m for m in mats["videos"]}; base = [t for t in d["tracks"] if t["type"] == "video"][0]
cards = [(s["target_timerange"]["start"], s["target_timerange"]["start"] + s["target_timerange"]["duration"]) for s in base["segments"] if vm[s["material_id"]].get("type") == "photo"]
for it in plan:
    text = it["text"]; kind = it.get("kind", "super"); t0 = snap(it["t0"] * US); t1 = snap(it["t1"] * US)
    if any(a + FR / 2 < t1 and t0 < b - FR / 2 for a, b in cards): print("  ⚠️ over a card, skipped:", text); continue
    ranges = []
    if kind == "cta": ranges = [(0, len(text), ACC)]
    elif kind == "name":
        i = text.find("\n"); ranges = [(i + 1, len(text), ACC)] if i >= 0 else []
    elif kind == "title":   # "01\nעוגנים": a small accent kicker over a white keyword — the typographic chapter title (0923 r6: the red circle badges read «ילדותי»)
        i = text.find("\n"); kw = fit(text[i + 1:], 36.0); ranges = [(0, i, ACC, round(kw * 0.6 * 2) / 2)] if i >= 0 else []
    else:
        for h in it.get("hl", []):
            i = text.find(h)
            if i < 0: print("  ⚠️ highlight not in text:", h, "|", text); continue
            ranges.append((i, i + len(h), ACC))
    size = {"name": min(24.0, fit(text)), "cta": min(34.0, fit(text)), "title": max(26.0, fit(text[text.find("\n") + 1:], 36.0))}.get(kind, fit(text))
    m = copy.deepcopy(dmat); m["id"] = nid(); capcut._set_text(m, text, None); styled(m, text, ranges, size, WHITE); mats["texts"].append(m)
    s = copy.deepcopy(dseg); ri += 1
    s.update({"id": nid(), "material_id": m["id"], "extra_material_refs": [anim_wrapper([("in:Grow", 0.35), ("out:Fade Out", 0.25)])], "render_index": ri, "keyframe_refs": [], "common_keyframes": [],
              "target_timerange": {"start": t0, "duration": t1 - t0}})
    s["clip"] = {"scale": {"x": 1.0, "y": 1.0}, "rotation": 0.0, "transform": {"x": 0.0, "y": A.y_name if kind == "name" else A.y}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    track["segments"].append(s); print(f"  {kind:5} {t0/US:7.2f}–{t1/US:7.2f} size {size:4.1f} ≈{max(F60.getlength(l) for l in text.split(chr(10)))*size/10:4.0f}px  {text.replace(chr(10), ' / ')}")
ss = sorted(track["segments"], key=lambda s: s["target_timerange"]["start"])
ov = [(a["target_timerange"]["start"] / US) for a, b in zip(ss, ss[1:]) if b["target_timerange"]["start"] < a["target_timerange"]["start"] + a["target_timerange"]["duration"]]
d["tracks"].append(track); print(f"supers {len(ss)} | overlaps {ov} | tracks {[t.get('name') or t['type'] for t in d['tracks']]}")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
