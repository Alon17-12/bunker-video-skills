# -*- coding: utf-8 -*-
"""Append ONE more reel to a draft that `reels_build.py` built and Alon has since touched — without
rebuilding anything he already has (his trims, the captions, the punches, the framing all stay).

    python reel_append.py plan.json --reel 5 --encode        # encode the new piece, glue it onto the work copies
    python reel_append.py plan.json --reel 5 --write         # add card + title + both cameras + adjust + bed at the end

The work copies are ONE concatenated file per camera (see reels_build.py), so a new reel is a new piece
encoded with the same parameters, gain-baked to the same loudness, and concatenated onto the end of the
existing copy (`-c copy`, same encoder, same GOP) — every earlier source time stays where it was. The mic
wavs get the same piece. `ccstudio-<prefix>-plan.json` records the new piece and span.

The draft segments are cloned from the LAST reel already on the timeline (card, title, base, over,
adjust, bed): same project, same templates, nothing borrowed from a donor. Keyframes are cleared on the
new footage — run `frame_shots.py --from <t>` and `reel_punches.py --from <t>` afterwards.

Music beds are written as LOCAL materials (type `extract_music`, category `local`, no `effect_id`):
a bed cloned from an online-library material keeps the library's `effect_id`, and CapCut re-resolves it
on open to the library's cached mp3 — the four beds of 0922 all played the same cache file, and Alon
heard nothing. Every bed on the track (old and new) is normalised here and its file copied into the
draft folder as `ccstudio-music-<name>.mp3`.
"""
import argparse, copy, json, os, re, shutil, subprocess, sys, time, uuid
from pathlib import Path
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut, paths

US = 1_000_000; FF = str(paths.FFMPEG)
ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("--reel", type=int, required=True)
ap.add_argument("--encode", action="store_true"); ap.add_argument("--write", action="store_true")
ap.add_argument("--target-lufs", type=float, default=-16.0)
A = ap.parse_args(); P = json.load(open(A.plan))
TGT = capcut.DRAFTS_DIR / P["target"]; PFX = P.get("prefix", "reel"); H = float(P.get("handle", 1.5)); CARD = float(P.get("card", 5.0))
BASE = int(P.get("base_cam", 2)); TOP = 3 - BASE; FPS = float(P.get("fps", 60)); FR = US / FPS
snap = lambda us: int(round(us / FR) * FR); nid = lambda: str(uuid.uuid4()).upper()
CAMFR = 1 / 30.0
R = next(r for r in P["reels"] if r["n"] == A.reel); sh = P["shoots"][R["shoot"]]
plan_p = TGT / f"ccstudio-{PFX}-plan.json"; plan = json.load(open(plan_p))
copies = {k: TGT / f"ccstudio-{PFX}-{k}.{'mp4' if k.startswith('cam') else 'wav'}" for k in ("cam1", "cam2", "mic1", "mic2")}

def probe(path):
    r = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r); dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    wh = re.search(r"(\d{3,5})x(\d{3,5})", r)
    return (int(wh.group(1)) if wh else 0), (int(wh.group(2)) if wh else 0), int(round(dur * US))
