"""0910 round 9 — B-roll layer (Seedance 2.5 clips via Higgsfield) + a «27 ספטמבר» calendar badge.
One full-frame 9:16 clip per section on the key visual sentence, muted, on a video track that sits
right above the adjust layer and BELOW every text/logo/arrow track (so nothing covers the captions,
the logo or the CTA). Hard cut in with a quick 1.08→1.0 settle, hard cut out, a whoosh on the cut.
The calendar badge is a photo overlay (like the CTA arrow) that pops in beside the head on three
date mentions, for exactly the caption's duration. Idempotent: tears its own tracks down first."""
import sys, os, json, copy, shutil
from pathlib import Path
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
SP = Path(__file__).parent; NAME = "0910"; US = 1_000_000; DRY = bool(os.environ.get("DRY"))
SFX = os.path.expanduser("~/VideoAssets/סאונד/SFX/")
WHOOSH, WHOOSH_VOL = SFX + "Woosh #2.WAV", 0.45
POP, POP_VOL = SFX + "Pop.mp3", 0.5
# (clip file, timeline start, duration, source offset)  — one per section, on the sentence it illustrates
BROLL = [   # (file, start, dur, source offset, mode) — literal scenes of the persona, one per key sentence
 ("c1.mp4",    3.40, 4.0, 0.3, "full"),  # worried editor with bills — «ימכור אותם שנים ואתם קיבלתם תשלום פעם אחת»
 ("c2.mp4",    9.55, 4.0, 0.3, "full"),  # relaxed editor, payments keep arriving — «להמשיך להכניס אלפי שקלים מדי חודש»
 ("c3.mp4",   26.75, 3.8, 0.4, "full"),  # social manager hunting clients — «ואתם שוב צריכים לחפש לקוחות חדשים»
 ("c4.mp4",   61.65, 4.2, 0.3, "full"),  # freelancer welcomed into the startup — «פותחים דלת שבדרך כלל סגורה»
 ("c5.mp4",   92.10, 3.9, 0.4, "full"),  # earning from growth on a balcony — «הולכים להרוויח מהצמיחה. כל חודש»
 ("c6.mp4",   98.20, 4.0, 0.3, "full"),  # video call with the startup team — «שותפים להצלחה של סטארט-אפ ישראלי»
 ("c7.mp4",  128.65, 4.0, 0.3, "full"),  # closes the laptop, phone keeps paying — «ואין תקרה למספר»
 ("c8.mp4",  141.95, 4.0, 0.3, "full"),  # vacation ruined by client replies — «יצאתם לחופש בלי דאגות לגבי פרויקט חדש»
 ("s6.mp4",  153.75, 4.0, 0.3, "full"),  # hammock, phone lights up — «שמגיע גם בחגים, גם כשאתם בחו״ל»
 ("c9.mp4",  177.20, 4.0, 0.3, "full"),  # freelancers watching the webinar — «חושף משהו ראשון מסוגו בארץ»
 ("c10.mp4", 184.90, 4.0, 0.3, "full"),  # new chapter, out the door — «יכול לשנות לחלק מכם את השנה הבאה»
 ("c11.mp4", 203.20, 3.9, 0.3, "full"),  # reviewing monthly income, calm — «הסוג הראשון היה בוובינר»
 ("s12.mp4", 207.60, 4.0, 0.3, "full"),  # scrolling the feed — «יראה את הסרטון הזה שוב בפיד»
]
PIP_SCALE, PIP_X, PIP_Y = 0.34, 0.66, 0.60
CAL_MIN = 2.2   # the badge shows on EVERY «ב-27 בספטמבר» card, at least this long, cut at the next full-frame b-roll
CAL_X, CAL_Y, CAL_SCALE = 0.62, 0.50, 0.30
pid = None if DRY else capcut._capcut_pid()
if pid and f"{capcut.DRAFTS_DIR/NAME}/" in capcut._capcut_open_files(pid): raise SystemExit("draft open in CapCut")
if not DRY and capcut.capcut_running(): raise SystemExit("CapCut running")
D = capcut.DRAFTS_DIR / NAME; d = capcut.load_draft(NAME); mats = d["materials"]
byid = {}
for k, v in mats.items():
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict) and "id" in m: byid[m["id"]] = (k, m)
def extras_of(seg): return [{"list": byid[r][0], "material": byid[r][1]} for r in seg["extra_material_refs"] if r in byid]
# ---- tear down
gone = [t for t in d["tracks"] if t.get("name") in ("broll", "calendar", "sfx broll", "sfx broll pop")]
# the arrow's Pop track was lost when a lane SHARED its audio material and the lane's tear-down deleted it (CapCut then
# dropped both tracks on load). Restore it verbatim from the frozen caption base, with the material and its extras.
if not any(t.get("name") == "sfx arrow" for t in d["tracks"]):
    base = json.load(open(D / "draft_info.caption-base-v4.json", encoding="utf-8")); bb = {}
    for k, v in base["materials"].items():
        if isinstance(v, list):
            for m in v:
                if isinstance(m, dict) and "id" in m: bb[m["id"]] = (k, m)
    src_t = next(t for t in base["tracks"] if t.get("name") == "sfx arrow"); t_new = copy.deepcopy(src_t)
    for sg in t_new["segments"]:
        for r in [sg["material_id"]] + sg.get("extra_material_refs", []):
            if r in bb and r not in byid: mats.setdefault(bb[r][0], []).append(copy.deepcopy(bb[r][1])); byid[r] = (bb[r][0], mats[bb[r][0]][-1])
    d["tracks"].append(t_new); print("restored 'sfx arrow' from the caption base:", len(t_new["segments"]), "pops")
