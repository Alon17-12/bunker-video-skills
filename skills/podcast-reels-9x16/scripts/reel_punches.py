# -*- coding: utf-8 -*-
"""Punches instead of drift, for a reel that is mostly one man talking to one camera.

    python reel_punches.py "<project>" --words <reel_captions words.json> [--gap 5] [--amp 0.08] [--t 0.35] [--write]

Every footage shot on both camera layers holds STILL at its framed scale and, on sentence starts
(a pause ≥ --pause before the word, on the shot's OWN mic) spaced ≥ --gap apart, snaps between two
levels — s and s·(1+amp) — over --t seconds with CurveInOut. Position is re-solved at each keyframe
so the face stays where the framing put it (a scale step about the canvas centre would otherwise
slide the eyes). Each reel's first shot opens with a 1 s zoom-out from +5 %. Shots under --static
do not move (a reaction cut is already a movement). Read-only without --write.

Why this and not a slow push-in: Alon on 0910 — "פחות ריחוף, יותר תנועות שתופסות את העין"; on the
reference creators a hold never runs past ~7 s without a cut or a punch; and this client asked for
FEWER camera jumps ("המצלמה יותר מדי קופצת ביני לבינו"), so the rhythm comes from the frame, not
from cutting to the listener.
"""
import argparse, json, os, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--words", required=True)
ap.add_argument("--gap", type=float, default=4.5); ap.add_argument("--amp", type=float, default=0.08); ap.add_argument("--t", type=float, default=0.35)
ap.add_argument("--pause", type=float, default=0.45, help="a gap this long before a word makes it a sentence start")
ap.add_argument("--static", type=float, default=2.5); ap.add_argument("--intro", type=float, default=0.05); ap.add_argument("--intro-s", type=float, default=1.0)
ap.add_argument("--from", dest="t_from", type=float, default=None, help="only footage segments starting at/after this project second (earlier reels keep their keyframes)")
ap.add_argument("--first-after", type=float, default=2.0); ap.add_argument("--last-before", type=float, default=1.2); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project
d = json.loads((D / "draft_info.json").read_text()); FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR)
vm = {m["id"]: m for m in d["materials"]["videos"]}
W = sorted(json.load(open(A.words)), key=lambda w: w["start_s"])
import re
def cam_of(path): m = re.search(r"cam\s*(\d)", os.path.basename(path)); return int(m.group(1)) if m else 0
# sentence starts per mic: first word, and any word after a pause ≥ --pause on the same mic
starts = {1: [], 2: []}
last_end = {1: -9, 2: -9}; prev_txt = {1: ".", 2: "."}
for w in W:
    m = w.get("mic", 2)
    if w["start_s"] - last_end[m] >= A.pause or prev_txt[m][-1:] in ".?!": starts[m].append(w["start_s"])   # a pause, or the transcriber's sentence end
    last_end[m] = max(last_end[m], w["end_s"]); prev_txt[m] = w["text"]
