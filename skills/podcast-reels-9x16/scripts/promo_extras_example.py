"""0910 round 4 — (1) Latin brand-name size 18→16; (2) a music bed per section (the 8 runs of
footage between the white cards), picked by mood/tempo, gain set from measured loudness so
every bed sits ~16 dB under the speech, 0.8s in / 1.2s out fades; (3) a white down-arrow that
pops in (scale overshoot, CurveInOut) with a bob, plus a Pop SFX, every time Eyal says
"…כאן למטה"."""
import os
import sys, json, copy, shutil, subprocess
from pathlib import Path
import numpy as np
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
SP = Path(__file__).parent; NAME = "0910"; US = 1_000_000
FF = os.path.expanduser("~/ffmpeg-bin/ffmpeg"); A = "~/VideoAssets"
MUSIC = A + "/סאונד/מוזיקת רקע"; SFX = A + "/סאונד/SFX/Pop.mp3"; ARROW = A + "/גרפיקות ואנימציות/חץ לבן.png"
BED_UNDER_SPEECH_DB = 16; FADE_IN, FADE_OUT = 0.8, 1.2
PICKS = [  # (file, why) — one per section, in order
    ("follow-your-inspiration-corporate-204845.mp3", "עורכי וידאו / קורסים — corporate מעורר, 120bpm"),
    ("smile-hiphop-music-183706.mp3", "מנהלות סושיאל / ריטיינר — היפ-הופ קליל, 109bpm"),
    ("magic-inspiration-201208.mp3", "סטארט-אפ פותח דלת — inspiration, 128bpm"),
    ("unlock-me-149058.mp3", "קטגוריה שלישית / 'נשמע מוזר' — סקרנות, 73bpm"),
    ("the-moment-of-inspiration-211761.mp3", "המודל החדש / הכנסה — רגוע ומעורר, 64bpm"),
    ("aurora-207570.mp3", "חופש בלי דאגות — אמביינט רגוע, 69bpm"),
    ("order-99518.mp3", "'זאת לא מודעה' — רציני, 77bpm"),
    ("heroes-among-us-dramatic-background-music-for-video-vlog-1-minute-203757.mp3", "שני סוגי אנשים בעוד שנה — דרמטי, 77bpm"),
]
CTA = [16.44, 44.08, 77.21, 106.30, 134.31, 162.24, 192.94, 218.47]   # "…כאן למטה" phrase starts (words cache)
pid = capcut._capcut_pid()
if pid and f"{capcut.DRAFTS_DIR/NAME}/" in capcut._capcut_open_files(pid): raise SystemExit("draft open in CapCut")
if capcut.capcut_running(): raise SystemExit("CapCut running")
D = capcut.DRAFTS_DIR / NAME; d = capcut.load_draft(NAME); mats = d["materials"]; vm = {m["id"]: m for m in mats["videos"]}
def rms_db(path, ss=0, t=20):
    raw = subprocess.run([FF, "-v", "error", "-ss", str(ss), "-t", str(t), "-i", path, "-ac", "1", "-ar", "8000", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32); return 20*np.log10(np.sqrt((x**2).mean()) + 1e-9)
def kf(t, v, curve="Line"):
    return {"id": capcut._new_id(), "curveType": curve, "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def group(prop, keys): return {"id": capcut._new_id(), "material_id": "", "property_type": prop, "keyframe_list": keys}
maxri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])

# ---- 1. brand name size
tm = {m["id"]: m for m in mats["texts"]}; n_font = 0
for m in mats["texts"]:
    c = json.loads(m["content"])
    if len(c["styles"]) > 1:
        for st in c["styles"]:
            if "Heebo" in st["font"]["path"]: st["size"] = 16.0; n_font += 1
        m["content"] = json.dumps(c, ensure_ascii=False)
print(f"latin size → 16 on {n_font} ranges")

# ---- sections = runs of footage
pieces = sorted(d["tracks"][0]["segments"], key=lambda s: s["target_timerange"]["start"]); runs = []
for s in pieces:
    st, du = s["target_timerange"]["start"], s["target_timerange"]["duration"]
    if vm[s["material_id"]].get("type") == "photo": continue
    if runs and runs[-1][1] == st: runs[-1][1] = st + du
    else: runs.append([st, st + du])
assert len(runs) == len(PICKS) == len(CTA), (len(runs), len(PICKS))
src_path = vm[pieces[0]["material_id"]]["path"]; speech = rms_db(src_path, pieces[0]["source_timerange"]["start"]/US, 20)
print(f"sections {len(runs)} | speech RMS {speech:.1f} dB → bed target {speech-BED_UNDER_SPEECH_DB:.1f} dB")

# ---- 2. music bed (one track, 8 segments) + 3b. SFX (one track, 8 hits)
donor_mat, donor_seg, donor_extras = capcut._audio_donor()
def audio_material(src, tag):
    dest = D / f"ccstudio-audio-{tag}{src.suffix.lower()}"; shutil.copy(src, dest)
    m = copy.deepcopy(donor_mat); dur = capcut._probe_audio_dur_us(dest)
    m.update({"id": capcut._new_id(), "path": str(dest), "name": src.stem, "material_name": src.stem, "duration": dur, "type": "extract_music"})
    mats.setdefault("audios", []).append(m); return m, dur
