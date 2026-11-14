# -*- coding: utf-8 -*-
"""Camera motion driven by the voice: an eased entry punch on every shot, a slow drift in, and sharper
in/out punches on the loud sentence starts — amplitude and speed scaled by how loud the words are.
Alon, 0923 r8: «בקושי יש תנועת קיפריימים של זום אין ואאוט אלא רק קאטים גסים … תנועות חדות יותר כשיש גלי קול
חזקים יותר ולפי התמלול, תמיד easing».

    python reel_motion_energy.py "<project>" [--tracks 0,1] [--captions כתוביות] [--gap 3.5] [--static 2.0]
        [--amp 0.05,0.10] [--t 0.42,0.28] [--entry 0.03 --entry-t 0.5] [--drift 1.3 --ceiling 1.15] [--write]

* Shots on the camera tracks only (--tracks by index; b-roll / titles / logo never move).
* Every shot ≥ --static: entry punch +entry over entry-t, then drift in at --drift %/s.
* Punch candidates = caption cards that start a sentence (after `.?!` or a pause ≥ --pause) or that are
  louder than the 75th percentile; loudness = peak 50 ms RMS in the 0.5 s after the card start, measured on
  the base camera's own audio through the timeline map. Candidates are taken loudest-first with ≥ --gap
  between accepted punches; amplitude / speed interpolate between the quiet and loud ends of --amp / --t.
* Direction alternates in / out inside [scale0, scale0 × ceiling]; the drift stops at the ceiling. The
  face stays put: position is re-solved at every key for an eye line at 0.34 H.
* Every key is CurveInOut. Existing scale / position keys on the shot are replaced; volume / alpha keys kept.
Read-only without --write.
"""
import argparse, json, os, re, subprocess, sys, uuid
import numpy as np
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
US = 1_000_000; FF = str(paths.FFMPEG)
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--tracks", default="0,1"); ap.add_argument("--captions", default="כתוביות")
ap.add_argument("--gap", type=float, default=2.5); ap.add_argument("--static", type=float, default=2.0); ap.add_argument("--pause", type=float, default=0.30)
ap.add_argument("--amp", default="0.05,0.10"); ap.add_argument("--t", default="0.42,0.28"); ap.add_argument("--entry", type=float, default=0.03); ap.add_argument("--entry-t", type=float, default=0.5)
ap.add_argument("--drift", type=float, default=0.6, help="%/s"); ap.add_argument("--ceiling", type=float, default=1.15, help="× the SMALLEST framed scale on the camera tracks — an absolute lid, not per shot"); ap.add_argument("--first-after", type=float, default=0.8); ap.add_argument("--last-before", type=float, default=0.5)
ap.add_argument("--audio", default="", help="voice file to measure instead of the camera copy (same time base) — the PRE-compression audio keeps the dynamics")
ap.add_argument("--write", action="store_true"); A = ap.parse_args()
amp0, amp1 = (float(x) for x in A.amp.split(",")); tq, tl_ = (float(x) for x in A.t.split(","))
D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR)
vm = {m["id"]: m for m in d["materials"]["videos"]}; tm = {m["id"]: m for m in d["materials"]["texts"]}
def resolve(p): return str(D / p.split("_##/", 1)[1]) if p.startswith("##_draftpath_placeholder") else p
tracks = [d["tracks"][int(i)] for i in A.tracks.split(",")]; base = tracks[0]
# --- voice envelope on the timeline, from the base camera's own audio ---------------------------------------
HOP = 0.05; env = {}
for s in base["segments"]:
    m = vm[s["material_id"]]
    if m.get("type") != "video" or not m.get("path"): continue
    src0, dur = s["source_timerange"]["start"] / US, s["source_timerange"]["duration"] / US; t0 = s["target_timerange"]["start"] / US
    r = subprocess.run([FF, "-v", "error", "-ss", f"{src0:.3f}", "-t", f"{dur:.3f}", "-i", A.audio or resolve(m["path"]), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.float32); n = int(HOP * 16000)
    for i in range(0, len(a) - n, n):
        env[round(t0 + i / 16000, 2)] = 20 * np.log10(np.sqrt(np.mean(a[i:i + n] ** 2)) + 1e-9)
def loud(t, w=0.5):
    """emphasis: the peak 50 ms RMS after the word minus the local median (±1.5 s) — a level-free measure of a stressed word"""
    peak = max((v for k, v in env.items() if t <= k < t + w), default=-90.0); ctx = [v for k, v in env.items() if t - 1.5 <= k < t + 1.5 and v > -50]
    return peak - (float(np.median(ctx)) if ctx else peak)
# --- candidates from the caption cards ------------------------------------------------------------------------
cap = next(t for t in d["tracks"] if t.get("name") == A.captions)
cards = sorted(((s["target_timerange"]["start"] / US, (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / US, json.loads(tm[s["material_id"]]["content"])["text"]) for s in cap["segments"]), key=lambda c: c[0])
cands = []; prev_end, prev_txt = -9, "."
for st, en, txt in cards:
    sent = (st - prev_end >= A.pause) or prev_txt.strip()[-1:] in ".?!"
    cands.append({"t": st, "db": loud(st), "sent": sent, "txt": txt}); prev_end, prev_txt = en, txt
dbs = np.array([c["db"] for c in cands]); p25, p75, p95 = np.percentile(dbs, [25, 75, 95])
pool = [c for c in cands if c["sent"] or c["db"] >= p75]
chosen = []
for c in sorted(pool, key=lambda c: -c["db"]):
    if all(abs(c["t"] - o["t"]) >= A.gap for o in chosen): chosen.append(c)
chosen.sort(key=lambda c: c["t"])
def strength(db): return float(np.clip((db - p25) / max(1e-6, p95 - p25), 0, 1))
# --- keys ------------------------------------------------------------------------------------------------------
def kf(t, v): return {"id": str(uuid.uuid4()).upper(), "curveType": "CurveInOut", "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def group(prop, keys): return {"id": str(uuid.uuid4()).upper(), "material_id": "", "property_type": prop, "keyframe_list": keys}
n_punch = n_entry = n_still = 0; amps = []; maxsc = 0
SC_MIN = min(s["clip"]["scale"]["x"] for tk in tracks for s in tk["segments"] if vm[s["material_id"]].get("type") == "video"); HI = SC_MIN * A.ceiling
for ti, tk in enumerate(tracks):
    for s in sorted(tk["segments"], key=lambda s: s["target_timerange"]["start"]):
        m = vm[s["material_id"]]
        if m.get("type") != "video" or not m.get("path"): continue
        sc0 = s["clip"]["scale"]["x"]; x0 = s["clip"]["transform"]["x"]; y0 = s["clip"]["transform"]["y"]
        src0, dur = s["source_timerange"]["start"], s["source_timerange"]["duration"]; t0 = s["target_timerange"]["start"] / US; L = dur / US
        lo, hi = sc0, HI
        def xy(v): k = v / sc0; return x0 * k, y0 * k + (1 - k) * (960 - 0.34 * 1920) / 960
        keys = [(0.0, sc0)]
        if L < A.static: n_still += 1
        else:
            v = min(hi, sc0 * (1 + A.entry)); keys.append((A.entry_t, v)); n_entry += 1; last_t, last_v, direction = A.entry_t, v, +1
            gate = A.entry_t + 0.8   # the first punch may come 0.8 s after the entry settles; later ones keep --gap
            for c in chosen:
                tl = c["t"] - t0
                if tl < max(A.first_after, gate) or tl > L - A.last_before: continue
                v_pre = min(hi, last_v * (1 + A.drift / 100 * (tl - last_t)))
                st_ = strength(c["db"]); amp = amp0 + (amp1 - amp0) * st_; T = tq + (tl_ - tq) * st_
                direction = +1 if v_pre * (1 + amp) <= hi else -1
                v_post = max(lo, min(hi, v_pre * (1 + direction * amp)))
                keys += [(tl, v_pre), (tl + T, v_post)]; last_t, last_v = tl + T, v_post; gate = tl + T + A.gap; n_punch += 1; amps.append(direction * amp)
            keys.append((L, min(hi, last_v * (1 + A.drift / 100 * (L - last_t)))))
        maxsc = max(maxsc, max(v for _, v in keys))
        seen = {}
        for t, v in keys: seen[snap(t * US)] = v
        pts = sorted(seen.items())
        s["common_keyframes"] = [g for g in s.get("common_keyframes", []) if g["property_type"] not in ("KFTypeScaleX", "KFTypeScaleY", "KFTypePositionX", "KFTypePositionY")]
        if len(pts) > 1:
            s["common_keyframes"] += [group("KFTypeScaleX", [kf(src0 + t, v) for t, v in pts]), group("KFTypeScaleY", [kf(src0 + t, v) for t, v in pts]),
                                      group("KFTypePositionX", [kf(src0 + t, xy(v)[0]) for t, v in pts]), group("KFTypePositionY", [kf(src0 + t, xy(v)[1]) for t, v in pts])]
        s["clip"]["scale"] = {"x": sc0, "y": sc0}; s["clip"]["transform"] = {"x": x0, "y": y0}
dur_min = d["duration"] / US / 60
print(f"envelope {len(env)} bins | candidates {len(cands)} (sentence starts {sum(c['sent'] for c in cands)}, loud≥p75 {sum(c['db'] >= p75 for c in cands)}) → punches {n_punch} ({n_punch / dur_min:.1f}/min), in {sum(a > 0 for a in amps)} / out {sum(a < 0 for a in amps)}")
print(f"entries {n_entry} | still shots {n_still} | amp {min(map(abs, amps)):.3f}–{max(map(abs, amps)):.3f} | max scale {maxsc:.2f} (ceiling ×{A.ceiling}) | loudness p25/p75/p95 {p25:.1f}/{p75:.1f}/{p95:.1f} dB emphasis")
ids = [k["id"] for tk in tracks for s in tk["segments"] for g in s.get("common_keyframes", []) for k in g["keyframe_list"]]; assert len(ids) == len(set(ids))
for g in (g for tk in tracks for s in tk["segments"] for g in s.get("common_keyframes", [])):
    ts = [k["time_offset"] for k in g["keyframe_list"]]; assert ts == sorted(ts) and len(ts) == len(set(ts)), "unsorted/duplicate key times"
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