ids = {s["material_id"] for t in gone for s in t["segments"]}; refs = {r for t in gone for s in t["segments"] for r in s.get("extra_material_refs", [])}
for k in list(mats):
    if isinstance(mats[k], list): mats[k] = [m for m in mats[k] if not (isinstance(m, dict) and (m.get("id") in ids or m.get("id") in refs))]
d["tracks"] = [t for t in d["tracks"] if t not in gone]
def kf(t, v, curve="Line"):
    return {"id": capcut._new_id(), "curveType": curve, "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def group(prop, keys): return {"id": capcut._new_id(), "material_id": "", "property_type": prop, "keyframe_list": keys}
maxri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
main_seg = next(s for s in d["tracks"][0]["segments"] if byid[s["material_id"]][1].get("type") != "photo"); main_mat = byid[main_seg["material_id"]][1]
arrow_seg = next(t for t in d["tracks"] if t.get("name") == "arrow cta")["segments"][0]; arrow_mat = byid[arrow_seg["material_id"]][1]
# ---- b-roll track
broll = {"attribute": 0, "flag": 0, "id": capcut._new_id(), "is_default_name": False, "name": "broll", "segments": [], "type": "video"}
for fn, t0, dur, off, mode in BROLL:
    if not (SP / "broll" / fn).exists(): print("  ⚠️ missing clip, skipped:", fn); continue
    dest = D / f"ccstudio-broll-{fn}"; shutil.copy(SP / "broll" / fn, dest)
    m = copy.deepcopy(main_mat); m.update({"id": capcut._new_id(), "path": str(dest), "material_name": dest.name, "duration": 5_041_667, "width": 1080, "height": 1920, "has_audio": False,
                                          "local_material_id": "", "material_id": "", "origin_material_id": "", "video_algorithm": {**m["video_algorithm"], "time_range": {"start": 0, "duration": 0}}})
    y0c, y1c = (0.21875, 0.78125) if mode == "pip" else (0.0, 1.0)   # pip = the middle square of the 9:16 clip
    m["crop"] = {"upper_left_x": 0.0, "upper_left_y": y0c, "upper_right_x": 1.0, "upper_right_y": y0c, "lower_left_x": 0.0, "lower_left_y": y1c, "lower_right_x": 1.0, "lower_right_y": y1c}
    mats["videos"].append(m)
    seg = copy.deepcopy(main_seg); maxri += 1
    seg.update({"id": capcut._new_id(), "material_id": m["id"], "extra_material_refs": capcut._clone_extras(mats, [e for e in extras_of(main_seg) if e["list"] != "material_animations"]),
                "render_index": maxri, "speed": 1.0, "volume": 0.0, "last_nonzero_volume": 1.0, "keyframe_refs": [],
                "target_timerange": {"start": int(t0 * US), "duration": int(dur * US)}, "source_timerange": {"start": int(off * US), "duration": int(dur * US)}})
    o, e = int(off * US), int((off + dur) * US)
    if mode == "full":   # settle in, then a quick punch INTO the clip right before the cut back to the face
        sc = [kf(o, 1.08, "CurveOut"), kf(o + int(0.5 * US), 1.0, "CurveOut"), kf(e - int(0.25 * US), 1.0, "CurveIn"), kf(e, 1.12, "CurveIn")]; px, py = 0.0, 0.0
    else:                # inset pops in beside the head and pops out
        sc = [kf(o, 0.004, "CurveInOut"), kf(o + int(0.25 * US), PIP_SCALE * 1.12, "CurveInOut"), kf(o + int(0.38 * US), PIP_SCALE, "CurveInOut"), kf(e - int(0.2 * US), PIP_SCALE, "CurveIn"), kf(e, 0.004, "CurveIn")]; px, py = PIP_X, PIP_Y
    seg["clip"] = {"scale": {"x": sc[0]["values"][0], "y": sc[0]["values"][0]}, "rotation": 0.0, "transform": {"x": px, "y": py}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    seg["common_keyframes"] = [group("KFTypeScaleX", sc), group("KFTypeScaleY", [dict(k, id=capcut._new_id()) for k in sc]),
                               group("KFTypePositionX", [kf(o, px), kf(e, px)]), group("KFTypePositionY", [kf(o, py), kf(e, py)]), group("KFTypeRotation", [kf(o, 0.0), kf(e, 0.0)])]
    broll["segments"].append(seg)
adj = next(i for i, t in enumerate(d["tracks"]) if t["type"] == "adjust")
d["tracks"].insert(adj + 1, broll)
# ---- music ducks 3 dB under every full-frame b-roll (volume keyframes on the bed pieces; idempotent)
DUCK, RAMP_IN, RAMP_OUT = 0.71, 0.3, 0.4
beds = next(t for t in d["tracks"] if t.get("name") == "music bed")
for sg in beds["segments"]:
    sg["common_keyframes"] = [g for g in sg.get("common_keyframes", []) if g["property_type"] != "KFTypeVolume"]
    ta = sg["target_timerange"]["start"] / US; tb = ta + sg["target_timerange"]["duration"] / US; src0 = sg["source_timerange"]["start"]; v = sg["volume"]
    keys = []
    for _, t0, dur, _, mode in BROLL:
        if mode != "full" or t0 + dur <= ta or t0 >= tb: continue
        for t, val in ((t0 - 0.05, v), (t0 - 0.05 + RAMP_IN, v * DUCK), (t0 + dur, v * DUCK), (t0 + dur + RAMP_OUT, v)):
            t = min(max(t, ta), tb); keys.append(kf(src0 + int((t - ta) * US), val))
    if keys:
        keys.sort(key=lambda k: k["time_offset"]); sg["common_keyframes"].append(group("KFTypeVolume", keys))
print("music ducks:", sum(1 for sg in beds["segments"] for g in sg["common_keyframes"] if g["property_type"] == "KFTypeVolume"), "bed pieces with volume keys")
# ---- SFX: whoosh on every b-roll cut, pop on every badge
donor_amat, donor_aseg, donor_aextras = capcut._audio_donor()
def audio_track(name, src, dest_name, hits, vol):
    dest = D / dest_name; shutil.copy(src, dest); adur = capcut._probe_audio_dur_us(dest)
    am = copy.deepcopy(donor_amat); am.update({"id": capcut._new_id(), "path": str(dest), "name": dest_name, "material_name": dest_name, "duration": adur, "type": "extract_music"}); mats["audios"].append(am)
    segs = []
    for t in sorted(hits):
        seg = copy.deepcopy(donor_aseg)
        seg.update({"id": capcut._new_id(), "material_id": am["id"], "extra_material_refs": capcut._clone_extras(mats, donor_aextras), "volume": vol, "last_nonzero_volume": vol, "speed": 1.0,
                    "target_timerange": {"start": int(t * US), "duration": adur}, "source_timerange": {"start": 0, "duration": adur}, "common_keyframes": [], "keyframe_refs": [], "render_index": 0})
        segs.append(seg)
    d["tracks"].append({"attribute": 0, "flag": 0, "id": capcut._new_id(), "is_default_name": False, "name": name, "segments": segs, "type": "audio"})
audio_track("sfx broll", WHOOSH, "ccstudio-audio-woosh2.wav", [t0 - 0.12 for _, t0, _, _, mode in BROLL if mode == "full"], WHOOSH_VOL)
print(f"broll {len(BROLL)} clips | tracks now {[t.get('name') for t in d['tracks']]}")
if DRY: print("DRY RUN — nothing written")
else: capcut._backup(D); capcut._atomic_write(D, d); print("written")
