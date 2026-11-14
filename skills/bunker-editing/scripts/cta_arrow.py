#!/usr/bin/env python3
"""A bouncing down-arrow + Pop at every call to action (Alon, תוכן הבונקר לממומן 24.10.2026: «להכניס חץ עם סאונד של pop
כשאנחנו מניעים לפעולה» — the one place Pop is wanted; elsewhere in Bunker reels it stays banned).

    cta_arrow.py "<project>" --at 7.82,17.9 [--y 0.79] [--h 0.22] [--write]

--at  timeline seconds the arrow lands (put it ~0.06 s before the CTA word); --y the arrow's centre as a fraction of the
canvas height (default: below the captions — 0.79 on 9:16, 0.93 on 16:9); --h its height as a fraction of the canvas
height (default 0.13 on 9:16, 0.11 on 16:9). Track «חץ» (video, above the adjust layer so the grade does not touch
it) + Pop on audio track «SFX». Assets: assets/cta/arrow_down.mov (ProRes 4444, 1.8 s) and pop.wav (leading silence
trimmed, so the hit is on the arrow's first frame). CapCut must be closed.
"""
import argparse, copy, json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402

US = 1_000_000
ASSETS = Path(__file__).resolve().parents[2] / "assets/cta"
AW, AH, ADUR, POP_GAIN = 320, 360, 1.8, 0.7


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("--at", required=True)
    ap.add_argument("--y", type=float); ap.add_argument("--h", type=float); ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    P = capcut.DRAFTS_DIR / a.project
    d = json.loads(capcut._draft_file(P).read_text())
    W, H = d["canvas_config"]["width"], d["canvas_config"]["height"]
    tall = H > W
    yfrac = a.y if a.y is not None else (0.79 if tall else 0.93)
    hfrac = a.h if a.h is not None else (0.13 if tall else 0.11)
    fit = min(W / AW, H / AH)                       # CapCut scale 1 = the clip fitted inside the canvas
    scale = hfrac * H / (AH * fit)
    ty = -(yfrac * H - H / 2) / (H / 2)
    times = [float(x) for x in a.at.split(",") if x.strip()]
    mats = d["materials"]
    donor = next(s for t in d["tracks"] if t["type"] == "video" for s in t["segments"]
                 if (next((m for m in mats["videos"] if m["id"] == s["material_id"]), {}) or {}).get("type") == "video")
    dmat = next(m for m in mats["videos"] if m["id"] == donor["material_id"])
    arrow = P / "ccstudio-cta-arrow.mov"; pop = P / "ccstudio-cta-pop.wav"
    vm = copy.deepcopy(dmat)
    vm.update({"id": capcut._new_id(), "path": str(arrow), "material_name": arrow.name, "width": AW, "height": AH,
               "duration": int(ADUR * US), "has_audio": False, "type": "video"})
    by_list = {e["id"]: k for k, v in mats.items() if isinstance(v, list) for e in v if isinstance(e, dict) and "id" in e}
    vsegs, asegs = [], []
    adonor_mat, adonor_seg, adonor_extras = capcut._audio_donor()
    am = copy.deepcopy(adonor_mat)
    am.update({"id": capcut._new_id(), "path": str(pop), "name": "Pop", "material_name": "Pop",
               "duration": capcut._probe_audio_dur_us(ASSETS / "pop.wav"), "type": "extract_music"})
    fr = lambda t: int(round(round(t * 30) * US / 30))
    for t in times:
        s = copy.deepcopy(donor); s["id"] = capcut._new_id(); s["material_id"] = vm["id"]
        refs = []
        for r in donor.get("extra_material_refs", []):
            lst = by_list.get(r)
            if lst in ("speeds", "canvases", "placeholder_infos", "material_animations", "sound_channel_mappings", "vocal_separations"):
                e = copy.deepcopy(next(x for x in mats[lst] if x["id"] == r)); e["id"] = capcut._new_id(); mats[lst].append(e); refs.append(e["id"])
        s["extra_material_refs"] = refs
        s["target_timerange"] = {"start": fr(t), "duration": fr(ADUR)}
        s["source_timerange"] = {"start": 0, "duration": fr(ADUR)}
        s["clip"] = {"scale": {"x": scale, "y": scale}, "rotation": 0.0, "transform": {"x": 0.0, "y": ty},
                     "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
        s["volume"] = 0.0; s["enable_lut"] = False; s["common_keyframes"] = []; s["keyframe_refs"] = []
        vsegs.append(s)
        x = copy.deepcopy(adonor_seg); xr = []
        for ex in adonor_extras:
            e = copy.deepcopy(ex["material"]); e["id"] = capcut._new_id(); mats.setdefault(ex["list"], []).append(e); xr.append(e["id"])
        x.update({"id": capcut._new_id(), "material_id": am["id"], "extra_material_refs": xr, "volume": POP_GAIN,
                  "target_timerange": {"start": fr(t), "duration": am["duration"]}, "source_timerange": {"start": 0, "duration": am["duration"]}})
        asegs.append(x)
    print(json.dumps({"project": a.project, "canvas": f"{W}x{H}", "arrows": times, "scale": round(scale, 4), "y": round(ty, 3)}, ensure_ascii=False))
    if not a.write:
        print("(יבש — בלי --write לא נכתב כלום)"); return
    if capcut.capcut_running():
        raise SystemExit("⛔ CapCut פתוח — סגור אותו לגמרי ותריץ שוב.")
    shutil.copy2(ASSETS / "arrow_down.mov", arrow); shutil.copy2(ASSETS / "pop.wav", pop)
    mats["videos"].append(vm); mats.setdefault("audios", []).append(am)
    vt = next((t for t in d["tracks"] if t["type"] == "video" and t.get("name") == "חץ"), None)
    if vt is None:
        vt = {"attribute": 0, "flag": 0, "id": capcut._new_id(), "is_default_name": False, "name": "חץ", "segments": [], "type": "video"}
        d["tracks"].append(vt)
    at = next((t for t in d["tracks"] if t["type"] == "audio" and t.get("name") == "SFX"), None)
    if at is None:
        at = {"attribute": 0, "flag": 0, "id": capcut._new_id(), "is_default_name": False, "name": "SFX", "segments": [], "type": "audio"}
        d["tracks"].append(at)
    for tr, new in ((vt, vsegs), (at, asegs)):
        segs = sorted(tr["segments"] + new, key=lambda s: s["target_timerange"]["start"])
        for p, q in zip(segs, segs[1:]):
            if p["target_timerange"]["start"] + p["target_timerange"]["duration"] > q["target_timerange"]["start"]:
                raise SystemExit(f"⛔ חפיפה במסלול «{tr['name']}» ב-{q['target_timerange']['start'] / US:.2f} — חצים קרובים מדי")
        tr["segments"] = segs
    capcut._backup(P); capcut._atomic_write(P, d)
    print("✓ נכתב")


if __name__ == "__main__":
    main()
