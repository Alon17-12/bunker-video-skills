# -*- coding: utf-8 -*-
"""Add b-roll items to an EXISTING `broll` track without rebuilding it — the surgical counterpart of `reel_broll.py`.

Why it exists (0923 r10): Alon edited the draft by hand between rounds (removed two b-rolls and a bed, animated the
reel-1 arrow, dropped three captions). `reel_broll.py` tears the whole track down and rebuilds it from an items
file, which would silently undo every one of those edits — his hand-work is sacred. This script only ADDS segments
(and optionally trims existing ones), cloning the nearest existing b-roll segment as the template so every
CapCut-internal field comes along; the clip recipe is reel_broll's (1.08 → 1.0 settle over 0.5 s, CurveOut, full
cover). Each new item also gets a click on the `sfx` track (clone of an existing click segment, same volume).

    python reel_broll_add.py "<project>" --items new_items.json [--trim ccstudio-broll-n2-meeting.mp4=1.75,…] [--write]

items: [{"file": "ccstudio-broll-n2-call.mp4", "t": 110.03, "dur": 2.2, "off": 0.0, "why": "«…»"}, …] — files already in
the draft folder (broll_cut.py / a transcoded Remotion render). Refuses an item that overlaps anything on the track
after the trims; register_media.py --write afterwards so the files show in the Media panel.
"""
import argparse, copy, json, os, re, subprocess, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
US = 1_000_000; FF = str(paths.FFMPEG)
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--items", required=True); ap.add_argument("--trim", default="", help="file=dur,file=dur — shorten existing b-roll segments (seconds)")
ap.add_argument("--remove", default="", help="file,file — drop these b-roll segments (and the click at their start); the file stays on disk for you to delete")
ap.add_argument("--track", default="broll"); ap.add_argument("--tpl-track", default="", help="clone the template from this video track when the b-roll track holds only stills (לקוח M 04.10: arrows only)"); ap.add_argument("--sfx", default="sfx"); ap.add_argument("--click", default="ccstudio-sfx-click"); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]; FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR); nid = lambda: str(uuid.uuid4()).upper()
vm = {m["id"]: m for m in mats["videos"]}; am = {m["id"]: m for m in mats["audios"]}
track = next(t for t in d["tracks"] if t.get("name") == A.track); sfx = next((t for t in d["tracks"] if t.get("name") == A.sfx), None)
def probe(path):
    r = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r); dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0
    wh = re.search(r"(\d{3,5})x(\d{3,5})", r); return int(wh.group(1)), int(wh.group(2)), int(round(dur * US))