def lufs(path):
    r = subprocess.run([FF, "-hide_banner", "-i", str(path), "-vn", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r); return float(m[-1]) if m else None

# ── the piece, on the camera clock; its place on the copy clock is the END of the copy as it is now ──
a = max(0.0, R["start"] - H); L = round((R["end"] + H - a) / CAMFR) * CAMFR
copy_a = probe(copies["cam2"])[2] / US
piece = {"reel": R["n"], "shoot": R["shoot"], "cam_a": a, "len": L, "copy_a": round(copy_a, 4), "in": R["start"] - a, "out": R["end"] - a}
print(f"ריל {R['n']} {R['shoot']} cam {R['start']:.2f}–{R['end']:.2f} ({R['end']-R['start']:.1f}s) → copy {copy_a+piece['in']:.2f}–{copy_a+piece['out']:.2f}   «{R['title']}»")
if any(pc["reel"] == R["n"] for pc in plan["pieces"]) and A.encode: sys.exit("✗ הריל הזה כבר בעותקי העבודה — לא מצרף פעמיים")

if A.encode:
    tmp = TGT / "ccstudio-tmp"; tmp.mkdir(exist_ok=True)
    for cam in (1, 2):
        src = sh[f"cam{cam}"]; mic = sh[f"mic{cam}"]; mo = float(sh["mic_offset"]); part = tmp / f"c{cam}-new.mp4"
        subprocess.run([FF, "-v", "error", "-y", "-ss", f"{a:.4f}", "-t", f"{L:.4f}", "-i", src, "-ss", f"{a+mo:.4f}", "-t", f"{L:.4f}", "-i", mic,
                        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "h264_videotoolbox", "-b:v", "30M", "-g", "30", "-r", "30",
                        "-c:a", "aac", "-b:a", "256k", "-ac", "1", "-shortest", str(part)], check=True)
        have = lufs(part); need = A.target_lufs - have
        if need > 1.0:
            norm = tmp / f"c{cam}-new.norm.mp4"
            subprocess.run([FF, "-v", "error", "-y", "-i", str(part), "-c:v", "copy", "-af", f"volume={need:.1f}dB,alimiter=limit=0.891:attack=5:release=50", "-c:a", "aac", "-b:a", "256k", str(norm)], check=True)
            os.replace(norm, part); print(f"  cam{cam}: piece {have:.1f} LUFS → +{need:.1f} dB → {lufs(part):.1f}")
        else: print(f"  cam{cam}: piece {have:.1f} LUFS, left")
        old = copies[f"cam{cam}"]; keep = tmp / f"c{cam}-old.mp4"; shutil.move(old, keep)
        (tmp / f"c{cam}.txt").write_text(f"file '{keep.name}'\nfile '{part.name}'\n")
        subprocess.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"c{cam}.txt", "-c", "copy", str(old)], check=True, cwd=tmp)
        wp = tmp / f"m{cam}-new.wav"
        subprocess.run([FF, "-v", "error", "-y", "-ss", f"{a+mo:.4f}", "-t", f"{L:.4f}", "-i", mic, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(wp)], check=True)
        oldw = copies[f"mic{cam}"]; keepw = tmp / f"m{cam}-old.wav"; shutil.move(oldw, keepw)
        (tmp / f"m{cam}.txt").write_text(f"file '{keepw.name}'\nfile '{wp.name}'\n")
        subprocess.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"m{cam}.txt", "-c", "copy", str(oldw)], check=True, cwd=tmp)
        print(f"  cam{cam}: copy now {probe(old)[2]/US:.2f}s · mic {probe(oldw)[2]/US:.2f}s", flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    plan["pieces"].append(piece); json.dump(plan, open(plan_p, "w"), ensure_ascii=False, indent=1); print("✓ encoded + appended")

if not A.write: sys.exit()
pid = capcut._capcut_pid()
if pid and f"{TGT}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט — לצאת למסך הבית")
pc = next(p for p in plan["pieces"] if p["reel"] == R["n"])
d = json.loads((TGT / "draft_info.json").read_text()); mats = d["materials"]
byid = {}
for k, v in mats.items():
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict) and "id" in m: byid[m["id"]] = (k, m)
def clone_refs(seg):
    out = []
    for r in seg.get("extra_material_refs", []):
        if r in byid:
            k, m = byid[r]; m2 = copy.deepcopy(m); m2["id"] = nid(); mats[k].append(m2); byid[m2["id"]] = (k, m2); out.append(m2["id"])
    return out
