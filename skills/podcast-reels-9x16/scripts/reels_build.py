# -*- coding: utf-8 -*-
"""Build a 9:16 client-reels draft from marked ranges — stages 3+4 of the pipeline, into a draft
that already exists (the one Alon created and dropped the raw material into), with the house
delivery format from the first frame.

    python reels_build.py plan.json            # dry run: prints the layout and the copies it would make
    python reels_build.py plan.json --write    # encodes work copies, writes draft_info.json, registers media

The plan (JSON):
  target   draft folder to rebuild IN PLACE (its id and Media-panel identity are kept; its timeline is replaced)
  donor    a 9:16 reel project of the right shape — templates for segments, the white card, the title
           style, the adjust track with the brand LUT (`פרויקט-דוגמה N רילס` for a customer reel: zero logos)
  shoots   {key: {cam1, cam2, mic1, mic2, mic_offset}}  — mic_time = cam_time + mic_offset (measured, ≈ −0.15);
           a mic may be the camera file itself (RODECASTER Video mp4s carry the mix); cam2/mic2 null = one-camera
           shoot (the hidden layer gets that reel's picture with silent audio so the copy stays continuous)
  reels    [{n, title, shoot, start, end, music: {path, src_start, vol}}]  — start/end on the CAMERA clock
  base_cam which camera is the visible bottom layer (the dominant speaker); the other toggles on top
  prefix   work-copy names: ccstudio-<prefix>-cam1.mp4 …

Work copies are ONE concatenated file per camera (all reel ranges back to back, `handle` s each side)
with that camera's own isolated mic muxed in, plus the same concatenation of the two mic wavs — so
copy_time == mic_time for every reel and every later stage (apply_multicam, reel_captions, mic_windows)
reads the mics at `--mic-offset 0` with one `--audio` folder. The sound travels with the picture, both
layers play at volume ≥ 1 (each file carries a different mic, nothing doubles), opacity is the edit.
"""
import argparse, copy, json, os, shutil, subprocess, sys, time, uuid
from pathlib import Path
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut, paths

US = 1_000_000; FF = str(paths.FFMPEG)
ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("--write", action="store_true"); ap.add_argument("--skip-encode", action="store_true", help="work copies already exist — only rebuild the draft")
A = ap.parse_args(); P = json.load(open(A.plan))
TGT = capcut.DRAFTS_DIR / P["target"]; DON = capcut.DRAFTS_DIR / P["donor"]
H = float(P.get("handle", 1.5)); CARD = float(P.get("card", 5.0)); PFX = P.get("prefix", "reel"); BASE = int(P.get("base_cam", 2)); TOP = 3 - BASE
FPS = float(P.get("fps", 60)); FR = US / FPS
snap = lambda us: int(round(us / FR) * FR)
nid = lambda: str(uuid.uuid4()).upper()

# ── 1. the copy plan: every reel range with handles, on the camera clock ─────────────────────────
CAMFR = 1 / 30.0                                                             # the cameras are 30 fps; cut lengths on their grid
pieces = []; t_copy = 0.0
for r in P["reels"]:
    sh = P["shoots"][r["shoot"]]
    a = max(0.0, r["start"] - H); L = round((r["end"] + H - a) / CAMFR) * CAMFR
    pieces.append({"reel": r["n"], "shoot": r["shoot"], "cam_a": a, "len": L, "copy_a": t_copy, "in": r["start"] - a, "out": r["end"] - a})
    t_copy += L
print(f"{len(P['reels'])} reels · card {CARD}s · handles {H}s · copies {t_copy:.1f}s per camera")
for pc, r in zip(pieces, P["reels"]):
    print(f"  ריל {r['n']}  {r['shoot']:6} cam {r['start']:8.2f}–{r['end']:8.2f} ({r['end']-r['start']:5.1f}s)  → copy {pc['copy_a']+pc['in']:7.2f}–{pc['copy_a']+pc['out']:7.2f}   «{r['title'][:40]}»")

