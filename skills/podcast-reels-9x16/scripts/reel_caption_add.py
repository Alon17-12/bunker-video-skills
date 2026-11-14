# -*- coding: utf-8 -*-
"""Add / retext caption cards on the caption track (largest text track), cloned from its own first card.

    python reel_caption_add.py "<project>" --cards cards.json [--write]
cards.json: [{"t0": 229.17, "t1": 230.0, "text": "אני גם עשיתי את זה"}, {"at": 235.92, "text": "לא היה טוב"}]
`at` retexts the card starting there (±0.05 s); `del` removes it; `t0/t1` adds a card (refused if it overlaps an existing one).
"""
import argparse, copy, json, os, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--cards", required=True); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]; FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR)
nid = lambda: str(uuid.uuid4()).upper(); cards = json.load(open(A.cards))
tm = {m["id"]: m for m in mats["texts"]}; cap = max((t for t in d["tracks"] if t["type"] == "text"), key=lambda t: len(t["segments"]))
dseg = min(cap["segments"], key=lambda s: s["target_timerange"]["start"]); dmat = tm[dseg["material_id"]]
ri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
for c in cards:
    if "del" in c:
        n0 = len(cap["segments"]); cap["segments"] = [s for s in cap["segments"] if abs(s["target_timerange"]["start"] - c["del"] * US) >= 50_000]; print(f"  delete {c['del']:7.2f} ({n0 - len(cap['segments'])})"); continue
    if "at" in c:
        s = next((s for s in cap["segments"] if abs(s["target_timerange"]["start"] - c["at"] * US) < 50_000), None)
        if not s: print("  ⚠️ no card at", c["at"]); continue
        capcut._set_text(tm[s["material_id"]], c["text"], None); print(f"  retext {c['at']:7.2f} → {c['text']}"); continue
    t0, t1 = snap(c["t0"] * US), snap(c["t1"] * US)
    if any(s["target_timerange"]["start"] < t1 and t0 < s["target_timerange"]["start"] + s["target_timerange"]["duration"] for s in cap["segments"]): print("  ⚠️ overlaps an existing card, skipped:", c); continue
    m = copy.deepcopy(dmat); m["id"] = nid(); capcut._set_text(m, c["text"], None); mats["texts"].append(m)
    s = copy.deepcopy(dseg); ri += 1; s.update({"id": nid(), "material_id": m["id"], "render_index": ri, "extra_material_refs": [], "keyframe_refs": [], "common_keyframes": [], "target_timerange": {"start": t0, "duration": t1 - t0}})
    cap["segments"].append(s); print(f"  add {t0/US:7.2f}–{t1/US:7.2f} {c['text']}")
cap["segments"].sort(key=lambda s: s["target_timerange"]["start"]); print(f"captions now {len(cap['segments'])}")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