vm = {m["id"]: m for m in mats["videos"]}
tr = {t.get("name") or t["type"]: t for t in d["tracks"]}
base_t = [t for t in d["tracks"] if t["type"] == "video"][0]; over_t = [t for t in d["tracks"] if t["type"] == "video"][1]
adj_t = next(t for t in d["tracks"] if t["type"] == "adjust"); title_t = tr["כותרות"]; bed_t = tr["מוזיקה"]
last = lambda t: max(t["segments"], key=lambda s: s["target_timerange"]["start"])
# material durations: the copies grew
for m in mats["videos"]:
    for cam in (1, 2):
        if m.get("path", "").endswith(copies[f"cam{cam}"].name): m["duration"] = probe(copies[f"cam{cam}"])[2]
cam_mat = {cam: next(m for m in mats["videos"] if m.get("path", "").endswith(copies[f"cam{cam}"].name)) for cam in (1, 2)}
t0 = d["duration"]; dur = snap(int((R["end"] - R["start"]) * US)); src_a = snap(int((pc["copy_a"] + pc["in"]) * US))
# card + title
cs = copy.deepcopy(last(base_t) if vm[last(base_t)["material_id"]].get("type") == "photo" else next(s for s in base_t["segments"] if vm[s["material_id"]].get("type") == "photo"))
cs["id"] = nid(); cs["extra_material_refs"] = clone_refs(cs); cs["target_timerange"] = {"start": t0, "duration": snap(int(CARD * US))}; cs["source_timerange"] = {"start": 0, "duration": cs["target_timerange"]["duration"]}; cs["common_keyframes"] = []; cs["keyframe_refs"] = []
ts = copy.deepcopy(last(title_t)); tmat = copy.deepcopy(byid[ts["material_id"]][1]); tmat["id"] = nid(); mats["texts"].append(tmat)
ts["id"] = nid(); ts["material_id"] = tmat["id"]; ts["extra_material_refs"] = clone_refs(ts); ts["target_timerange"] = {"start": t0 + snap(int(0.2 * US)), "duration": snap(int((CARD - 0.4) * US))}
from PIL import ImageFont
pay = json.loads(tmat["content"]); FONT = pay["styles"][0]["font"]["path"]; f60 = ImageFont.truetype(FONT, 60)
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
size = float(pay["styles"][0].get("size", 25)); lines = [f"רילס {R['n']}"] + title_lines(R["title"], 0.9 * 1080, size)
widest = max(f60.getlength(l) for l in lines)
while widest * size / 10 > 0.82 * 1080 and size > 14: size -= 1
capcut._set_text(tmat, "\n".join(lines), None); pay = json.loads(tmat["content"])
for st in pay.get("styles", []): st["size"] = size; st["useLetterColor"] = True
tmat["content"] = json.dumps(pay, ensure_ascii=False); tmat["font_size"] = size
# footage
def footage(tk, cam, visible):
    s = copy.deepcopy(next(x for x in sorted(tk["segments"], key=lambda x: -x["target_timerange"]["start"]) if vm[x["material_id"]].get("type") == "video"))
    s["id"] = nid(); s["material_id"] = cam_mat[cam]["id"]; s["extra_material_refs"] = clone_refs(s)
    s["target_timerange"] = {"start": t0 + snap(int(CARD * US)), "duration": dur}; s["source_timerange"] = {"start": src_a, "duration": dur}
    s["clip"]["scale"] = {"x": 1.0, "y": 1.0}; s["clip"]["transform"] = {"x": 0.0, "y": 0.0}; s["clip"]["alpha"] = 1.0 if visible else 0.0
    s["volume"] = 1.0; s["last_nonzero_volume"] = 1.0; s["common_keyframes"] = []; s["keyframe_refs"] = []; return s
