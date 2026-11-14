"""CapCut draft engine — scan drafts, extract styles, inject caption tracks.

All timestamps are in microseconds (CapCut's native unit) unless noted.
Never writes a draft without creating a timestamped backup first.
"""
import copy
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import paths

DRAFTS_DIR = Path.home() / "Movies/CapCut/User Data/Projects/com.lveditor.draft"
BACKUP_PREFIX = "draft_info.ccstudio-backup-"
MAX_BACKUPS = 5
FFMPEG_BIN = str(paths.FFMPEG)


def _draft_file(draft_dir: Path) -> Path:
    """Newer CapCut versions use draft_info.json; older use draft_content.json."""
    for name in ("draft_info.json", "draft_content.json"):
        p = draft_dir / name
        if p.exists():
            return p
    raise FileNotFoundError(f"No draft json in {draft_dir}")


_pid_cache = {"t": 0.0, "pid": None}


def _capcut_pid() -> int | None:
    """PID of the running CapCut, cached ~2s — status polling and multi-write
    flows (a full treatment fires many guarded writes) shouldn't fork pgrep
    each time."""
    now = time.time()
    if now - _pid_cache["t"] > 2.0:
        out = subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True, text=True)
        pid = None
        if out.returncode == 0:
            try:
                pid = int(out.stdout.split()[0])
            except (ValueError, IndexError):
                pid = None
        _pid_cache.update(t=now, pid=pid)
    return _pid_cache["pid"]


def capcut_running() -> bool:
    return _capcut_pid() is not None


# ---- draft-scoped lock ------------------------------------------------------
# CapCut clobbers only the draft it has OPEN IN THE EDITOR (it saves that one
# from memory). Blocking every write whenever the process exists forced users
# to quit CapCut to work on a *different* project. Instead we lock a specific
# draft when either signal fires:
#   1. CapCut holds files open inside that draft's folder (lsof), or
#   2. the draft's json was saved recently (CapCut autosaves the open project
#      constantly; 90s of quiet after exit-to-home unlocks it) — ignoring
#      writes WE made, which also bump the mtime.
# Verified empirically: launch-to-home-screen holds zero draft files and
# touches zero drafts, so other projects stay writable while CapCut is open.

_lsof_cache = {"t": 0.0, "pid": None, "out": ""}
_own_writes: dict[str, float] = {}  # draft id → epoch of OUR last draft write
_RECENT_SAVE_S = 90.0


def _capcut_open_files(pid: int) -> str:
    now = time.time()
    if _lsof_cache["pid"] != pid or now - _lsof_cache["t"] > 2.0:
        try:
            r = subprocess.run(["lsof", "-nP", "-p", str(pid)],
                               capture_output=True, text=True, timeout=6)
            _lsof_cache.update(t=now, pid=pid, out=r.stdout or "")
        except Exception:
            _lsof_cache.update(t=now, pid=pid, out="")
    return _lsof_cache["out"]


def draft_locked(draft_id: str) -> bool:
    """True when writing this draft now risks being clobbered by CapCut."""
    pid = _capcut_pid()
    if pid is None:
        return False
    d = DRAFTS_DIR / draft_id
    if f"{d}/" in _capcut_open_files(pid):
        return True
    try:
        m = _draft_file(d).stat().st_mtime
        meta = d / "draft_meta_info.json"
        if meta.exists():
            m = max(m, meta.stat().st_mtime)
    except (FileNotFoundError, OSError):
        return True  # can't inspect it — stay safe
    if m <= _own_writes.get(draft_id, 0.0) + 1.5:
        return False  # the newest save is ours, not CapCut's
    return (time.time() - m) < _RECENT_SAVE_S


_TEXT_CACHE_PATH = Path(__file__).resolve().parent.parent / "drafts_cache.json"
_text_cache: dict | None = None


