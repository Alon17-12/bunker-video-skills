#!/usr/bin/env python3
"""Mic dialogue into a project Alon cut himself (תוכן הבונקר לממומן, 24.10.2026: two camera layers that each play the
camera's own sound = the RØDECaster mix twice → +6 dB and a comb filter).

    project_dialogue.py "<project>" <from_s> <to_s> <dialogue.wav> --live-offset 0.0173 [--write]

Inside [from, to] on the timeline: every footage segment (video, real file) gets volume 0, and the audio track
«דיבור» gets one segment per clip of the bottom footage track — same target range, source = the clip's camera time
+ live-offset (the dialogue master runs on the Live-Mix clock; measure it: sync_offsets.py cam1.mp4 Live-Mix.wav).
All on ONE lane (no overlaps: Alon, «למה הפרדת את הקטע קול הזה מציר הזמן הרגיל?»), 15 ms fades at each cut.
The dialogue file is copied into the draft folder (CapCut's sandbox cannot read the SSD). CapCut must be closed.
"""
import argparse, copy, json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402

US = 1_000_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("t_from", type=float); ap.add_argument("t_to", type=float); ap.add_argument("dialogue")
    ap.add_argument("--live-offset", type=float, required=True); ap.add_argument("--bottom", type=int, default=0)
    ap.add_argument("--name", default="דיבור"); ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    P = capcut.DRAFTS_DIR / a.project
    d = json.loads(capcut._draft_file(P).read_text())
    mats = d["materials"]
    vids = {m["id"]: m for m in mats.get("videos", [])}
    A, B = int(a.t_from * US), int(a.t_to * US)
    inside = lambda s: s["target_timerange"]["start"] >= A - 1000 and s["target_timerange"]["start"] + s["target_timerange"]["duration"] <= B + 1000
    real = lambda s: (vids.get(s["material_id"]) or {}).get("type") == "video" and Path((vids.get(s["material_id"]) or {}).get("path", "")).exists()
    muted = 0
    for t in d["tracks"]:
        if t["type"] != "video":
            continue
        for s in t["segments"]:
            if inside(s) and real(s) and s.get("volume", 1.0) != 0.0:
                s["volume"] = 0.0; muted += 1
    vtracks = [t for t in d["tracks"] if t["type"] == "video"]
    clips = sorted((s for s in vtracks[a.bottom]["segments"] if inside(s) and real(s)), key=lambda s: s["target_timerange"]["start"])
    # the one dialogue track
    tr = next((t for t in d["tracks"] if t["type"] == "audio" and t.get("name") == a.name), None)
    donor_mat, donor_seg, donor_extras = capcut._audio_donor()
    src = Path(a.dialogue)
    # one file per take: every session's master is called «דיאלוג.wav» — a name from the stem alone made all 7 videos of
    # תוכן הבונקר לממומן play the first take's 29 s file (25.10.2026)
    import zlib
    dest = P / f"ccstudio-dialogue-{zlib.crc32(str(src.resolve()).encode()) % 100000:05d}.wav"
    mat = next((m for m in mats.get("audios", []) if m.get("path") == str(dest)), None)
    if mat is None:
        mat = copy.deepcopy(donor_mat)
        mat.update({"id": capcut._new_id(), "path": str(dest), "name": dest.stem, "material_name": dest.stem,
                    "duration": capcut._probe_audio_dur_us(src), "type": "extract_music"})
    segs = []
    for c in clips:
        s = copy.deepcopy(donor_seg)
        refs = []
        for ex in donor_extras:
            e = copy.deepcopy(ex["material"]); e["id"] = capcut._new_id(); mats.setdefault(ex["list"], []).append(e); refs.append(e["id"])
        tt = dict(c["target_timerange"])
        s.update({"id": capcut._new_id(), "material_id": mat["id"], "extra_material_refs": refs, "volume": 1.0,
                  "target_timerange": tt,
                  "source_timerange": {"start": max(0, c["source_timerange"]["start"] + int(round(a.live_offset * US))), "duration": tt["duration"]}})
        s["fade"] = None
        segs.append(s)
    if tr:
        clash = [x for x in tr["segments"] if x["target_timerange"]["start"] < B - 40_000 and x["target_timerange"]["start"] + x["target_timerange"]["duration"] > A + 40_000]
        if clash:
            raise SystemExit(f"⛔ במסלול «{a.name}» כבר יש {len(clash)} מקטעים בטווח — לא כותב מעליהם")
    print(json.dumps({"range": [a.t_from, a.t_to], "muted_video_segments": muted, "dialogue_segments": len(segs),
                      "clips": [[round(c['target_timerange']['start'] / US, 3), round(c['source_timerange']['start'] / US, 3)] for c in clips]}, ensure_ascii=False))
    if not a.write:
        print("(יבש — בלי --write לא נכתב כלום)"); return
    if capcut.capcut_running():
        raise SystemExit("⛔ CapCut פתוח — סגור אותו לגמרי ותריץ שוב.")
    if not dest.exists():
        shutil.copy2(src, dest)
    if not any(m["id"] == mat["id"] for m in mats.get("audios", [])):
        mats.setdefault("audios", []).append(mat)
    if tr is None:
        tr = {"attribute": 0, "flag": 0, "id": capcut._new_id(), "is_default_name": False, "name": a.name, "segments": [], "type": "audio"}
        d["tracks"].append(tr)
    tr["segments"] = sorted(tr["segments"] + segs, key=lambda s: s["target_timerange"]["start"])
    capcut._backup(P)
    capcut._atomic_write(P, d)
    print("✓ נכתב")


if __name__ == "__main__":
    main()