def encode_copies():
    tmp = TGT / "ccstudio-tmp"; tmp.mkdir(exist_ok=True)
    out = {}
    for cam in (1, 2):
        parts = []
        for i, pc in enumerate(pieces):
            sh = P["shoots"][pc["shoot"]]; single = not sh.get(f"cam{cam}")          # a one-camera shoot: this angle does not exist
            src = sh[f"cam{cam}"] or sh["cam1"]; mic = sh.get(f"mic{cam}") or sh["mic1"]; mo = float(sh["mic_offset"])
            part = tmp / f"c{cam}-{i}.mp4"
            ss_mic = pc["cam_a"] + mo; assert ss_mic >= 0, "negative mic seek"
            subprocess.run([FF, "-v", "error", "-y", "-ss", f"{pc['cam_a']:.4f}", "-t", f"{pc['len']:.4f}", "-i", src,
                            "-ss", f"{ss_mic:.4f}", "-t", f"{pc['len']:.4f}", "-i", mic,
                            "-map", "0:v:0", "-map", "1:a:0"] + (["-vf", sh[f"vf{cam}"]] if sh.get(f"vf{cam}") else []) +
                           [*((["-c:v", "h264_videotoolbox"]) if __import__("sys").platform == "darwin" else ["-c:v", "libx264", "-preset", "fast"]), "-b:v", "30M", "-g", "30", "-r", "30"]
                           + (["-af", "volume=0"] if single else []) +                    # keeps the copy continuous; the layer stays hidden and silent
                           ["-c:a", "aac", "-b:a", "256k", "-ac", "1", "-shortest", str(part)], check=True)
            parts.append(part); print(f"    cam{cam} piece {i}: {pc['len']:.2f}s", flush=True)
        lst = tmp / f"c{cam}.txt"; lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
        dst = TGT / f"ccstudio-{PFX}-cam{cam}.mp4"
        subprocess.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(dst)], check=True, cwd=tmp)
        out[f"cam{cam}"] = dst
        # the mic wav, same concatenation
        wparts = []
        for i, pc in enumerate(pieces):
            sh = P["shoots"][pc["shoot"]]; mic = sh.get(f"mic{cam}") or sh["mic1"]; mo = float(sh["mic_offset"]); wp = tmp / f"m{cam}-{i}.wav"
            subprocess.run([FF, "-v", "error", "-y", "-ss", f"{pc['cam_a']+mo:.4f}", "-t", f"{pc['len']:.4f}", "-i", mic] + (["-af", "volume=0"] if not sh.get(f"cam{cam}") else []) + ["-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(wp)], check=True); wparts.append(wp)
        wl = tmp / f"m{cam}.txt"; wl.write_text("".join(f"file '{p.name}'\n" for p in wparts))
        wdst = TGT / f"ccstudio-{PFX}-mic{cam}.wav"
        subprocess.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(wl), "-c", "copy", str(wdst)], check=True, cwd=tmp)
        out[f"mic{cam}"] = wdst
    shutil.rmtree(tmp, ignore_errors=True)
    return out

def probe(path):
    r = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    import re
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r); dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    wh = re.search(r"(\d{3,5})x(\d{3,5})", r)                                # audio files have no frame size
    return (int(wh.group(1)) if wh else 0), (int(wh.group(2)) if wh else 0), int(dur * US)