bs = footage(base_t, BASE, True); osg = footage(over_t, TOP, False)
adj = copy.deepcopy(last(adj_t)); adj["id"] = nid(); adj["extra_material_refs"] = clone_refs(adj)
adj["target_timerange"] = {"start": bs["target_timerange"]["start"], "duration": dur}; adj["source_timerange"] = {"start": 0, "duration": dur}; adj["common_keyframes"] = []; adj["keyframe_refs"] = []
# ── beds: every bed becomes a LOCAL material with the file inside the draft folder ────────────────
def localise(m, src):
    dst = TGT / f"ccstudio-music-{os.path.basename(src)}"
    if not dst.exists(): shutil.copy(src, dst)
    m.update({"path": str(dst), "name": dst.name, "material_name": None, "type": "extract_music", "category_id": "", "category_name": "local", "effect_id": "",
              "music_id": str(uuid.uuid4()), "local_material_id": str(uuid.uuid4()), "source_platform": 0, "check_flag": 1, "duration": probe(dst)[2], "copyright_limit_type": "none", "wave_points": []})
    return m
by_name = {os.path.splitext(os.path.basename(r["music"]["path"]))[0]: r for r in P["reels"] if r.get("music")}
n_fix = 0
for s in bed_t["segments"]:
    m = byid[s["material_id"]][1]; key = re.sub(r"^ccstudio-music-|\.mp3$", "", m.get("name", "")); r = by_name.get(key)
    if r: localise(m, r["music"]["path"]); s["volume"] = float(r["music"]["vol"]); s["last_nonzero_volume"] = s["volume"]; n_fix += 1
    else: print("  ?? bed without a plan entry:", m.get("name"))
bm = copy.deepcopy(byid[last(bed_t)["material_id"]][1]); bm["id"] = nid(); mats["audios"].append(bm); localise(bm, R["music"]["path"])
bsg = copy.deepcopy(last(bed_t)); bsg["id"] = nid(); bsg["material_id"] = bm["id"]; bsg["extra_material_refs"] = clone_refs(bsg)
src0 = snap(int(float(R["music"].get("src_start", 0)) * US)); bdur = min(dur, bm["duration"] - src0)
bsg["target_timerange"] = {"start": bs["target_timerange"]["start"], "duration": bdur}; bsg["source_timerange"] = {"start": src0, "duration": bdur}
bsg["volume"] = float(R["music"]["vol"]); bsg["last_nonzero_volume"] = bsg["volume"]; bsg["common_keyframes"] = []; bsg["keyframe_refs"] = []
for x in mats.get("audio_fades", []):
    if x["id"] in bsg["extra_material_refs"]: x["fade_in_duration"] = int(0.6 * US); x["fade_out_duration"] = int(2.0 * US)
ri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
for s in (cs, ts, bs, osg, adj, bsg): ri += 1; s["render_index"] = ri
base_t["segments"] += [cs, bs]; over_t["segments"].append(osg); adj_t["segments"].append(adj); title_t["segments"].append(ts); bed_t["segments"].append(bsg)
d["duration"] = bs["target_timerange"]["start"] + dur
ids = [s["id"] for t in d["tracks"] for s in t["segments"]]; assert len(ids) == len(set(ids))
plan["spans"] = [sp for sp in plan["spans"] if sp[2] != R["n"]] + [[bs["target_timerange"]["start"] / US, d["duration"] / US, R["n"]]]
capcut._backup(TGT); tmpf = TGT / "draft_info.json.tmp"; tmpf.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmpf.read_text()); tmpf.replace(TGT / "draft_info.json")
mp = TGT / "draft_meta_info.json"
if mp.exists() and capcut._capcut_pid() is None:
    meta = json.loads(mp.read_text()); meta["tm_duration"] = d["duration"]; meta["tm_draft_modified"] = int(time.time() * US); mp.write_text(json.dumps(meta, ensure_ascii=False))
json.dump(plan, open(plan_p, "w"), ensure_ascii=False, indent=1)
print(f"✓ WRITTEN ריל {R['n']}: card {t0/US:.2f} · footage {bs['target_timerange']['start']/US:.2f}–{d['duration']/US:.2f} · title size {size:.0f} · beds localised {n_fix}+1 · duration {d['duration']/US/60:.2f} min")
