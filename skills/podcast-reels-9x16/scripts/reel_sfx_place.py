# -*- coding: utf-8 -*-
"""Place designed sound effects on a reel's `sfx` track — one composite wav per animated insert, replacing the generic
click `reel_sound.py` / `reel_broll_add.py` put there. 0923 r11: Alon «תכין סאונד אפקטס תואם לכל סרטון כזה» — a riser
under a counter, keyboard under a form, a notification when the reply lands; mixed offline (ffmpeg) into
`ccstudio-sfx-anim-<name>.wav` so each insert is ONE segment that starts with its cut.

    python reel_sfx_place.py "<project>" --items sfx.json [--write]

items: [{"t": 122.95, "file": "ccstudio-sfx-anim-suppliers.wav", "vol": 0.35, "replace_click": true}, …]
Files sit in the draft folder. The material is cloned from the project's own click material (local, no effect_id —
the 0922 silent-bed trap); the segment from a click segment. A hit that would overlap a neighbour on `sfx` goes to
`sfx 2`. register_media.py --write afterwards.
"""
import argparse, copy, json, os, re, subprocess, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
US = 1_000_000; FF = str(paths.FFMPEG)
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--items", required=True); ap.add_argument("--sfx", default="sfx"); ap.add_argument("--click", default="ccstudio-sfx-click"); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]; FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR); nid = lambda: str(uuid.uuid4()).upper()
am = {m["id"]: m for m in mats["audios"]}; sfx = next(t for t in d["tracks"] if t.get("name") == A.sfx)
tpl = next(s for s in sfx["segments"] if am[s["material_id"]]["name"] == A.click); tmat = am[tpl["material_id"]]
def probe_us(p):
    r = subprocess.run([FF, "-i", str(p)], capture_output=True, text=True).stderr; m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r); return int(round((int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) * US))
maxri = max(s["render_index"] for s in sfx["segments"]); lane2 = next((t for t in d["tracks"] if t.get("name") == f"{A.sfx} 2"), None); placed = []
for it in json.load(open(A.items)):
    p = D / it["file"]; assert p.exists(), p; t0 = snap(it["t"] * US); dur = probe_us(p)
    if it.get("replace_click", True):
        for s in [s for s in sfx["segments"] if s["target_timerange"]["start"] == t0 and am[s["material_id"]]["name"] == A.click]: sfx["segments"].remove(s)
    m = copy.deepcopy(tmat); m.update({"id": nid(), "name": p.stem, "material_name": p.name, "path": str(p), "duration": dur, "music_id": "", "local_material_id": "", "effect_id": "", "category_name": "local", "type": "extract_music", "wave_points": []}); mats["audios"].append(m); am[m["id"]] = m
    s = copy.deepcopy(tpl); maxri += 1; refs = []
    for r in tpl.get("extra_material_refs", []):
        for k, v in mats.items():
            if isinstance(v, list):
                src = next((x for x in v if isinstance(x, dict) and x.get("id") == r), None)
                if src is not None: c = copy.deepcopy(src); c["id"] = nid(); v.append(c); refs.append(c["id"]); break
    vol = float(it.get("vol", 0.35))
    s.update({"id": nid(), "material_id": m["id"], "extra_material_refs": refs, "render_index": maxri, "volume": vol, "last_nonzero_volume": vol, "target_timerange": {"start": t0, "duration": dur}, "source_timerange": {"start": 0, "duration": dur}, "common_keyframes": [], "keyframe_refs": []})
    clash = [x for x in sfx["segments"] if x["target_timerange"]["start"] < t0 + dur and x["target_timerange"]["start"] + x["target_timerange"]["duration"] > t0]
    if clash:
        if lane2 is None: lane2 = {"attribute": 0, "flag": 0, "id": nid(), "is_default_name": False, "name": f"{A.sfx} 2", "segments": [], "type": "audio"}; d["tracks"].append(lane2)
        lane2["segments"].append(s); where = "sfx 2"
    else: sfx["segments"].append(s); where = "sfx"
    placed.append(s); print(f"  ♪ {t0/US:7.2f} +{dur/US:.2f}s {p.name:36} vol {vol:.2f} → {where}" + (f"  (clash with {len(clash)})" if clash else ""))
sfx["segments"].sort(key=lambda s: s["target_timerange"]["start"])
print(f"placed {len(placed)} | sfx {len(sfx['segments'])} segments" + (f" | sfx 2 {len(lane2['segments'])}" if lane2 else ""))
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
