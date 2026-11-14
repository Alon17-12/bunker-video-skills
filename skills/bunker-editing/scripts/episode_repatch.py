#!/usr/bin/env python3
"""A new version of an episode project with new routing patches (and its dialogue back inside the draft) — the project is
copied, never rebuilt, so anything changed in it by hand stays (house rule: patch his project, don't rebuild).

    $PY skill/scripts/episode_repatch.py "<project>" "<new project>" <patches.json> --trim-in 3.6 [--audio-m4a] [--zoom 2=1.12:-0.12]

--zoom CAM=SCALE:TX: every patch of that camera scaled and shifted (TX in half-canvas widths; −(SCALE−1) keeps its right edge,
+(SCALE−1) its left). With routing_cover.py first, that is every frame the camera is on screen (אורח C 27.10.2026: Guest C's
hand from the left edge of cam 2 → 2=1.12:-0.12 crops 10.7 % off the left, 5.4 % top and bottom).

--audio-m4a: the dialogue track's file is re-encoded to AAC 320k inside the new draft folder (CapCut's sandbox cannot
read the SSD — «File not accessible», 21.10.2026 — and the WAV is 1.7 GB on a nearly full disk).
CapCut must be closed.
"""
import argparse, copy, json, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402
import reels  # noqa: E402

US = 1_000_000
FPS = 30
FF = str(Path.home() / "ffmpeg-bin/ffmpeg")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("patches")
    ap.add_argument("--trim-in", type=float, required=True); ap.add_argument("--audio-m4a", action="store_true")
    ap.add_argument("--dialogue", help="a new dialogue master (Live-Mix clock): trimmed like the picture → AAC 320k in the draft, replaces the dialogue track's file")
    ap.add_argument("--duration", type=float, help="with --dialogue: the episode length (s)")
    ap.add_argument("--zoom", action="append", default=[], help="CAM=SCALE:TX, e.g. 2=1.12:-0.12")
    a = ap.parse_args()
    if capcut.capcut_running():
        raise SystemExit("⛔ CapCut פתוח — סגור אותו לגמרי ותריץ שוב.")
    name = reels._unique_name(a.dst)
    dst = capcut.DRAFTS_DIR / name
    reels._copy_draft_folder(capcut.DRAFTS_DIR / a.src, dst)
    d = json.loads(capcut._draft_file(dst).read_text())
    mats = d["materials"]
    vids = {m["id"]: m for m in mats["videos"]}
    tr = next(t for t in d["tracks"] if t.get("name") == "ניתוב")
    donors = {}
    for s in tr["segments"]:
        p = vids[s["material_id"]]["path"]
        donors.setdefault(1 if p.endswith(" 1.mp4") else 2, s)
    by_list = {e["id"]: k for k, v in mats.items() if isinstance(v, list) for e in v if isinstance(e, dict) and "id" in e}
    old_refs = {r for s in tr["segments"] for r in s.get("extra_material_refs", [])}
    zoom = {int(c): tuple(map(float, v.split(":"))) for c, v in (z.split("=") for z in a.zoom)}
    segs = []
    for cam, f, g, *rest in json.loads(Path(a.patches).read_text()):
        so = rest[0] if rest else 0.0          # routing_frames.py: the camera file's offset against «מקור» (s)
        don = donors[cam]
        seg = copy.deepcopy(don); seg["id"] = capcut._new_id()
        refs = []
        for r in don.get("extra_material_refs", []):
            lst = by_list.get(r)
            if not lst or lst == "transitions":   # a donor from an older build: the spine's closing fade must not land on every patch
                continue
            e = copy.deepcopy(next(x for x in mats[lst] if x.get("id") == r)); e["id"] = capcut._new_id()
            mats[lst].append(e); refs.append(e["id"])
        seg["extra_material_refs"] = refs
        # on the frame grid, exactly (21.10.2026: a patch saved as 5110.4667 starts 33 µs after its frame → CapCut showed
        # one frame of «מקור» = the other camera; 632 of 658 v3 patches were off the grid)
        F, G, Tn, O = (int(round(x * FPS)) for x in (f, g, a.trim_in, so))
        fr = lambda n: int(round(n * US / FPS))
        seg["source_timerange"] = {"start": fr(F + O), "duration": fr(G - Tn) - fr(F - Tn)}
        seg["target_timerange"] = {"start": fr(F - Tn), "duration": fr(G - Tn) - fr(F - Tn)}
        if cam in zoom:
            k, tx = zoom[cam]
            seg["clip"]["scale"] = {"x": k, "y": k}
            seg["clip"]["transform"] = {"x": tx, "y": 0.0}
        segs.append(seg)
    # the old segments' own extra materials go (each segment had its own copy)
    for k, v in mats.items():
        if isinstance(v, list):
            mats[k] = [e for e in v if not (isinstance(e, dict) and e.get("id") in old_refs)]
    tr["segments"] = segs
    if a.dialogue:
        new = dst / f"דיאלוג {time.strftime('%H%M')}.m4a"
        subprocess.run([FF, "-v", "error", "-y", "-ss", f"{a.trim_in:.6f}", "-t", f"{a.duration:.6f}", "-i", a.dialogue,
                        "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2", str(new)], check=True)
        for m in mats["audios"]:
            m["path"] = str(new); m["name"] = new.name
        for f in dst.glob("ccstudio-audio-*.m4a"):
            f.unlink()
        print("dialogue →", new.name, f"{new.stat().st_size / 1e6:.0f} MB")
    elif a.audio_m4a:
        for m in mats["audios"]:
            p = Path(m["path"])
            if p.suffix.lower() == ".wav" and p.exists() and dst not in p.parents:
                new = dst / (p.stem + ".m4a")
                subprocess.run([FF, "-v", "error", "-y", "-i", str(p), "-c:a", "aac", "-b:a", "320k", "-ar", "48000", str(new)], check=True)
                m["path"] = str(new)
                print("audio →", new.name, f"{new.stat().st_size / 1e6:.0f} MB")
    capcut._atomic_write(dst, d)
    meta_p = dst / "draft_meta_info.json"
    meta = json.loads(meta_p.read_text()); meta_id = capcut._new_id(); now = int(time.time() * US)
    meta.update({"draft_id": meta_id, "draft_name": name, "draft_fold_path": str(dst), "tm_draft_create": now, "tm_draft_modified": now})
    meta_p.write_text(json.dumps(meta, ensure_ascii=False))
    reels._registry_add(dst, meta_id, int(d["duration"]), a.src)
    print(json.dumps({"project": name, "patches": len(segs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