def _has_captions(draft_dir: Path) -> bool:
    """Whether the draft has any text track — cached by file mtime because
    parsing 100+ multi-MB drafts on every listing is too slow."""
    global _text_cache
    if _text_cache is None:
        try:
            _text_cache = json.loads(_TEXT_CACHE_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            _text_cache = {}
    f = _draft_file(draft_dir)
    mtime = f.stat().st_mtime
    cached = _text_cache.get(draft_dir.name)
    if cached and cached["mtime"] == mtime:
        return cached["has_text"]
    try:
        draft = json.loads(f.read_text())
        has_text = any(t.get("type") == "text" and t.get("segments")
                       for t in draft.get("tracks", []))
    except (OSError, json.JSONDecodeError):
        has_text = False
    _text_cache[draft_dir.name] = {"mtime": mtime, "has_text": has_text}
    try:
        _TEXT_CACHE_PATH.write_text(json.dumps(_text_cache))
    except OSError:
        pass
    return has_text


def extract_captions(draft_id: str) -> list[dict]:
    """All caption segments currently in the draft (any text track), for export."""
    draft = load_draft(draft_id)
    mats = {m["id"]: m for m in draft.get("materials", {}).get("texts", [])}
    out = []
    for track in draft.get("tracks", []):
        if track.get("type") != "text":
            continue
        for seg in track.get("segments", []):
            mat = mats.get(seg.get("material_id"))
            tgt = seg.get("target_timerange") or {}
            if not mat or not tgt.get("duration"):
                continue
            try:
                text = json.loads(mat["content"]).get("text", "").strip()
            except (json.JSONDecodeError, KeyError):
                continue
            if text:
                cap = {"text": text, "start_us": tgt["start"],
                       "duration_us": tgt["duration"]}
                w = mat.get("words") or {}
                if w.get("text"):
                    cap["words"] = [
                        {"text": t, "start_ms": int(a), "end_ms": int(b)}
                        for t, a, b in zip(w["text"], w["start_time"], w["end_time"])
                        if t.strip()  # skip the interleaved space entries
                    ]
                out.append(cap)
    out.sort(key=lambda c: c["start_us"])
    return out


def list_drafts() -> list[dict]:
    drafts = []
    if not DRAFTS_DIR.exists():
        return drafts
    for d in DRAFTS_DIR.iterdir():
        if not d.is_dir():
            continue
        try:
            _draft_file(d)
        except FileNotFoundError:
            continue
        meta = {}
        meta_path = d / "draft_meta_info.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        cover = d / "draft_cover.jpg"
        drafts.append({
            "id": d.name,
            "name": meta.get("draft_name", d.name),
            "duration_us": meta.get("tm_duration", 0),
            "modified_us": meta.get("tm_draft_modified", 0),
            "has_cover": cover.exists(),
            "has_text": _has_captions(d),
            "backups": len(list(d.glob(BACKUP_PREFIX + "*"))),
        })
    drafts.sort(key=lambda x: x["modified_us"], reverse=True)
    return drafts


def load_draft(draft_id: str) -> dict:
    return json.loads(_draft_file(DRAFTS_DIR / draft_id).read_text())


def cover_path(draft_id: str) -> Path | None:
    p = DRAFTS_DIR / draft_id / "draft_cover.jpg"
    return p if p.exists() else None


# ---------------------------------------------------------------- audio plan

_STILL_EXTS = (".image", ".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif")
_VIDEO_EXTS = (".mp4", ".mov", ".m4v", ".mts", ".avi", ".mkv", ".webm")


# ---------------------------------------------------------------- caption look

# font_size(×clip.scale) → text height as a fraction of canvas height. CapCut's
# internal unit isn't published, so this single scalar is calibrated by eye
# against the real CapCut preview; tune HERE if captions read too big/small.
FONT_PX_K = 8.0


def _hex_from_rgb01(rgb) -> str:
    try:
        return "#%02x%02x%02x" % tuple(
            max(0, min(255, round(float(c) * 255))) for c in list(rgb)[:3])
    except (TypeError, ValueError):
        return "#ffffff"


def caption_descriptor(material: dict, segment: dict,
                       canvas_w: int, canvas_h: int) -> dict:
    """Everything the preview overlay needs to draw a caption the way CapCut
    renders it: real colour, outline, shadow, alignment, on-canvas position and
    size — derived from the actual caption material + segment transform."""
    clip = (segment or {}).get("clip", {}) or {}
    tr = clip.get("transform", {}) or {}
    scale = (clip.get("scale", {}) or {}).get("x", 1.0) or 1.0
    font_size = material.get("font_size") or 10.0

    color = material.get("text_color") or "#ffffff"
    stroke = None
    try:
        st = json.loads(material["content"])["styles"][0]
        fill = (st.get("fill", {}).get("content", {})
                  .get("solid", {}).get("color"))
        if fill:
            color = _hex_from_rgb01(fill)
        strokes = st.get("strokes") or []
        if strokes:
            sc = (strokes[0].get("content", {})
                            .get("solid", {}).get("color", [0, 0, 0]))
            stroke = {"width": strokes[0].get("width", 0.0),
                      "color": _hex_from_rgb01(sc)}
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        pass
    if stroke is None and material.get("border_color") and material.get("border_width"):
        stroke = {"width": material.get("border_width", 0.0),
                  "color": material.get("border_color")}

    shadow = None
    if material.get("has_shadow"):
        shadow = {"color": material.get("shadow_color") or "#000000",
                  "alpha": material.get("shadow_alpha", 1.0),
                  "distance": material.get("shadow_distance", 0.0),
                  "angle": material.get("shadow_angle", -45.0)}

    align = {0: "left", 1: "center", 2: "right"}.get(material.get("alignment", 1), "center")

    # CapCut transform units are half-canvas, +x = right, +y = up. Convert to a
    # 0..1 fraction of the canvas from the top-left so the browser can place it.
    return {
        "canvas_w": canvas_w, "canvas_h": canvas_h,
        "color": color, "stroke": stroke, "shadow": shadow, "align": align,
        "pos_x": 0.5 + (tr.get("x", 0.0)) / 2.0,
        "pos_y": 0.5 - (tr.get("y", 0.0)) / 2.0,
        "size_frac": max(0.02, min(0.4, font_size * scale * FONT_PX_K / max(canvas_h, 1))),
        "has_font": bool(material.get("font_path")),
    }


def _is_speech_audio(mat: dict) -> bool:
    """Voiceover recordings and audio detached from a video carry speech.

    CapCut labels locally-imported music files "extract_music" too, so the
    type alone is not enough — genuine detached audio keeps the video's file
    extension, while imported music is .mp3/.wav/etc.
    """
    kind = mat.get("type")
    if kind == "record":
        return True
    if kind in ("extract_music", "extract"):
        return Path(mat.get("path", "")).suffix.lower() in _VIDEO_EXTS
    return False  # music / sound = library music and SFX


def _multicam_index(draft_dir: Path) -> dict:
    """Multi-camera clips keep their media inside subdraft/*/draft_content.json,
    nested as materials.drafts[].draft (a full inner timeline).

    Returns inner-track-id -> {path, inner mapping} for every camera/audio
    track found, so a main-draft segment can be mapped to real file time.
    """
    idx = {}
    for sub in sorted((draft_dir / "subdraft").glob("*/draft_content.json")):
        try:
            sd = json.loads(sub.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for drm in sd.get("materials", {}).get("drafts", []):
            inner = drm.get("draft") or {}
            mats = {}
            for lst in ("videos", "audios"):
                for m in inner.get("materials", {}).get(lst, []):
                    mats[m["id"]] = m
            for t in inner.get("tracks", []):
                if t.get("type") not in ("video", "audio") or not t.get("segments"):
                    continue
                seg = t["segments"][0]
                m = mats.get(seg.get("material_id"))
                if not m or not m.get("path"):
                    continue
                idx[t["id"]] = {
                    "path": m["path"],
                    "inner_src_start": (seg.get("source_timerange") or {}).get("start", 0),
                    "inner_tgt_start": (seg.get("target_timerange") or {}).get("start", 0),
                    "inner_speed": seg.get("speed", 1.0) or 1.0,
                }
    return idx


def _multicam_entries(seg: dict, mat: dict, mc_idx: dict) -> list[dict]:
    """Map a main-timeline multicam segment to the real recording file(s)."""
    mci = mat.get("multi_camera_info") or {}
    track_ids = mci.get("audio_open_track_id_list") or []
    if not track_ids and mci.get("cur_camera_track_id"):
        track_ids = [mci["cur_camera_track_id"]]
    src = seg.get("source_timerange") or {}
    tgt = seg.get("target_timerange") or {}
    entries = []
    for tid in track_ids:
        inner = mc_idx.get(tid)
        if not inner:
            continue
        speed = inner["inner_speed"]
        file_start = inner["inner_src_start"] + (src.get("start", 0) - inner["inner_tgt_start"]) * speed
        file_duration = src.get("duration", tgt.get("duration", 0)) * speed
        entries.append({
            "path": inner["path"],
            "source_start_us": int(file_start),
            "source_duration_us": int(file_duration),
            "target_start_us": tgt.get("start", 0),
            "target_duration_us": tgt.get("duration", 0),
            "speed": (seg.get("speed", 1.0) or 1.0) * speed,
            "volume": seg.get("volume", 1.0),
        })
    return entries


def video_plan(draft: dict, draft_id: str) -> dict:
    """What the timeline actually LOOKS like — the preview's source of truth.

    `audio_plan` answers "which file plays at time T", which is all transcription
    ever needed, and it is why the preview showed the raw 16:9 camera file for a
    9:16 reel: nothing in that plan says the canvas is vertical, that the clip is
    scaled to fill it, or that it's panned onto the speaker.

    This returns the composition instead: the canvas, every visual layer in track
    order (bottom first), and each layer's placement — so the client can rebuild
    the same frame CapCut will render. Photos (white spacers between reels, and
    logos) are INCLUDED: they're what you see in the gaps and the corners.
    """
    canvas = draft.get("canvas_config") or {}
    cw = canvas.get("width") or 1920
    ch = canvas.get("height") or 1080
    video_mats = {m["id"]: m for m in draft.get("materials", {}).get("videos", [])}
    mc_idx = _multicam_index(DRAFTS_DIR / draft_id)

    layers = []
    for track_i, track in enumerate(draft.get("tracks", [])):
        if track.get("type") != "video":
            continue
        for seg in track.get("segments", []):
            mat = video_mats.get(seg.get("material_id"))
            tgt = seg.get("target_timerange") or {}
            src = seg.get("source_timerange") or {}
            if not mat or not tgt.get("duration"):
                continue

            path, still = mat.get("path"), mat.get("type") == "photo"
            if not path and mat.get("multi_camera_info"):
                # the camera that is actually on screen in this cut
                cam = (mat["multi_camera_info"] or {}).get("cur_camera_track_id")
                inner = mc_idx.get(cam)
                if not inner:
                    continue
                speed = inner["inner_speed"]
                path = inner["path"]
                src = {"start": int(inner["inner_src_start"]
                                    + (src.get("start", 0) - inner["inner_tgt_start"]) * speed),
                       "duration": int(src.get("duration", 0) * speed)}
            if not path:
                continue

            clip = seg.get("clip") or {}
            scale = (clip.get("scale") or {}).get("x", 1.0)
            tr = clip.get("transform") or {}
            layers.append({
                "index": len(layers),
                "track": track_i,
                "kind": "photo" if still else "video",
                "path": path,
                "exists": Path(path).exists(),
                "target_start_us": tgt["start"],
                "target_duration_us": tgt["duration"],
                "source_start_us": src.get("start", 0),
                "source_duration_us": src.get("duration", tgt["duration"]),
                "speed": seg.get("speed", 1.0) or 1.0,
                # placement, in CapCut's own units: scale is relative to
                # fit-inside, transform is in half-canvas units with +y = UP
                "scale": scale,
                "tx": tr.get("x", 0.0),
                "ty": tr.get("y", 0.0),
                "mat_w": mat.get("width") or cw,
                "mat_h": mat.get("height") or ch,
            })

    layers.sort(key=lambda l: (l["track"], l["target_start_us"]))
    return {"canvas": {"width": cw, "height": ch},
            "duration_us": draft.get("duration", 0),
            "layers": layers}


def audio_plan(draft: dict, draft_id: str | None = None,
               include_music: bool = False) -> list[dict]:
    """Every speech-carrying segment placed on the timeline.

    Covers: all video tracks (skipping stills and muted b-roll), multi-camera
    clips (resolved through their subdraft), and voiceover / detached-audio
    tracks. Library music and SFX are excluded on purpose — UNLESS
    include_music is set, which the preview mix uses to hear the full episode
    (voice + music + SFX) exactly as it sits on the timeline.
    """
    video_mats = {m["id"]: m for m in draft.get("materials", {}).get("videos", [])}
    audio_mats = {m["id"]: m for m in draft.get("materials", {}).get("audios", [])}
    mc_idx = None
    plan = []
    for track in draft.get("tracks", []):
        ttype = track.get("type")
        if ttype not in ("video", "audio"):
            continue
        for seg in track.get("segments", []):
            if seg.get("volume", 1.0) == 0:
                continue  # muted b-roll / camera layer
            src = seg.get("source_timerange") or {}
            tgt = seg.get("target_timerange") or {}
            if not tgt.get("duration"):
                continue
            if ttype == "video":
                mat = video_mats.get(seg.get("material_id"))
                if not mat:
                    continue
                if mat.get("has_audio") is False:
                    continue
                if not mat.get("path") and mat.get("multi_camera_info"):
                    if mc_idx is None:
                        mc_idx = _multicam_index(DRAFTS_DIR / draft_id) if draft_id else {}
                    plan.extend(_multicam_entries(seg, mat, mc_idx))
                    continue
                if not mat.get("path"):
                    continue
                if mat.get("type") == "photo" or Path(mat["path"]).suffix.lower() in _STILL_EXTS:
                    continue
            else:
                mat = audio_mats.get(seg.get("material_id"))
                if not mat or not mat.get("path"):
                    continue
                if not include_music and not _is_speech_audio(mat):
                    continue
            plan.append({
                "path": mat["path"],
                "source_start_us": src.get("start", 0),
                "source_duration_us": src.get("duration", tgt.get("duration")),
                "target_start_us": tgt["start"],
                "target_duration_us": tgt["duration"],
                "speed": seg.get("speed", 1.0) or 1.0,
                "volume": seg.get("volume", 1.0),
            })
    plan.sort(key=lambda s: s["target_start_us"])
    return plan


# ---------------------------------------------------------------- styles

def list_text_tracks(draft: dict) -> list[dict]:
    """Summaries of text tracks so the user can pick a style donor."""
    mats = {m["id"]: m for m in draft.get("materials", {}).get("texts", [])}
    out = []
    for ti, track in enumerate(draft.get("tracks", [])):
        if track.get("type") != "text" or not track.get("segments"):
            continue
        seg = track["segments"][0]
        mat = mats.get(seg.get("material_id"))
        if not mat:
            continue
        try:
            sample = json.loads(mat["content"]).get("text", "")
        except (json.JSONDecodeError, KeyError):
            sample = ""
        out.append({
            "track_index": ti,
            "segment_count": len(track["segments"]),
            "sample_text": sample,
            "font": mat.get("font_title") or mat.get("font_name") or "system",
        })
    return out


def extract_style(draft_id: str, track_index: int) -> dict:
    """Deep-copy everything needed to recreate a caption in this exact look."""
    draft = load_draft(draft_id)
    track = draft["tracks"][track_index]
    if track.get("type") != "text":
        raise ValueError("not a text track")
    seg = copy.deepcopy(track["segments"][0])
    mats = draft.get("materials", {})
    material = None
    for m in mats.get("texts", []):
        if m["id"] == seg["material_id"]:
            material = copy.deepcopy(m)
            break
    if material is None:
        raise ValueError("donor text material not found")
    # everything the donor segment references (animations etc.), keyed by the
    # materials-dict list it lives in, so injection can clone it back in place
    extras = []
    for ref in seg.get("extra_material_refs", []):
        for list_name, lst in mats.items():
            if not isinstance(lst, list):
                continue
            for m in lst:
                if isinstance(m, dict) and m.get("id") == ref:
                    extras.append({"list": list_name, "material": copy.deepcopy(m)})
    try:
        sample = json.loads(material["content"]).get("text", "")
    except (json.JSONDecodeError, KeyError):
        sample = ""
    return {
        "source_draft": draft_id,
        "sample_text": sample,
        "segment_template": seg,
        "material_template": material,
        "extra_materials": extras,
    }


# ---------------------------------------------------------------- color / LUT

def _materials_index(draft: dict) -> dict:
    idx = {}
    for lname, lst in draft.get("materials", {}).items():
        if isinstance(lst, list):
            for m in lst:
                if isinstance(m, dict) and "id" in m:
                    idx[m["id"]] = (lname, m)
    return idx


def extract_color(draft_id: str) -> dict:
    """Clone a draft's whole color setup: adjust layers + segment LUTs."""
    draft = load_draft(draft_id)
    idx = _materials_index(draft)
    preset = {"source_draft": draft_id, "adjust_layers": [], "lut": None}
    for track in draft.get("tracks", []):
        if track.get("type") != "adjust" or not track.get("segments"):
            continue
        seg = copy.deepcopy(track["segments"][0])
        material = None
        extras = []
        lname_mat = idx.get(seg.get("material_id"))
        if lname_mat:
            material = {"list": lname_mat[0], "material": copy.deepcopy(lname_mat[1])}
        for ref in seg.get("extra_material_refs", []):
            hit = idx.get(ref)
            if hit:
                extras.append({"list": hit[0], "material": copy.deepcopy(hit[1])})
        preset["adjust_layers"].append(
            {"segment": seg, "material": material, "extras": extras})
    # a LUT enabled on any video segment (they all share the same effect)
    for track in draft.get("tracks", []):
        if track.get("type") != "video":
            continue
        for seg in track.get("segments", []):
            if not seg.get("enable_lut"):
                continue
            for ref in seg.get("extra_material_refs", []):
                hit = idx.get(ref)
                if hit and hit[1].get("type") == "lut":
                    preset["lut"] = copy.deepcopy(hit[1])
                    break
            if preset["lut"]:
                break
        if preset["lut"]:
            break
    if not preset["adjust_layers"] and not preset["lut"]:
        raise ValueError("no_color_setup")
    return preset


def apply_color(draft_id: str, preset: dict, replace_existing: bool = True) -> dict:
    """Apply a cloned color preset: adjust layers span the full timeline,
    the LUT is enabled on every video segment."""
    if draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    draft_dir = DRAFTS_DIR / draft_id
    draft = load_draft(draft_id)
    backup = _backup(draft_dir)
    mats = draft.setdefault("materials", {})
    applied = {"adjust_layers": 0, "lut_segments": 0}

    if replace_existing:
        removed = set()
        for track in [t for t in draft["tracks"] if t.get("type") == "adjust"]:
            for s in track.get("segments", []):
                removed.add(s.get("material_id"))
                removed.update(s.get("extra_material_refs", []))
        draft["tracks"] = [t for t in draft["tracks"] if t.get("type") != "adjust"]
        for lname, lst in mats.items():
            if isinstance(lst, list):
                mats[lname] = [m for m in lst
                               if not (isinstance(m, dict) and m.get("id") in removed)]

    for layer in preset.get("adjust_layers", []):
        seg = copy.deepcopy(layer["segment"])
        seg["id"] = _new_id()
        if layer.get("material"):
            mat = copy.deepcopy(layer["material"]["material"])
            mat["id"] = _new_id()
            mats.setdefault(layer["material"]["list"], []).append(mat)
            seg["material_id"] = mat["id"]
        refs = []
        for extra in layer.get("extras", []):
            clone = copy.deepcopy(extra["material"])
            clone["id"] = _new_id()
            mats.setdefault(extra["list"], []).append(clone)
            refs.append(clone["id"])
        seg["extra_material_refs"] = refs
        seg["target_timerange"] = {"start": 0, "duration": draft.get("duration", 0)}
        draft["tracks"].append({
            "attribute": 0, "flag": 0, "id": _new_id(), "is_default_name": True,
            "name": "", "segments": [seg], "type": "adjust",
        })
        applied["adjust_layers"] += 1

    if preset.get("lut"):
        for track in draft.get("tracks", []):
            if track.get("type") != "video":
                continue
            for seg in track.get("segments", []):
                lut = copy.deepcopy(preset["lut"])
                lut["id"] = _new_id()
                mats.setdefault("effects", []).append(lut)
                seg.setdefault("extra_material_refs", []).append(lut["id"])
                seg["enable_lut"] = True
                applied["lut_segments"] += 1

    path = _draft_file(draft_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(draft, ensure_ascii=False, separators=(",", ":")))
    json.loads(tmp.read_text())
    tmp.replace(path)
    applied["backup"] = backup.name
    return applied


# ---------------------------------------------------------------- logos

_LOGO_SKIP_NAMES = {"白", "黑"}  # CapCut's built-in white/black cards
_LOGO_FILE_PREFIX = "ccstudio-logo"


def extract_logos(draft_id: str, min_cover: float = 0.25) -> list[dict]:
    """Learn a draft's persistent image overlays (logos): photo materials whose
    segments cover a meaningful share of the timeline. Snapshot material +
    representative segment + extras, donor-clone style."""
    draft = load_draft(draft_id)
    duration = draft.get("duration", 0)
    if not duration:
        raise ValueError("no_duration")
    idx = _materials_index(draft)
    photos = {m["id"]: m for m in draft.get("materials", {}).get("videos", [])
              if m.get("type") == "photo"}
    covered: dict[str, int] = {}
    best: dict[str, dict] = {}
    for track in draft.get("tracks", []):
        if track.get("type") != "video":
            continue
        for seg in track.get("segments", []):
            mat = photos.get(seg.get("material_id"))
            if not mat:
                continue
            name = mat.get("material_name") or mat.get("name") or ""
            if name in _LOGO_SKIP_NAMES or name.startswith("ccstudio-"):
                continue
            dur = (seg.get("target_timerange") or {}).get("duration", 0)
            mid = mat["id"]
            covered[mid] = covered.get(mid, 0) + dur
            prev = best.get(mid)
            if not prev or dur > (prev.get("target_timerange") or {}).get("duration", 0):
                best[mid] = seg
    logos = []
    for mid, total in covered.items():
        if total < min_cover * duration:
            continue
        mat, seg = photos[mid], best[mid]
        extras = []
        for ref in seg.get("extra_material_refs", []):
            hit = idx.get(ref)
            if hit:
                extras.append({"list": hit[0], "material": copy.deepcopy(hit[1])})
        logos.append({"name": mat.get("material_name") or mat.get("name") or "logo",
                      "path": mat.get("path", ""),
                      "material": copy.deepcopy(mat),
                      "segment": copy.deepcopy(seg),
                      "extras": extras})
    if not logos:
        raise ValueError("no_logos")
    return logos


def apply_logos(draft_id: str, logos: list[dict], replace_existing: bool = True) -> dict:
    """Clone learned logo overlays into a draft, each on its own top track
    spanning the full timeline. The image file is copied into the draft folder
    so the preset survives moved originals."""
    if draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    draft_dir = DRAFTS_DIR / draft_id
    draft = load_draft(draft_id)
    duration = draft.get("duration", 0)
    backup = _backup(draft_dir)
    mats = draft.setdefault("materials", {})

    if replace_existing:
        logo_mids = {m["id"] for m in mats.get("videos", [])
                     if (m.get("material_name") or "").startswith(_LOGO_FILE_PREFIX)}
        removed_refs = set(logo_mids)
        kept = []
        for track in draft.get("tracks", []):
            segs = track.get("segments", [])
            if track.get("type") == "video" and segs and \
                    all(s.get("material_id") in logo_mids for s in segs):
                for s in segs:
                    removed_refs.update(s.get("extra_material_refs", []))
                continue
            kept.append(track)
        draft["tracks"] = kept
        for lname, lst in mats.items():
            if isinstance(lst, list):
                mats[lname] = [m for m in lst
                               if not (isinstance(m, dict) and m.get("id") in removed_refs)]

    applied, skipped = 0, []
    for i, logo in enumerate(logos):
        src = Path(logo.get("path", ""))
        if not src.exists():
            skipped.append(logo.get("name", "?"))
            continue
        local_name = f"{_LOGO_FILE_PREFIX}-{i}{src.suffix.lower() or '.png'}"
        local = draft_dir / local_name
        if src != local:
            shutil.copy2(src, local)
        mat = copy.deepcopy(logo["material"])
        mat.update({"id": _new_id(), "path": str(local),
                    "material_name": local_name})
        if "name" in mat:
            mat["name"] = local_name
        mat["duration"] = max(mat.get("duration", 0), duration)
        mats.setdefault("videos", []).append(mat)
        seg = copy.deepcopy(logo["segment"])
        refs = []
        for extra in logo.get("extras", []):
            clone = copy.deepcopy(extra["material"])
            clone["id"] = _new_id()
            mats.setdefault(extra["list"], []).append(clone)
            refs.append(clone["id"])
        seg.update({"id": _new_id(), "material_id": mat["id"],
                    "extra_material_refs": refs,
                    "target_timerange": {"start": 0, "duration": duration},
                    "source_timerange": {"start": 0, "duration": duration},
                    "common_keyframes": [], "keyframe_refs": []})
        draft["tracks"].append({
            "attribute": 0, "flag": 0, "id": _new_id(), "is_default_name": True,
            "name": "", "segments": [seg], "type": "video",
        })
        applied += 1
    if applied:
        _atomic_write(draft_dir, draft)
    return {"applied": applied, "skipped": skipped, "backup": backup.name}


# ---------------------------------------------------------------- injection

def _backup(draft_dir: Path) -> Path:
    src = _draft_file(draft_dir)
    dst = draft_dir / f"{BACKUP_PREFIX}{int(time.time())}.json"
    shutil.copy2(src, dst)
    backups = sorted(draft_dir.glob(BACKUP_PREFIX + "*"))
    for old in backups[:-MAX_BACKUPS]:
        old.unlink()
    return dst


def restore_backup(draft_id: str, name: str | None = None) -> str:
    """Restore a specific backup (or the newest) — atomically, with parse-back."""
    draft_dir = DRAFTS_DIR / draft_id
    backups = sorted(draft_dir.glob(BACKUP_PREFIX + "*"))
    if not backups:
        raise FileNotFoundError("no backups for this draft")
    chosen = next((b for b in backups if b.name == name), None) if name else backups[-1]
    if chosen is None:
        raise FileNotFoundError("backup not found")
    data = json.loads(chosen.read_text())  # never install a corrupt backup
    path = _draft_file(draft_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    tmp.replace(path)
    return chosen.name


def _new_id() -> str:
    return str(uuid.uuid4()).upper()


def _set_text(material: dict, text: str, words: list[dict] | None) -> None:
    """Rewrite the donor material's text payload, keeping every style byte."""
    for field in ("content", "base_content"):
        if not material.get(field):
            continue
        try:
            payload = json.loads(material[field])
        except json.JSONDecodeError:
            continue
        payload["text"] = text
        for style in payload.get("styles", []):
            if "range" in style:
                style["range"] = [0, len(text)]
        material[field] = json.dumps(payload, ensure_ascii=False)
    if "recognize_text" in material:
        material["recognize_text"] = text
    # per-word timings (ms, relative to segment start), spaces interleaved,
    # matching CapCut's native subtitle format
    if "words" in material:
        starts, ends, texts = [], [], []
        for i, w in enumerate(words or []):
            if i > 0:
                starts.append(ends[-1])
                ends.append(w["start_ms"])
                texts.append(" ")
            starts.append(w["start_ms"])
            ends.append(w["end_ms"])
            texts.append(w["text"])
        material["words"] = {"start_time": starts, "end_time": ends, "text": texts}


def inject_captions(draft_id: str, captions: list[dict], style: dict,
                    replace_existing: bool = False) -> dict:
    """Add a text track with one segment per caption, styled like the donor.

    captions: [{text, start_us, duration_us, words: [{text, start_ms, end_ms}]}]
    words timings are relative to the caption start.
    """
    if draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    draft_dir = DRAFTS_DIR / draft_id
    draft = load_draft(draft_id)
    backup = _backup(draft_dir)

    if replace_existing:
        # Replace CAPTION tracks only. A text track holding a title-length
        # segment (a headline spanning much of the video) is a design element,
        # not captions — flattening it into caption style would destroy it.
        def _is_title_track(t):
            return any((s.get("target_timerange") or {}).get("duration", 0) > 25_000_000
                       for s in t.get("segments", []))
        removed_mat_ids = set()
        for track in [t for t in draft["tracks"]
                      if t.get("type") == "text" and not _is_title_track(t)]:
            removed_mat_ids.update(s.get("material_id") for s in track.get("segments", []))
            for s in track.get("segments", []):
                removed_mat_ids.update(s.get("extra_material_refs", []))
        draft["tracks"] = [t for t in draft["tracks"]
                           if t.get("type") != "text" or _is_title_track(t)]
        for list_name, lst in draft.get("materials", {}).items():
            if isinstance(lst, list):
                draft["materials"][list_name] = [
                    m for m in lst
                    if not (isinstance(m, dict) and m.get("id") in removed_mat_ids)
                ]

    mats = draft.setdefault("materials", {})
    seg_tpl = style["segment_template"]
    mat_tpl = style["material_template"]

    segments = []
    for cap in captions:
        text = cap["text"].strip()
        if not text:
            continue
        material = copy.deepcopy(mat_tpl)
        material["id"] = _new_id()
        _set_text(material, text, cap.get("words"))
        mats.setdefault("texts", []).append(material)

        extra_refs = []
        for extra in style.get("extra_materials", []):
            clone = copy.deepcopy(extra["material"])
            clone["id"] = _new_id()
            mats.setdefault(extra["list"], []).append(clone)
            extra_refs.append(clone["id"])

        seg = copy.deepcopy(seg_tpl)
        seg["id"] = _new_id()
        seg["material_id"] = material["id"]
        seg["extra_material_refs"] = extra_refs
        seg["target_timerange"] = {"start": int(cap["start_us"]),
                                   "duration": int(cap["duration_us"])}
        segments.append(seg)

    track = {
        "attribute": 0,
        "flag": 0,
        "id": _new_id(),
        "is_default_name": True,
        "name": "",
        "segments": segments,
        "type": "text",
    }
    draft["tracks"].append(track)

    path = _draft_file(draft_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(draft, ensure_ascii=False, separators=(",", ":")))
    # sanity: the file we are about to install must parse back
    json.loads(tmp.read_text())
    tmp.replace(path)
    return {"injected": len(segments), "backup": backup.name}


# ---------------------------------------------------------------- AI ops

def _atomic_write(draft_dir: Path, draft: dict) -> None:
    # second guard: slow steps (VAD, model) may run between the entry check
    # and this write — CapCut editing THIS draft meanwhile would clobber us
    if draft_locked(draft_dir.name):
        raise RuntimeError("capcut_running")
    path = _draft_file(draft_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(draft, ensure_ascii=False, separators=(",", ":")))
    json.loads(tmp.read_text())  # must parse back before installing
    tmp.replace(path)
    # our own save must not read as "CapCut touched this draft" to the lock
    _own_writes[draft_dir.name] = time.time()


def set_camera(draft_id: str, changes: list[dict]) -> dict:
    """Switch the active camera of multicam cuts.

    changes: [{segment_index, camera_id}] — indexes follow timeline order of
    multicam segments (the same order the AI context lists them in).
    """
    if draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    draft_dir = DRAFTS_DIR / draft_id
    draft = load_draft(draft_id)
    backup = _backup(draft_dir)
    mats = {m["id"]: m for m in draft.get("materials", {}).get("videos", [])}
    # multicam materials in timeline order — same order the AI context uses
    timed = []
    for track in draft.get("tracks", []):
        if track.get("type") != "video":
            continue
        for seg in track.get("segments", []):
            mat = mats.get(seg.get("material_id"))
            if mat and not mat.get("path") and mat.get("multi_camera_info"):
                timed.append(((seg.get("target_timerange") or {}).get("start", 0), mat))
    timed.sort(key=lambda x: x[0])
    changed = 0
    for ch in changes:
        idx = ch.get("segment_index")
        cam = ch.get("camera_id")
        if idx is None or cam is None or not (0 <= idx < len(timed)):
            continue
        mci = timed[idx][1].get("multi_camera_info") or {}
        if mci.get("cur_camera_track_id") != cam:
            mci["cur_camera_track_id"] = cam
            changed += 1
    _atomic_write(draft_dir, draft)
    return {"changed": changed, "backup": backup.name}


def update_caption_texts(draft_id: str, changes: list[dict]) -> dict:
    """Fix the TEXT of existing captions in place — style, timing, animations
    and track structure stay untouched, so it works on CapCut-native captions
    the app never injected.

    changes: [{index, text}] — index is the caption's position in
    extract_captions() order (start_us-sorted), the same order the AI context
    and the editor list them in.
    """
    if draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    draft_dir = DRAFTS_DIR / draft_id
    draft = load_draft(draft_id)
    backup = _backup(draft_dir)
    mats = {m["id"]: m for m in draft.get("materials", {}).get("texts", [])}
    refs = []  # (start_us, duration_us, material, current_text) in caption order
    for track in draft.get("tracks", []):
        if track.get("type") != "text":
            continue
        for seg in track.get("segments", []):
            mat = mats.get(seg.get("material_id"))
            tgt = seg.get("target_timerange") or {}
            if not mat or not tgt.get("duration"):
                continue
            try:
                text = json.loads(mat["content"]).get("text", "").strip()
            except (json.JSONDecodeError, KeyError):
                continue
            if text:
                refs.append((tgt["start"], tgt["duration"], mat, text))
    refs.sort(key=lambda r: r[0])
    changed = 0
    for ch in changes:
        idx = ch.get("index")
        new_text = (ch.get("text") or "").strip()
        if not isinstance(idx, int) or not (0 <= idx < len(refs)) or not new_text:
            continue
        _start, dur_us, mat, old_text = refs[idx]
        if new_text == old_text:
            continue
        # keep per-word karaoke timing when the token count survives the fix,
        # otherwise spread the caption's duration proportionally by char
        w = mat.get("words") or {}
        old_words = [{"text": t, "start_ms": int(a), "end_ms": int(b)}
                     for t, a, b in zip(w.get("text", []), w.get("start_time", []),
                                        w.get("end_time", []))
                     if t.strip()]
        tokens = new_text.split()
        if len(old_words) == len(tokens):
            words = [{**ow, "text": t} for ow, t in zip(old_words, tokens)]
        else:
            total = sum(len(t) for t in tokens) or 1
            dur_ms = dur_us // 1000
            words, cursor = [], 0
            for t in tokens:
                a = int(dur_ms * cursor / total)
                cursor += len(t)
                words.append({"text": t, "start_ms": a,
                              "end_ms": int(dur_ms * cursor / total)})
        _set_text(mat, new_text, words if old_words else None)
        changed += 1
    _atomic_write(draft_dir, draft)
    return {"changed": changed, "backup": backup.name}


def apply_fades(draft_id: str, fade_ms: int) -> dict:
    """Gentle audio fade in/out on every sound-carrying segment.

    Replaces any existing audio_fade on the segment (no duplicates)."""
    if draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    draft_dir = DRAFTS_DIR / draft_id
    draft = load_draft(draft_id)
    backup = _backup(draft_dir)
    mats = draft.setdefault("materials", {})
    fades = mats.setdefault("audio_fades", [])
    fade_ids = {f["id"] for f in fades if isinstance(f, dict)}
    fade_us = int(fade_ms * 1000)
    video_mats = {m["id"]: m for m in mats.get("videos", [])}
    count = 0
    for track in draft.get("tracks", []):
        ttype = track.get("type")
        if ttype not in ("video", "audio"):
            continue
        for seg in track.get("segments", []):
            if seg.get("volume", 1.0) == 0:
                continue
            if ttype == "video":
                mat = video_mats.get(seg.get("material_id"))
                if not mat or mat.get("has_audio") is False:
                    continue
                if mat.get("type") == "photo":
                    continue
            dur = (seg.get("target_timerange") or {}).get("duration", 0)
            if dur < fade_us * 2:
                continue
            refs = [r for r in seg.get("extra_material_refs", []) if r not in fade_ids]
            fade = {"id": _new_id(), "type": "audio_fade", "fade_type": 0,
                    "fade_in_duration": fade_us, "fade_out_duration": fade_us}
            fades.append(fade)
            refs.append(fade["id"])
            seg["extra_material_refs"] = refs
            count += 1
    # drop fade materials nothing references anymore
    used = set()
    for track in draft.get("tracks", []):
        for seg in track.get("segments", []):
            used.update(seg.get("extra_material_refs") or [])
    mats["audio_fades"] = [f for f in fades if f["id"] in used]
    _atomic_write(draft_dir, draft)
    return {"segments": count, "backup": backup.name}


def apply_punchins(draft_id: str, zooms: list[dict]) -> dict:
    """Static zoom on the video cut containing each moment — the classic
    podcast punch-in. zooms: [{time_us, scale}] (scale multiplies current)."""
    if draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    draft_dir = DRAFTS_DIR / draft_id
    draft = load_draft(draft_id)
    backup = _backup(draft_dir)
    video_mats = {m["id"]: m for m in draft.get("materials", {}).get("videos", [])}
    segs = []
    for track in draft.get("tracks", []):
        if track.get("type") != "video":
            continue
        for seg in track.get("segments", []):
            mat = video_mats.get(seg.get("material_id")) or {}
            if mat.get("type") == "photo":
                continue
            tgt = seg.get("target_timerange") or {}
            segs.append((tgt.get("start", 0),
                         tgt.get("start", 0) + tgt.get("duration", 0), seg))
    changed, seen = 0, set()
    for z in zooms:
        t, factor = int(z["time_us"]), float(z.get("scale", 1.08))
        for a, b, seg in segs:
            if a <= t < b and seg["id"] not in seen:
                seen.add(seg["id"])
                clip = seg.setdefault("clip", {})
                cur = (clip.get("scale") or {}).get("x", 1.0) or 1.0
                clip["scale"] = {"x": cur * factor, "y": cur * factor}
                changed += 1
                break
    _atomic_write(draft_dir, draft)
    return {"changed": changed, "backup": backup.name}


# ---------------------------------------------------------------- add audio

def _audio_donor() -> tuple[dict, dict, list]:
    """A plain audio clip (material, segment, extras) cloned from any draft —
    the safe way to add an audio track without hand-writing CapCut's schema."""
    for d in list_drafts():
        try:
            draft = load_draft(d["id"])
        except (OSError, json.JSONDecodeError):
            continue
        mats = {m["id"]: m for m in draft.get("materials", {}).get("audios", [])}
        idx = _materials_index(draft)
        for track in draft.get("tracks", []):
            if track.get("type") != "audio":
                continue
            for seg in track.get("segments", []):
                mat = mats.get(seg.get("material_id"))
                if mat and mat.get("path"):
                    extras = [{"list": idx[r][0], "material": idx[r][1]}
                              for r in seg.get("extra_material_refs", []) if r in idx]
                    return copy.deepcopy(mat), copy.deepcopy(seg), copy.deepcopy(extras)
    raise RuntimeError("לא נמצא דונור אודיו — הוסף פעם אחת מוזיקה כלשהי בקאפקאט כדי שאלמד את המבנה")


def _probe_audio_dur_us(path: Path) -> int:
    out = subprocess.run([FFMPEG_BIN, "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True)
    idx = out.stderr.find("Duration:")
    if idx < 0:
        return 0
    try:
        h, m, s = out.stderr[idx + 9:idx + 21].strip().split(",")[0].split(":")
        return int((int(h) * 3600 + int(m) * 60 + float(s)) * 1e6)
    except (ValueError, IndexError):
        return 0


def _clone_extras(mats: dict, donor_extras: list) -> list:
    refs = []
    for ex in donor_extras:
        clone = copy.deepcopy(ex["material"])
        clone["id"] = _new_id()
        mats.setdefault(ex["list"], []).append(clone)
        refs.append(clone["id"])
    return refs


def add_audio(draft_id: str, file_path: str, name: str = "", *,
              at_us: int = 0, duration_us: int | None = None,
              volume: float = 1.0, loop_to_fill: bool = False,
              kind: str = "music") -> dict:
    """Place an audio file on the project as a NEW track.

    music: loop_to_fill spreads it from at_us to the end of the episode.
    sfx:   a single hit at at_us. The file is copied INTO the draft folder so
    the project stays self-contained (same as logos). Caller should run ducking
    afterwards for music."""
    if draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    src = Path(file_path)
    if not src.exists():
        raise RuntimeError("קובץ האודיו לא נמצא")
    draft_dir = DRAFTS_DIR / draft_id
    draft = load_draft(draft_id)

    asset_dur = int(duration_us or 0) or _probe_audio_dur_us(src)
    if asset_dur <= 0:
        raise RuntimeError("לא הצלחתי לקרוא את אורך קובץ האודיו")
    episode_dur = int(draft.get("duration", 0) or 0)

    donor_mat, donor_seg, donor_extras = _audio_donor()
    backup = _backup(draft_dir)

    aid = _new_id()[:8]
    dest = draft_dir / f"ccstudio-audio-{aid}{src.suffix.lower()}"
    shutil.copy(src, dest)

    mats = draft.setdefault("materials", {})
    mat = copy.deepcopy(donor_mat)
    mat.update({"id": _new_id(), "path": str(dest),
                "name": name or src.stem, "material_name": name or src.stem,
                "duration": asset_dur, "type": "extract_music"})
    mats.setdefault("audios", []).append(mat)

    # build one or more segments on the timeline
    segments = []
    if kind == "music" and loop_to_fill and episode_dur > at_us:
        cursor = int(at_us)
        while cursor < episode_dur:
            seg_dur = min(asset_dur, episode_dur - cursor)
            seg = copy.deepcopy(donor_seg)
            seg.update({"id": _new_id(), "material_id": mat["id"],
                        "extra_material_refs": _clone_extras(mats, donor_extras),
                        "volume": volume, "speed": 1.0,
                        "target_timerange": {"start": cursor, "duration": seg_dur},
                        "source_timerange": {"start": 0, "duration": seg_dur},
                        "common_keyframes": []})
            segments.append(seg)
            cursor += seg_dur
    else:
        seg_dur = asset_dur if duration_us is None else min(asset_dur, int(duration_us))
        seg = copy.deepcopy(donor_seg)
        seg.update({"id": _new_id(), "material_id": mat["id"],
                    "extra_material_refs": _clone_extras(mats, donor_extras),
                    "volume": volume, "speed": 1.0,
                    "target_timerange": {"start": int(at_us), "duration": seg_dur},
                    "source_timerange": {"start": 0, "duration": seg_dur},
                    "common_keyframes": []})
        segments.append(seg)

    draft.setdefault("tracks", []).append({
        "attribute": 0, "flag": 0, "id": _new_id(),
        "is_default_name": True, "name": "", "segments": segments, "type": "audio",
    })
    _atomic_write(draft_dir, draft)
    return {"segments": len(segments), "kind": kind,
            "name": mat["name"], "at_us": int(at_us),
            "looped": kind == "music" and loop_to_fill and len(segments) > 1,
            "backup": backup.name}