def kf(t, v, curve="CurveInOut"):
    return {"id": nid(), "time_offset": t, "values": [v], "curveType": curve, "graphID": "", "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}}
def group(pt, keys): return {"id": nid(), "property_type": pt, "keyframe_list": keys}
# ---- removes (0923 r10: the «phone call» pick turned out to be a guest adjusting a mic — literal or nothing) ----
for fn in [x for x in A.remove.split(",") if x]:
    hit = [s for s in track["segments"] if vm[s["material_id"]]["material_name"] == fn]; assert len(hit) == 1, f"remove {fn}: {len(hit)} segments"
    s = hit[0]; t0 = s["target_timerange"]["start"]; dead = {s["material_id"], *s.get("extra_material_refs", [])}; track["segments"].remove(s)
    if sfx:
        for c in [c for c in sfx["segments"] if c["target_timerange"]["start"] == t0 and am.get(c["material_id"], {}).get("name") == A.click]:
            dead |= set(c.get("extra_material_refs", [])); sfx["segments"].remove(c)     # the click MATERIAL is shared by every click — never dead
    for k, v in mats.items():
        if isinstance(v, list): mats[k] = [m for m in v if not (isinstance(m, dict) and m.get("id") in dead)]
    print(f"  − {fn} @ {t0/US:.2f} (+ its click)")
# ---- trims ----
for spec in [x for x in A.trim.split(",") if x]:
    fn, dur = spec.split("="); dur = snap(float(dur) * US); hit = [s for s in track["segments"] if vm[s["material_id"]]["material_name"] == fn]
    assert len(hit) == 1, f"trim {fn}: {len(hit)} segments"
    s = hit[0]; old = s["target_timerange"]["duration"]; s["target_timerange"]["duration"] = dur; s["source_timerange"]["duration"] = dur
    for g in s.get("common_keyframes", []):
        for k in g["keyframe_list"]:
            if k["time_offset"] == old: k["time_offset"] = dur        # the tail key follows the new end
        g["keyframe_list"] = [k for k in g["keyframe_list"] if k["time_offset"] <= dur]
    print(f"  trim {fn}: {old/US:.2f} → {dur/US:.2f}s @ {s['target_timerange']['start']/US:.2f}")
# ---- adds ----
items = json.load(open(A.items)); video_segs = [s for s in track["segments"] if vm[s["material_id"]].get("type") == "video"]
if not video_segs and A.tpl_track: video_segs = [s for s in next(t for t in d["tracks"] if t.get("name") == A.tpl_track)["segments"] if vm[s["material_id"]].get("type") == "video"]
assert video_segs, "no video b-roll segment to clone"
click_segs = [s for s in (sfx["segments"] if sfx else []) if am.get(s["material_id"], {}).get("name") == A.click]
added = []
for it in items:
    path = D / it["file"]; assert path.exists(), path
    w, h, dur_us = probe(path); t0 = snap(it["t"] * US); L = snap(it["dur"] * US); off = snap(it.get("off", 0.0) * US)
    if off + L > dur_us: L = dur_us - off
    tpl = min(video_segs, key=lambda s: abs(s["target_timerange"]["start"] - t0)); tm_ = vm[tpl["material_id"]]
    m = copy.deepcopy(tm_); m.update({"id": nid(), "material_name": path.name, "path": str(path), "duration": dur_us, "width": w, "height": h, "local_material_id": "",
                                       "material_id": "", "category_id": "", "category_name": "local", "source": 0, "check_flag": 63043327})
    mats["videos"].append(m); vm[m["id"]] = m
    refs = []
    for r in tpl.get("extra_material_refs", []):
        for k, v in mats.items():
            if isinstance(v, list):
                src = next((x for x in v if isinstance(x, dict) and x.get("id") == r), None)
                if src is not None: c = copy.deepcopy(src); c["id"] = nid(); v.append(c); refs.append(c["id"]); break
    cover = max(1080 / w, 1920 / h) / min(1080 / w, 1920 / h) if (w, h) != (1080, 1920) else 1.0
    s = copy.deepcopy(tpl); s.update({"id": nid(), "material_id": m["id"], "extra_material_refs": refs, "render_index": max(x["render_index"] for x in track["segments"]) + 1, "keyframe_refs": [], "speed": 1.0, "volume": 0.0,
                                      "target_timerange": {"start": t0, "duration": L}, "source_timerange": {"start": off, "duration": L}})
    sc = [kf(off, cover * 1.08, "CurveOut"), kf(off + snap(0.5 * US), cover * 1.0, "CurveOut"), kf(off + L, cover * 1.0)]
    s["clip"] = {"scale": {"x": sc[0]["values"][0], "y": sc[0]["values"][0]}, "rotation": 0.0, "transform": {"x": 0.0, "y": 0.0}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    s["common_keyframes"] = [group("KFTypeScaleX", sc), group("KFTypeScaleY", [dict(k, id=nid()) for k in sc]), group("KFTypePositionX", [kf(off, 0.0), kf(off + L, 0.0)]), group("KFTypePositionY", [kf(off, 0.0), kf(off + L, 0.0)])]
    track["segments"].append(s); added.append(s)
    if click_segs:
        c = copy.deepcopy(min(click_segs, key=lambda x: abs(x["target_timerange"]["start"] - t0))); c["id"] = nid(); c["target_timerange"]["start"] = t0; c["render_index"] = max(x["render_index"] for x in sfx["segments"]) + 1
        c["extra_material_refs"] = []   # audio refs are per-segment speed/beats clones; a click carries none it needs
        for r in min(click_segs, key=lambda x: abs(x["target_timerange"]["start"] - t0)).get("extra_material_refs", []):
            for k, v in mats.items():
                if isinstance(v, list):
                    src = next((x for x in v if isinstance(x, dict) and x.get("id") == r), None)
                    if src is not None: cc = copy.deepcopy(src); cc["id"] = nid(); v.append(cc); c["extra_material_refs"].append(cc["id"]); break
        sfx["segments"].append(c)
    print(f"  + {t0/US:7.2f} +{L/US:.2f}s {path.name:40} {w}x{h} tpl@{tpl['target_timerange']['start']/US:.2f} click {'✓' if click_segs else '-'} — {it.get('why', '')}")
# ---- QA ----
for t in (track, sfx):
    if not t: continue
    t["segments"].sort(key=lambda s: s["target_timerange"]["start"])
    ov = [(a, b) for a, b in zip(t["segments"], t["segments"][1:]) if b["target_timerange"]["start"] < a["target_timerange"]["start"] + a["target_timerange"]["duration"] - 1]
    if t is track: assert not ov, "overlap on broll: " + ", ".join(f"{vm[a['material_id']]['material_name']}→{vm[b['material_id']]['material_name']} @ {b['target_timerange']['start']/US:.2f}" for a, b in ov)
    elif ov: print(f"  ⚠ sfx overlaps {len(ov)} (clicks 0.28 s; two hits inside a window keep both)")
print(f"broll now {len(track['segments'])} segments (+{len(added)}) | sfx {len(sfx['segments']) if sfx else 0}")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