def kf(t, v, curve="CurveInOut"): return {"id": str(uuid.uuid4()).upper(), "curveType": curve, "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def group(prop, keys): return {"id": str(uuid.uuid4()).upper(), "material_id": "", "property_type": prop, "keyframe_list": keys}
vt = [t for t in d["tracks"] if t["type"] == "video" and t["segments"]]
base = vt[0]; reel_starts = set(); prev = None
for s in sorted(base["segments"], key=lambda s: s["target_timerange"]["start"]):          # a reel starts on the first footage piece after a card (or at 0) —
    if vm[s["material_id"]].get("type") == "video" and (prev is None or vm[prev["material_id"]].get("type") == "photo"): reel_starts.add(s["target_timerange"]["start"])
    prev = s                                                                                # not on every piece a silence cut left behind (0923: 21 intros)
n_punch = n_still = n_intro = 0
for tk in vt:
    for s in tk["segments"]:
        m = vm[s["material_id"]]
        if m.get("type") != "video" or not m.get("path"): continue
        if A.t_from is not None and s["target_timerange"]["start"] / US < A.t_from - 0.01: continue
        cam = cam_of(m["path"]); sc0 = s["clip"]["scale"]["x"]; x0 = s["clip"]["transform"]["x"]; y0 = s["clip"]["transform"]["y"]
        src0, dur = s["source_timerange"]["start"], s["source_timerange"]["duration"]; t0 = s["target_timerange"]["start"]; L = dur / US
        # the face's canvas position at the framed scale is the invariant: face_px = 540 + 540x + 540·s·(2fx−1) — solve fx from
        # the framing, then re-solve x (and y, via the same identity on the other axis) at every new scale
        fx = ((0.5 * 1080 - 540 - 540 * x0) / (540 * sc0) + 1) / 2 if False else None
        def xy_at(s_new):                                   # keep the point that sits at canvas centre-ish (the face) fixed
            k = s_new / sc0; return x0 * k - (k - 1) * 0.0, y0 * k - (k - 1) * 0.0   # placeholder, refined below
        # exact: the canvas point P = (540 + 540x0 + 540·sc0·u, 960 − 960y0 + 607.5·sc0·v) for source offsets (u,v); keep the
        # face point (u*,v*) fixed. We do not know (u*,v*) here, so keep the canvas CENTRE fixed instead: x' = x0 + (1 − k)·(face offset)
        # ≈ scale about the face by moving x,y proportionally: x' = x0·k + (1 − k)·cx_face/540 …  with cx_face at canvas centre (0.50 W)
        # and eyes at 0.34 H (frame_shots), so: x' = x0·k, y' = y0·k + (1 − k)·(960 − 0.34·1920)/960 → both derived from the framing.
        def xy(s_new):
            k = s_new / sc0; return x0 * k, y0 * k + (1 - k) * (960 - 0.34 * 1920) / 960
        keys = []  # (t_local_s, scale)
        hi = sc0 * (1 + A.amp); lo = sc0; cur = lo
        if t0 in reel_starts and tk is base:
            keys += [(0.0, sc0 * (1 + A.intro)), (A.intro_s, sc0)]; last = A.intro_s; n_intro += 1
        else: keys.append((0.0, sc0)); last = 0.0
        if L >= A.static:
            for tw in starts.get(cam, []):
                tl = tw - t0 / US
                if tl < max(A.first_after, last + A.gap) or tl > L - A.last_before: continue
                nxt = hi if cur == lo else lo
                keys += [(tl, cur), (tl + A.t, nxt)]; cur = nxt; last = tl + A.t; n_punch += 1
        else: n_still += 1
        keys.append((L, cur))
        sx = [kf(src0 + snap(int(t * US)), v) for t, v in keys]; sy = [kf(src0 + snap(int(t * US)), v) for t, v in keys]
        px = [kf(src0 + snap(int(t * US)), xy(v)[0]) for t, v in keys]; py = [kf(src0 + snap(int(t * US)), xy(v)[1]) for t, v in keys]
        s["common_keyframes"] = [g for g in s.get("common_keyframes", []) if g["property_type"] not in ("KFTypeScaleX", "KFTypeScaleY", "KFTypePositionX", "KFTypePositionY")]
        s["common_keyframes"] += [group("KFTypeScaleX", sx), group("KFTypeScaleY", sy), group("KFTypePositionX", px), group("KFTypePositionY", py)]
        s["clip"]["scale"] = {"x": keys[0][1], "y": keys[0][1]}; s["clip"]["transform"] = {"x": xy(keys[0][1])[0], "y": xy(keys[0][1])[1]}
        print(f"  {'base' if tk is base else 'over'} cam{cam} {t0/US:7.2f} +{L:5.1f}s  punches {max(0, (len(keys) - 2 - (2 if t0 in reel_starts and tk is base else 0)) // 2)}")
print(f"punches {n_punch} | intro zoom-outs {n_intro} | still shots {n_still}")
ids = [k["id"] for tk in vt for s in tk["segments"] for g in s.get("common_keyframes", []) for k in g["keyframe_list"]]; assert len(ids) == len(set(ids))
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