def audio_segment(m, at_us, dur_us, vol, fade_in=0.0, fade_out=0.0):
    seg = copy.deepcopy(donor_seg); refs = capcut._clone_extras(mats, donor_extras)
    # replace / add the fade material
    fades = mats.setdefault("audio_fades", []); refs = [r for r in refs if not any(f["id"] == r for f in fades)]
    fd = {"fade_in_duration": int(fade_in*US), "fade_out_duration": int(fade_out*US), "fade_type": 0, "id": capcut._new_id(), "type": "audio_fade"}
    fades.append(fd); refs.append(fd["id"])
    seg.update({"id": capcut._new_id(), "material_id": m["id"], "extra_material_refs": refs, "volume": vol, "last_nonzero_volume": vol, "speed": 1.0,
                "target_timerange": {"start": int(at_us), "duration": int(dur_us)}, "source_timerange": {"start": 0, "duration": int(dur_us)},
                "common_keyframes": [], "keyframe_refs": [], "render_index": 0})
    return seg
music_segs = []; report = []
for i, ((a, b), (fname, why)) in enumerate(zip(runs, PICKS)):
    src = Path(MUSIC) / fname; m, mdur = audio_material(src, f"bed{i+1}")
    loud = rms_db(str(src), 5, 30); gain = float(min(0.5, 10 ** ((speech - BED_UNDER_SPEECH_DB - loud) / 20)))
    dur = min(b - a, mdur); music_segs.append(audio_segment(m, a, dur, gain, FADE_IN, FADE_OUT))
    report.append(f"  #{i+1} {a/US:6.1f}–{b/US:6.1f}  gain {gain:.3f} ({loud:.1f} dB)  {fname[:48]}  — {why}")
d["tracks"].append({"attribute": 0, "flag": 0, "id": capcut._new_id(), "is_default_name": False, "name": "music bed", "segments": music_segs, "type": "audio"})
print("music:\n" + "\n".join(report))
sfx_m, sfx_dur = audio_material(Path(SFX), "pop"); sfx_segs = []
for t in CTA: sfx_segs.append(audio_segment(sfx_m, int((t - 0.05)*US), sfx_dur, 0.7))
d["tracks"].append({"attribute": 0, "flag": 0, "id": capcut._new_id(), "is_default_name": False, "name": "sfx arrow", "segments": sfx_segs, "type": "audio"})
print(f"sfx: {len(sfx_segs)} × Pop.mp3 ({sfx_dur/US:.2f}s) @0.7")

# ---- 3. arrow overlay (one track, 8 pop-ins)
tpl = json.load(open(SP / "logo_template.json")); dest = D / "ccstudio-arrow-down.png"; shutil.copy(ARROW, dest)
am = copy.deepcopy(tpl["material"]); am.update({"id": capcut._new_id(), "path": str(dest), "material_name": dest.name, "width": 1080, "height": 1080, "duration": max(am.get("duration", 0), d["duration"])})
if "name" in am: am["name"] = dest.name
mats["videos"].append(am)
SCALE, Y, BOB = 0.20, -0.68, -0.03
arrow_segs = []
for (a, b), t in zip(runs, CTA):
    start = t - 0.10; end = min(start + 3.0, b/US - 0.08); L = end - start
    refs = []
    for lst, items in tpl["extras"].items():
        for ex in items:
            c = copy.deepcopy(ex); c["id"] = capcut._new_id(); mats.setdefault(lst, []).append(c); refs.append(c["id"])
    seg = copy.deepcopy(tpl["segment"]); maxri += 1
    seg.update({"id": capcut._new_id(), "material_id": am["id"], "extra_material_refs": refs, "render_index": maxri, "track_render_index": len(d["tracks"]),
                "target_timerange": {"start": int(start*US), "duration": int(L*US)}, "source_timerange": {"start": 0, "duration": int(L*US)},
                "volume": 1.0, "track_attribute": 0, "keyframe_refs": []})
    seg["clip"] = {"scale": {"x": 0.004, "y": 0.004}, "rotation": 0.0, "transform": {"x": 0.0, "y": Y}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    sc = [kf(0, 0.004, "CurveInOut"), kf(0.25*US, SCALE*1.18, "CurveInOut"), kf(0.40*US, SCALE, "CurveInOut"), kf((L-0.25)*US, SCALE, "CurveInOut"), kf(L*US, 0.004, "CurveInOut")]
    ys = [kf(0, Y), kf(0.40*US, Y)]; tt = 0.40
    while tt + 1.0 <= L - 0.25:
        ys += [kf((tt+0.5)*US, Y+BOB, "CurveInOut"), kf((tt+1.0)*US, Y, "CurveInOut")]; tt += 1.0
    ys.append(kf(L*US, Y))
    seg["common_keyframes"] = [group("KFTypeScaleX", sc), group("KFTypeScaleY", [dict(k, id=capcut._new_id()) for k in sc]),
                               group("KFTypePositionY", ys), group("KFTypePositionX", [kf(0, 0.0), kf(L*US, 0.0)]), group("KFTypeRotation", [kf(0, 0.0), kf(L*US, 0.0)])]
    arrow_segs.append(seg)
d["tracks"].append({"attribute": 0, "flag": 0, "id": capcut._new_id(), "is_default_name": False, "name": "arrow cta", "segments": arrow_segs, "type": "video"})
print(f"arrow: {len(arrow_segs)} pop-ins, windows " + ", ".join(f"{s['target_timerange']['start']/US:.1f}+{s['target_timerange']['duration']/US:.1f}" for s in arrow_segs))
capcut._backup(D); capcut._atomic_write(D, d); print("written")
