# -*- coding: utf-8 -*-
"""The sound layer of a reel project: a click on every b-roll / framed insert, a swoosh on every super, and
the bed ducked −3 dB (×0.71) under every b-roll window (creator-styles.md §9 — "a whoosh/click on every
graphic", "ducks −3 dB under b-roll"). One SFX track (`sfx`); volume keyframes on the bed pieces.

    python reel_sound.py "<project>" --click ccstudio-sfx-click.mp3 --swoosh ccstudio-sfx-swoosh.mp3 [--click-vol 0.6] [--swoosh-vol 0.35] [--duck 0.71] [--ramp 0.3] [--write]

Files live in the draft folder as local materials (cloned from the project's own bed material so no
library `effect_id` survives — the 0922 silent-bed trap). Two hits inside 0.25 s keep the first.
Idempotent: tears the `sfx` track down and strips previous KFTypeVolume groups from the beds.
Volume keys are `Line` — that is what CapCut writes for its own volume keys (0910 donor); the ease rule
is for motion. Read-only without --write.
"""
import argparse, copy, json, os, re, subprocess, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
US = 1_000_000; FF = str(paths.FFMPEG)
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--click", required=True); ap.add_argument("--swoosh", required=True); ap.add_argument("--pop", default="", help="SFX for photo/overlay b-roll items (emoji pops); default = the click")
ap.add_argument("--click-vol", type=float, default=0.6); ap.add_argument("--swoosh-vol", type=float, default=0.35); ap.add_argument("--duck", type=float, default=0.71); ap.add_argument("--ramp", type=float, default=0.3)
ap.add_argument("--broll", default="broll"); ap.add_argument("--supers", default="supers"); ap.add_argument("--bed", default="מוזיקה"); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]; FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR)
nid = lambda: str(uuid.uuid4()).upper()
byid = {}
for k, v in mats.items():
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict) and "id" in m: byid[m["id"]] = (k, m)
gone = [t for t in d["tracks"] if t.get("name") == "sfx"]
dead = {s["material_id"] for t in gone for s in t["segments"]} | {r for t in gone for s in t["segments"] for r in s.get("extra_material_refs", [])}
for k in list(mats):
    if isinstance(mats[k], list): mats[k] = [m for m in mats[k] if not (isinstance(m, dict) and m.get("id") in dead)]
d["tracks"] = [t for t in d["tracks"] if t not in gone]
def probe_us(p):
    r = subprocess.run([FF, "-i", str(p)], capture_output=True, text=True).stderr; m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r)
    return int(round((int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) * US))
bed = next(t for t in d["tracks"] if t["type"] == "audio" and t.get("name") == A.bed); am = {m["id"]: m for m in mats["audios"]}
dseg = bed["segments"][0]; dmat = am[dseg["material_id"]]
def material(fn):
    p = D / fn; m = copy.deepcopy(dmat); m.update({"id": nid(), "name": p.stem, "path": str(p), "duration": probe_us(p), "music_id": "", "local_material_id": "", "effect_id": "", "category_name": "local", "type": "extract_music", "wave_points": []}); mats["audios"].append(m); return m
def clone_refs(seg):
    out = []
    for r in seg.get("extra_material_refs", []):
        if r in byid:
            k, mm = byid[r]; m2 = copy.deepcopy(mm); m2["id"] = nid()
            if k == "audio_fades": m2["fade_in_duration"] = m2["fade_out_duration"] = 0
            mats[k].append(m2); out.append(m2["id"])
    return out
track = {"attribute": 0, "flag": 0, "id": nid(), "is_default_name": False, "name": "sfx", "segments": [], "type": "audio"}
ri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
def hit(m, t, vol, label):
    global ri
    st = snap(t * US)
    if any(abs(s["target_timerange"]["start"] - st) < int(0.6 * US) for s in track["segments"]): print(f"  · {label} at {t:.2f} inside 0.6 s of another hit, skipped"); return
    s = copy.deepcopy(dseg); ri += 1; dur = m["duration"] - 20_000                       # never read past the file end
    s.update({"id": nid(), "material_id": m["id"], "extra_material_refs": clone_refs(dseg), "render_index": ri, "volume": vol, "last_nonzero_volume": vol, "common_keyframes": [], "keyframe_refs": [],
              "target_timerange": {"start": st, "duration": dur}, "source_timerange": {"start": 0, "duration": dur}}); track["segments"].append(s)
