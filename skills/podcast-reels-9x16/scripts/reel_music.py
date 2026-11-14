# -*- coding: utf-8 -*-
"""Swap the music beds of a reel project: one bed per reel (card start → next card start, so the card is not silent), the file copied
into the draft folder as a LOCAL material (`extract_music`, no `effect_id` — the library-clone trap), looped
in pieces when the master is shorter than the reel, fades 0.6 s in / 2.0 s out / 0.3 s at seams.

    python reel_music.py "<project>" --beds /path/a.mp3,/path/b.mp3,/path/c.mp3 [--vol 0.14] [--name מוזיקה] [--write]

One path per reel, in order; a single path repeats. Idempotent: the named audio track is rebuilt (its
materials and fades too). Re-run `reel_sound.py` afterwards — the ducking keys live on the bed pieces.
"""
import argparse, copy, json, os, re, shutil, subprocess, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
US = 1_000_000; FF = str(paths.FFMPEG)
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--beds", required=True); ap.add_argument("--vol", type=float, default=0.14); ap.add_argument("--fade-in", type=float, default=0.6, help="first piece fade-in (r8: 0.15 — a 0.6 s fade on top of a 0.5 s lead-in read as silence)"); ap.add_argument("--name", default="מוזיקה"); ap.add_argument("--start", choices=["card", "footage"], default="footage", help="bed starts at the white card (r3) or at the first footage frame after it (r4, Alon: «בתחילת הסרטון באופן מדויק יותר»)"); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]; FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR)
nid = lambda: str(uuid.uuid4()).upper(); beds = [b.strip() for b in A.beds.split(",") if b.strip()]
byid = {}
for k, v in mats.items():
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict) and "id" in m: byid[m["id"]] = (k, m)
def probe_us(p):
    r = subprocess.run([FF, "-i", str(p)], capture_output=True, text=True).stderr; m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r)
    return int(round((int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) * US))
track = next(t for t in d["tracks"] if t["type"] == "audio" and t.get("name") == A.name); am = {m["id"]: m for m in mats["audios"]}
dseg = copy.deepcopy(track["segments"][0]); dmat = copy.deepcopy(am[dseg["material_id"]])
dead = {s["material_id"] for s in track["segments"]} | {r for s in track["segments"] for r in s.get("extra_material_refs", [])}
for k in list(mats):
    if isinstance(mats[k], list): mats[k] = [m for m in mats[k] if not (isinstance(m, dict) and m.get("id") in dead)]
track["segments"] = []
vm = {m["id"]: m for m in mats["videos"]}; base = sorted([t for t in d["tracks"] if t["type"] == "video"][0]["segments"], key=lambda s: s["target_timerange"]["start"])
cards = [s for s in base if vm[s["material_id"]].get("type") == "photo"]; end = d["duration"]
spans = [((c["target_timerange"]["start"] if A.start == "card" else c["target_timerange"]["start"] + c["target_timerange"]["duration"]), (cards[i + 1]["target_timerange"]["start"] if i + 1 < len(cards) else end)) for i, c in enumerate(cards)]   # r3: from the card start (a silent card «קצת מוזר»); r4: Alon wants the bed exactly on the first footage frame
def refs(fade_in, fade_out):
    out = []
    for r in dseg.get("extra_material_refs", []):
        if r in byid:
            k, mm = byid[r]; m2 = copy.deepcopy(mm); m2["id"] = nid()
            if k == "audio_fades": m2["fade_in_duration"] = int(fade_in * US); m2["fade_out_duration"] = int(fade_out * US)
            mats[k].append(m2); out.append(m2["id"])
    return out
ri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
for i, (a, b) in enumerate(spans):
    src = beds[i] if i < len(beds) else beds[-1]; dst = D / f"ccstudio-music-{os.path.basename(src)}"
    if not dst.exists(): shutil.copy(src, dst)
    L = probe_us(dst); m = copy.deepcopy(dmat); m.update({"id": nid(), "name": dst.stem, "path": str(dst), "duration": L, "music_id": "", "local_material_id": "", "effect_id": "", "category_name": "local", "type": "extract_music", "wave_points": []}); mats["audios"].append(m)
    t = a; n = 0
    while t < b:
        piece = min(L, b - t); last = t + piece >= b; s = copy.deepcopy(dseg); ri += 1
        s.update({"id": nid(), "material_id": m["id"], "extra_material_refs": refs(A.fade_in if n == 0 else 0.3, 2.0 if last else 0.3), "render_index": ri, "volume": A.vol, "last_nonzero_volume": A.vol, "common_keyframes": [], "keyframe_refs": [],
                  "target_timerange": {"start": int(t), "duration": int(piece)}, "source_timerange": {"start": 0, "duration": int(piece)}})
        track["segments"].append(s); t += piece; n += 1
    print(f"  reel {i+1} {a/US:7.2f}–{b/US:7.2f}  {dst.name}  {L/US:.1f}s file → {n} piece(s) @ {A.vol}")
print(f"beds {len(track['segments'])} pieces on {len(spans)} reels")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