def lufs(path):
    r = subprocess.run([FF, "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    import re; m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r); return float(m[-1]) if m else None

if not A.write:
    print("\n(הרצה יבשה — הוסף --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{TGT}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט — לצאת למסך הבית")

copies = {k: TGT / f"ccstudio-{PFX}-{k}.{'mp4' if k.startswith('cam') else 'wav'}" for k in ("cam1", "cam2", "mic1", "mic2")}
if not A.skip_encode or not all(p.exists() for p in copies.values()):
    print("\nencoding work copies …"); copies = encode_copies()
levels = {k: lufs(copies[k]) for k in ("mic1", "mic2")}
print("mic loudness (integrated LUFS over all reels):", levels)
TARGET_LUFS = float(P.get("voice_lufs", -18.0))
# RODECASTER channels are recorded with 15–25 dB of headroom; a CapCut volume slider tops out far below
# that, so the gain is BAKED into the work copy's audio (video stream copied, a limiter for safety) and
# the segments play at volume 1. Re-running with --skip-encode re-measures the copy, so it is idempotent.
gain = {}
for c in (1, 2):
    have = lufs(copies[f"cam{c}"]); need = TARGET_LUFS - (have if have is not None and have > -60 else TARGET_LUFS)
    if need > 1.0:
        tmp = copies[f"cam{c}"].with_suffix(".norm.mp4")
        subprocess.run([FF, "-v", "error", "-y", "-i", str(copies[f"cam{c}"]), "-c:v", "copy", "-af", f"volume={need:.1f}dB,alimiter=limit=0.891:attack=5:release=50",
                        "-c:a", "aac", "-b:a", "256k", str(tmp)], check=True); os.replace(tmp, copies[f"cam{c}"])
        print(f"  cam{c}: audio {have:.1f} LUFS → +{need:.1f} dB baked → {lufs(copies[f'cam{c}']):.1f} LUFS")
    else: print(f"  cam{c}: audio {have:.1f} LUFS, left as is")
    gain[c] = 1.0

# ── 2. the draft: the donor's settings, this draft's identity, a timeline from scratch ──────────
tgt_old = json.loads((TGT / "draft_info.json").read_text()); don = json.loads((DON / "draft_info.json").read_text())
d = copy.deepcopy(don); d["id"] = tgt_old["id"]; d["name"] = tgt_old.get("name", ""); d["fps"] = FPS
dvids = {m["id"]: m for m in don["materials"]["videos"]}; didx = capcut._materials_index(don)
vt = [t for t in don["tracks"] if t["type"] == "video" and t["segments"]]
seg_tpl = next(copy.deepcopy(s) for t in vt for s in t["segments"] if dvids.get(s["material_id"], {}).get("type") == "video")
mat_tpl = copy.deepcopy(next(m for m in don["materials"]["videos"] if m.get("type") == "video"))
card_seg = next(copy.deepcopy(s) for t in vt for s in t["segments"] if dvids.get(s["material_id"], {}).get("type") == "photo")
card_mat = copy.deepcopy(dvids[card_seg["material_id"]])
def _txt(t):
    m = next((m for m in don["materials"]["texts"] if m["id"] == t["segments"][0]["material_id"]), None)
    try: return json.loads(m["content"])["text"] if m else ""
    except Exception: return ""
title_tr = next(t for t in don["tracks"] if t["type"] == "text" and 0 < len(t["segments"]) <= 20 and t["segments"][0]["target_timerange"]["duration"] > 3 * US
                and (not P.get("title_like") or _txt(t).startswith(P["title_like"])))     # plan "title_like": the donor card title's opening text
title_seg = copy.deepcopy(title_tr["segments"][0]); title_mat = copy.deepcopy(next(m for m in don["materials"]["texts"] if m["id"] == title_seg["material_id"]))
adj_tr = next(t for t in don["tracks"] if t["type"] == "adjust" and t["segments"]); adj_seg = copy.deepcopy(adj_tr["segments"][0])
adj_mat_list, adj_mat = next(((k, m) for k, v in don["materials"].items() if isinstance(v, list) for m in v if isinstance(m, dict) and m.get("id") == adj_seg["material_id"]), (None, None))   # the adjust segment's own material (a `placeholder`), cloned once below
aud_tr = next(t for t in don["tracks"] if t["type"] == "audio" and t["segments"]); aud_seg = copy.deepcopy(aud_tr["segments"][0])
aud_mat = copy.deepcopy(next(m for m in don["materials"]["audios"] if m["id"] == aud_seg["material_id"]))
trk_tpl = copy.deepcopy(vt[0]); trk_tpl["segments"] = []

for k, v in list(d["materials"].items()):                                    # a clean pool: only what this build references
    if isinstance(v, list): d["materials"][k] = []
def add(listname, m): m = copy.deepcopy(m); m["id"] = nid(); d["materials"].setdefault(listname, []).append(m); return m
def clone_extras(seg):
    refs = []
    for r in seg.get("extra_material_refs", []):
        if r in didx: refs.append(add(didx[r][0], didx[r][1])["id"])
    return refs

cam_mat = {}
for c in (1, 2):
    w, h, dur = probe(copies[f"cam{c}"]); m = add("videos", mat_tpl)
    m.update({"path": str(copies[f"cam{c}"]), "width": w, "height": h, "duration": dur, "material_name": copies[f"cam{c}"].name, "type": "video", "crop_scale": 1.0,
              "crop": {"upper_left_x": 0.0, "upper_left_y": 0.0, "upper_right_x": 1.0, "upper_right_y": 0.0, "lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0, "lower_right_y": 1.0}})
    m["matting"] = {"flag": 0, "has_use_quick_brush": False, "has_use_quick_eraser": False, "interactiveTime": [], "path": "", "strokes": []} if m.get("matting") else m.get("matting")
    cam_mat[c] = m
white = TGT / "ccstudio-card.png"                                            # a real 1080×1920 white PNG, not the donor's 300×170 online material
subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=white:s={d['canvas_config']['width']}x{d['canvas_config']['height']}", "-frames:v", "1", str(white)], check=True)
cmat = add("videos", card_mat); cmat.update({"path": str(white), "width": d["canvas_config"]["width"], "height": d["canvas_config"]["height"], "material_name": white.name})

def footage(cam, src_a, dur_us, t_us, visible):
    s = copy.deepcopy(seg_tpl); s["id"] = nid(); s["material_id"] = cam_mat[cam]["id"]
    s["target_timerange"] = {"start": int(t_us), "duration": int(dur_us)}; s["source_timerange"] = {"start": snap(int(src_a * US)), "duration": int(dur_us)}
    s["clip"]["scale"] = {"x": 1.0, "y": 1.0}; s["clip"]["transform"] = {"x": 0.0, "y": 0.0}; s["clip"]["alpha"] = 1.0 if visible else 0.0; s["clip"]["rotation"] = 0.0
    s["volume"] = round(gain[cam], 4); s["last_nonzero_volume"] = s["volume"]
    s["common_keyframes"] = []; s["keyframe_refs"] = []; s["extra_material_refs"] = clone_extras(seg_tpl); return s
def card(t_us):
    s = copy.deepcopy(card_seg); s["id"] = nid(); s["material_id"] = cmat["id"]
    s["target_timerange"] = {"start": int(t_us), "duration": snap(int(CARD * US))}; s["source_timerange"] = {"start": 0, "duration": s["target_timerange"]["duration"]}
    s["clip"]["scale"] = {"x": 1.0, "y": 1.0}; s["clip"]["transform"] = {"x": 0.0, "y": 0.0}; s["clip"]["alpha"] = 1.0; s["volume"] = 0.0
    s["common_keyframes"] = []; s["keyframe_refs"] = []; s["extra_material_refs"] = clone_extras(card_seg); return s

from PIL import ImageFont
FONT = json.loads(title_mat["content"])["styles"][0]["font"]["path"]; f60 = ImageFont.truetype(FONT, 60)
def title_lines(text, width_px, size):
    """wrap by RENDERED width (PIL@60 × size/10, the 9:16 calibration), not by characters — Alon re-flowed
    «ההבדל האמיתי בין יד שנייה לפריסל» (31 chars) back onto ONE line at size 25; a 22-char wrap was three lines"""
    out, cur = [], ""
    for w in text.split():
        cand = f"{cur} {w}".strip()
        if cur and f60.getlength(cand) * size / 10 > width_px: out.append(cur); cur = w
        else: cur = cand
    if cur: out.append(cur)
    return out
def title(t_us, n, text):
    m = add("texts", title_mat); size = float(json.loads(title_mat["content"])["styles"][0].get("size", 32))
    lines = [f"רילס {n}"] + title_lines(text, 0.9 * 1080, size)
    widest = max(f60.getlength(l) for l in lines); px = lambda sz: widest * sz / 10        # 9:16: px = PIL@60 × size/10
    while px(size) > 0.82 * 1080 and size > 14: size -= 1
    capcut._set_text(m, "\n".join(lines), None)
    pay = json.loads(m["content"])
    for st in pay.get("styles", []): st["size"] = size; st["useLetterColor"] = True
    m["content"] = json.dumps(pay, ensure_ascii=False); m["font_size"] = size
    s = copy.deepcopy(title_seg); s["id"] = nid(); s["material_id"] = m["id"]; s["extra_material_refs"] = clone_extras(title_seg)
    s["target_timerange"] = {"start": int(t_us + snap(int(0.2 * US))), "duration": snap(int((CARD - 0.4) * US))}; s["source_timerange"] = None
    s["common_keyframes"] = []; s["keyframe_refs"] = []; return s, size
_adj_clone = add(adj_mat_list, adj_mat) if adj_mat else None
def adjust(t0, t1):
    s = copy.deepcopy(adj_seg); s["id"] = nid(); s["extra_material_refs"] = clone_extras(adj_seg)
    if _adj_clone: s["material_id"] = _adj_clone["id"]
    s["target_timerange"] = {"start": int(t0), "duration": int(t1 - t0)}; s["source_timerange"] = {"start": 0, "duration": int(t1 - t0)}; s["common_keyframes"] = []; s["keyframe_refs"] = []; return s
def music(t0, dur_us, spec):
    """the bed as a LOCAL material (a clone of a library track keeps its `effect_id` and CapCut re-points it to the
    library cache on open — 0922's four silent beds), the file copied into the draft folder, LOOPED in pieces when the
    track is shorter than the reel (the brand `.full` masters run 68–76 s); fade 0.6 s in on the first piece, 2.0 s out
    on the last, 0.3 s on the seams"""
    path = spec["path"]; dst = TGT / f"ccstudio-music-{os.path.basename(path)}"
    if not dst.exists(): shutil.copy(path, dst)
    m = add("audios", aud_mat)
    m.update({"path": str(dst), "name": dst.name, "material_name": None, "type": "extract_music", "category_id": "", "category_name": "local", "effect_id": "",
              "music_id": str(uuid.uuid4()), "local_material_id": str(uuid.uuid4()), "source_platform": 0, "check_flag": 1, "duration": probe(dst)[2], "copyright_limit_type": "none", "wave_points": []})
    src0 = snap(int(float(spec.get("src_start", 0)) * US)); pieces_out = []; left = int(dur_us); t = int(t0); first = True
    while left > 0:
        L = min(left, m["duration"] - src0)
        s = copy.deepcopy(aud_seg); s["id"] = nid(); s["material_id"] = m["id"]; s["extra_material_refs"] = [r for r in clone_extras(aud_seg) if not any(x["id"] == r for x in d["materials"].get("audio_fades", []))]
        s["target_timerange"] = {"start": t, "duration": int(L)}; s["source_timerange"] = {"start": src0, "duration": int(L)}
        s["volume"] = float(spec["vol"]); s["last_nonzero_volume"] = s["volume"]; s["common_keyframes"] = []; s["keyframe_refs"] = []
        last = left - L <= 0
        fd = {"id": nid(), "type": "audio_fade", "fade_type": 0, "fade_in_duration": int((0.6 if first else 0.3) * US), "fade_out_duration": int((2.0 if last else 0.3) * US)}
        d["materials"].setdefault("audio_fades", []).append(fd); s["extra_material_refs"].append(fd["id"])
        pieces_out.append(s); t += L; left -= L; src0 = 0; first = False
    return pieces_out

base, over, adjs, titles, beds = [], [], [], [], []; t = 0; spans = []
for pc, r in zip(pieces, P["reels"]):
    base.append(card(t)); ts, sz = title(t, r["n"], r["title"]); titles.append(ts); t += snap(int(CARD * US))
    dur = snap(int((r["end"] - r["start"]) * US)); a_src = pc["copy_a"] + pc["in"]
    base.append(footage(BASE, a_src, dur, t, True))
    if P["shoots"][r["shoot"]].get(f"cam{TOP}"): over.append(footage(TOP, a_src, dur, t, False))   # no over segment on a one-camera shoot
    adjs.append(adjust(t, t + dur))
    if r.get("music"): beds += music(t, dur, r["music"])
    spans.append((t, t + dur, r["n"])); print(f"  ריל {r['n']}: card {(t - snap(int(CARD*US)))/US:.2f} · footage {t/US:.2f}–{(t+dur)/US:.2f} · title size {sz:.0f}")
    t += dur
t0 = copy.deepcopy(trk_tpl); t0["id"] = nid(); t0["segments"] = base; t0["flag"] = 0; t0["attribute"] = 0; t0["name"] = ""; t0["is_default_name"] = True
t1 = copy.deepcopy(trk_tpl); t1["id"] = nid(); t1["segments"] = over; t1["flag"] = 2; t1["attribute"] = 0
ta = copy.deepcopy(adj_tr); ta["id"] = nid(); ta["segments"] = adjs
tt = copy.deepcopy(title_tr); tt["id"] = nid(); tt["segments"] = titles; tt["name"] = "כותרות"; tt["is_default_name"] = False
tm = copy.deepcopy(aud_tr); tm["id"] = nid(); tm["segments"] = beds; tm["name"] = "מוזיקה"; tm["is_default_name"] = False
d["tracks"] = [t0, t1] + ([ta] if P.get("adjust", True) else []) + [tt] + ([tm] if beds else [])
ri = 0
for tr in d["tracks"]:
    for s in tr["segments"]: s["render_index"] = ri; ri += 1
d["duration"] = t
# fresh ids on every keyframe container (none yet) and a sanity pass on ids
ids = [s["id"] for tr in d["tracks"] for s in tr["segments"]]; assert len(ids) == len(set(ids))
capcut._backup(TGT); tmp = TGT / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(TGT / "draft_info.json")
mp = TGT / "draft_meta_info.json"
if mp.exists() and capcut._capcut_pid() is None:
    meta = json.loads(mp.read_text()); meta["tm_duration"] = d["duration"]; meta["tm_draft_modified"] = int(time.time() * US); mp.write_text(json.dumps(meta, ensure_ascii=False))
json.dump({"pieces": pieces, "spans": [(a / US, b / US, n) for a, b, n in spans], "copies": {k: str(v) for k, v in copies.items()}, "gain": gain, "levels": levels}, open(TGT / f"ccstudio-{PFX}-plan.json", "w"), ensure_ascii=False, indent=1)
print(f"\n✓ WRITTEN «{P['target']}» · {len(base)} base segs · {len(over)} over · {len(adjs)} adjust · {len(titles)} titles · {len(beds)} beds · {d['duration']/US/60:.2f} min · canvas {d['canvas_config']['width']}x{d['canvas_config']['height']}")