click = material(A.click); swoosh = material(A.swoosh); pop = material(A.pop) if A.pop else click
vm = {m["id"]: m for m in mats["videos"]}
photo_starts = {s["target_timerange"]["start"] / US for t in d["tracks"] if t.get("name") in A.broll.split(",") for s in t["segments"] if vm[s["material_id"]].get("type") == "photo"}
wins = sorted((s["target_timerange"]["start"] / US, (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / US) for t in d["tracks"] if t.get("name") in A.broll.split(",") for s in t["segments"])
full = sorted((s["target_timerange"]["start"] / US, (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / US) for t in d["tracks"] if t.get("name") in A.broll.split(",") for s in t["segments"]
              if s["clip"]["transform"]["x"] == 0 and s["clip"]["transform"]["y"] == 0 and s["clip"]["scale"]["x"] >= 0.99)   # ducking only under FULL-FRAME inserts, not under a badge / arrow / title overlay
sups = sorted(s["target_timerange"]["start"] / US for t in d["tracks"] if t.get("name") == A.supers for s in t["segments"])
title_starts = {s["target_timerange"]["start"] / US for t in d["tracks"] if t.get("name") in A.broll.split(",") for s in t["segments"] if "title" in vm[s["material_id"]].get("material_name", "") or "counter" in vm[s["material_id"]].get("material_name", "")}   # r8: rendered motion titles on the b-roll track get the swoosh, not a click
for a, b in wins: hit(swoosh if a in title_starts else (pop if a in photo_starts else click), a, A.swoosh_vol if a in title_starts else A.click_vol, "swoosh" if a in title_starts else ("pop" if a in photo_starts else "click"))
for a in sups: hit(swoosh, a, A.swoosh_vol, "swoosh")
# trim any hit that would run into the next one
ss = sorted(track["segments"], key=lambda s: s["target_timerange"]["start"])
for x, y in zip(ss, ss[1:]):
    end = x["target_timerange"]["start"] + x["target_timerange"]["duration"]
    if y["target_timerange"]["start"] < end: x["target_timerange"]["duration"] = x["source_timerange"]["duration"] = y["target_timerange"]["start"] - x["target_timerange"]["start"]
track["segments"] = ss; pos = next(i for i, t in enumerate(d["tracks"]) if t is bed) + 1; d["tracks"].insert(pos, track)
# ducking
def kf(t, v): return {"id": nid(), "curveType": "Line", "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
n_duck = 0
if A.duck >= 0.999: full = []   # --duck 1.0: strip old volume keys, write none (0923 r4: 22 dips in 4 min read as pumping; the bed is already 16 dB under the voice)
for s in bed["segments"]:
    s["common_keyframes"] = [g for g in s.get("common_keyframes", []) if g["property_type"] != "KFTypeVolume"]
    t0 = s["target_timerange"]["start"]; t1 = t0 + s["target_timerange"]["duration"]; src0 = s["source_timerange"]["start"]; v = s["volume"]; R = int(A.ramp * US)
    pts = {}
    for a, b in full:
        a, b = snap(a * US), snap(b * US)
        if b <= t0 or a >= t1: continue
        for t, val in ((a - R, v), (a, v * A.duck), (b, v * A.duck), (b + R, v)): pts[min(max(t, t0), t1)] = val
        n_duck += 1
    if not pts: continue
    pts.setdefault(t0, v); pts.setdefault(t1, v)
    keys = [kf(src0 + (t - t0), val) for t, val in sorted(pts.items())]
    s["common_keyframes"].append({"id": nid(), "material_id": "", "property_type": "KFTypeVolume", "keyframe_list": keys})
print(f"sfx {len(ss)} hits ({len(wins)} clicks on b-roll, {len(sups)} swooshes on supers) | ducked {n_duck} windows ×{A.duck} | tracks {[t.get('name') or t['type'] for t in d['tracks']]}")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
