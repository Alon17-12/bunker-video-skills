# -*- coding: utf-8 -*-
"""Two small consistency fixes on a reel project.
    python reel_polish.py "<project>" [--mute-over] [--lut-over-cards] [--write]
--mute-over        every segment on the second video track (the over/angle layer) → volume 0. When both
                   cameras carry the same mix (a single RODECaster feed, 0923) the two layers sum = +6 dB
                   and a comb filter on any sub-frame offset — the 0922 "מיקרופון של מצלמה 2 מוזר" fault.
--align-angle-cuts a hidden over-layer sliver before a visible cutaway becomes visible, so the angle switch sits on the jump cut
--lut-over-cards   each adjust segment that starts on the first footage after a white card is extended
                   back over the card, so the grade is identical from the first frame (qa25 check 26).
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--mute-over", action="store_true"); ap.add_argument("--lut-over-cards", action="store_true"); ap.add_argument("--align-angle-cuts", action="store_true"); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); vm = {m["id"]: m for m in d["materials"]["videos"]}
vt = [t for t in d["tracks"] if t["type"] == "video" and t["segments"]]
if A.mute_over:
    n = 0
    for s in vt[1]["segments"]:
        if s.get("volume", 1.0) != 0.0: s["volume"] = 0.0; s["last_nonzero_volume"] = 1.0; n += 1
    print(f"over layer: muted {n}/{len(vt[1]['segments'])} segments")
if A.lut_over_cards:
    segs = sorted(vt[0]["segments"], key=lambda s: s["target_timerange"]["start"])
    cards = [(s["target_timerange"]["start"], s["target_timerange"]["start"] + s["target_timerange"]["duration"]) for s in segs if vm[s["material_id"]].get("type") == "photo"]
    for t in d["tracks"]:
        if t["type"] != "adjust": continue
        for s in t["segments"]:
            a = s["target_timerange"]["start"]
            for c0, c1 in cards:
                if abs(c1 - a) <= 1:
                    s["target_timerange"] = {"start": c0, "duration": s["target_timerange"]["duration"] + (a - c0)}
                    if s.get("source_timerange"): s["source_timerange"] = {"start": s["source_timerange"]["start"], "duration": s["target_timerange"]["duration"]}
                    print(f"adjust {a/US:.2f} → starts at card {c0/US:.2f}")
if A.align_angle_cuts:
    # a hidden over-layer sliver (< 0.5 s) right before a visible cutaway = the angle switch lands a beat AFTER the jump cut →
    # two visual events 0.1–0.3 s apart («קפיצות מוזרות … מעבר מהיר וחזרה», Alon 0923 round 3). Show the sliver: the switch lands ON the cut.
    ov = sorted(vt[1]["segments"], key=lambda s: s["target_timerange"]["start"]); n = 0
    for a, b in zip(ov, ov[1:]):
        if a["clip"]["alpha"] < 0.01 and b["clip"]["alpha"] >= 0.99 and a["target_timerange"]["duration"] < 0.5 * US and abs(a["target_timerange"]["start"] + a["target_timerange"]["duration"] - b["target_timerange"]["start"]) <= 1:
            a["clip"]["alpha"] = 1.0; n += 1; print(f"angle cut aligned: {a['target_timerange']['start']/US:.2f} (+{a['target_timerange']['duration']/US:.2f}s sliver now visible)")
    print(f"angle cuts aligned {n}")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
