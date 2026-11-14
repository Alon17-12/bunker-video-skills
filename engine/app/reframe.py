"""Auto-reframe — keep the speaker centred when landscape footage goes 9:16.

Without this, a 16:9 cut dropped on a 9:16 canvas is simply blown up and
centre-cropped: the speaker drifts to the edge (or out of frame) whenever they
aren't dead-centre in the original shot. This module looks at the footage,
finds the face, and pans the frame so the speaker sits in the middle.

Geometry (calibrated against 125 real CapCut drafts, see tests/test_reframe.py):
  * `clip.scale` 1.0 means FIT-INSIDE, so filling a 9:16 canvas with 16:9
    footage takes scale 3.1605 — CapCut's own number for exactly this case.
  * `clip.transform.x` is in HALF-CANVAS-WIDTH units, positive = right. At cover
    scale the source's full height already fills the canvas, so there is no
    vertical freedom to spend: this is a pure horizontal pan and transform.y
    stays 0.

Per cut we take the MEDIAN face position across sampled frames — one static
transform per segment, no keyframes. A median shrugs off a false positive on a
bookshelf, and a static frame can never judder.
"""
import shutil
import statistics
import subprocess
import tempfile
from pathlib import Path

import cv2

import capcut
import paths

CANVAS_W, CANVAS_H = 1080, 1920
FFMPEG = paths.FFMPEG
# shipped read-only with the app (227KB) — not the 1.6GB speech model, which
# downloads into the writable data dir
YUNET = paths.RESOURCE_DIR / "models" / "face_detection_yunet_2023mar.onnx"

SAMPLE_FPS = 2.0        # frames per second of cut we look at
MAX_FRAMES = 24         # cap per cut — long cuts don't need more evidence
FRAME_W = 640           # detect on a downscale; face position is a fraction
SCORE_MIN = 0.75        # YuNet confidence
MIN_FACE_W = 0.03       # ignore specks (reflections, faces in a poster)
MIN_HIT_RATE = 0.30     # < 30% of frames with a face -> don't trust it
DEADZONE = 0.01         # already within 1% of centre -> leave it alone.
                        # Was 3%, and it silently ate a real miss: camera 1 of the
                        # צומת 20 pilot sits at face_x=0.472 — 2.8% off, just under
                        # the old threshold — so 8 of 17 cuts kept the speaker 100px
                        # left of centre and the result read as "it just zoomed in".
                        # Per-camera locking already kills jitter, so this can be tight.
PAIR_FIT = 0.90         # a pair must fit inside 90% of the window to be framed together
CLUSTER_GAP = 0.12      # faces more than 12% of the width apart are different people
MIN_PRESENCE = 0.25     # a person must appear in 25% of the cut's frames to count
LOCK_SPREAD = 0.08      # a camera whose face position varies less than this is
                        # a locked-off tripod -> give all its cuts ONE framing


# --------------------------------------------------------------------------
# geometry — pure, tested
# --------------------------------------------------------------------------

def fill_scale(w: int, h: int, cw: int = CANVAS_W, ch: int = CANVAS_H) -> float:
    """CapCut scale=1.0 is fit-inside; this returns the cover (fill) factor."""
    if not w or not h:
        w, h = 1920, 1080
    return max(cw / w, ch / h) / min(cw / w, ch / h)


def rendered_width(w: int, h: int, cw: int = CANVAS_W, ch: int = CANVAS_H) -> float:
    """On-canvas width of the footage once it fills the canvas."""
    if not w or not h:
        w, h = 1920, 1080
    return w * max(cw / w, ch / h)


def max_transform_x(w: int, h: int, cw: int = CANVAS_W, ch: int = CANVAS_H) -> float:
    """Pan budget: how far we can travel before a black edge appears."""
    hidden_per_side = max(0.0, (rendered_width(w, h, cw, ch) - cw) / 2)
    return hidden_per_side / (cw / 2)


def transform_x(fx: float, w: int, h: int,
                cw: int = CANVAS_W, ch: int = CANVAS_H) -> float:
    """Pan needed to bring a face at fraction `fx` of the source width to centre."""
    limit = max_transform_x(w, h, cw, ch)
    if limit <= 0:
        return 0.0  # vertical footage: nothing to pan
    x = -(fx - 0.5) * rendered_width(w, h, cw, ch) / (cw / 2)
    return max(-limit, min(limit, x))


def window_fraction(w: int, h: int, cw: int = CANVAS_W, ch: int = CANVAS_H) -> float:
    """How much of the source width survives the crop (16:9 -> 9:16 = 31.6%)."""
    return min(1.0, cw / rendered_width(w, h, cw, ch))


# --------------------------------------------------------------------------
# decisions — pure, tested
# --------------------------------------------------------------------------

def cluster_faces(faces_per_frame: list[list[dict]], n_frames: int,
                  gap: float = CLUSTER_GAP,
                  min_presence: float = MIN_PRESENCE) -> list[dict]:
    """Group every face seen in a cut into PEOPLE, not frames.

    A detector looking at a two-person wide shot rarely finds both faces in the
    same frame — it flickers between them as they turn and gesture. Judging each
    frame on its own therefore makes the framing jump between people, or worse,
    average out onto the empty table between them. So we pool every detection in
    the cut and cluster by horizontal position: each cluster is a person who was
    actually there, whether or not any single frame caught them both.
    """
    seen = [(f["x"], f["w"], f["conf"], i)
            for i, faces in enumerate(faces_per_frame) for f in faces]
    if not seen or not n_frames:
        return []
    seen.sort()

    groups, current = [], [seen[0]]
    for face in seen[1:]:
        if face[0] - current[-1][0] > gap:
            groups.append(current)
            current = []
        current.append(face)
    groups.append(current)

    # A person seen in a single frame is a ghost (a face on a poster, a smear on
    # a turn). Demand two sightings — unless the cut is so short we only sampled
    # a frame or two, where there's nothing to discriminate with.
    min_frames = 2 if n_frames >= 4 else 1

    clusters = []
    for g in groups:
        frames = len({face[3] for face in g})
        if frames < min_frames or frames / n_frames < min_presence:
            continue
        clusters.append({
            "x": statistics.median([face[0] for face in g]),
            "w": statistics.median([face[1] for face in g]),
            "conf": max(face[2] for face in g),
            "frames": frames,
        })
    return clusters


def decide_cut(faces_per_frame: list[list[dict]], n_frames: int, w: int, h: int,
               cw: int = CANVAS_W, ch: int = CANVAS_H,
               min_rate: float = MIN_HIT_RATE,
               deadzone: float = DEADZONE) -> tuple[float | None, bool]:
    """One decision per cut: (where to aim, is this a two-shot).

    None means "leave it centred" — the honest answer when we didn't see enough
    to be sure, and never worse than the blind centre-crop we're replacing.
    """
    if not n_frames:
        return None, False
    hit_frames = sum(1 for faces in faces_per_frame if faces)
    if hit_frames / n_frames < min_rate:
        return None, False  # too little evidence to move anything

    clusters = cluster_faces(faces_per_frame, n_frames)
    if not clusters:
        return None, False
    two_shot = len(clusters) >= 2

    if len(clusters) == 1:
        fx = clusters[0]["x"]
    else:
        left = min(c["x"] - c["w"] / 2 for c in clusters)
        right = max(c["x"] + c["w"] / 2 for c in clusters)
        if (right - left) <= window_fraction(w, h, cw, ch) * PAIR_FIT:
            fx = (left + right) / 2          # both fit — frame them together
        else:
            dominant = max(clusters, key=lambda c: (c["w"], c["frames"]))
            fx = dominant["x"]               # can't fit both — follow the nearest

    if abs(fx - 0.5) < deadzone:
        return None, two_shot                # already centred; don't micro-nudge
    return fx, two_shot


def lock_cameras(cuts: list[dict], spread: float = LOCK_SPREAD) -> list[dict]:
    """Give every cut from the same locked-off camera the SAME framing.

    Podcast cameras sit on tripods and the speaker barely moves, so a per-cut
    decision is measuring noise, not motion: on the צומת 20 pilot the same camera
    drifted 0.450–0.491 across its cuts — 139px of framing that would visibly
    jump every time the edit returns to that angle. When a camera's face position
    is that stable, one framing for the whole camera is both truer and calmer.

    A camera whose speaker genuinely roams (spread beyond `spread`) keeps its
    per-cut framing — there we really are tracking movement.

    `cuts` are dicts with "group" (camera or file) and "fx" (None = no face).
    Returns them with "fx" locked and "locked" flagged. Caller applies deadzone.
    """
    seen = {}
    for c in cuts:
        if c["fx"] is not None:
            seen.setdefault(c["group"], []).append(c["fx"])

    locked = {}
    for group, xs in seen.items():
        if len(xs) >= 2 and (max(xs) - min(xs)) <= spread:
            locked[group] = statistics.median(xs)

    for c in cuts:
        if c["fx"] is not None and c["group"] in locked:
            c["fx"] = locked[c["group"]]
            c["locked"] = True
        else:
            c["locked"] = False
    return cuts


# --------------------------------------------------------------------------
# detection — I/O
# --------------------------------------------------------------------------

_detector = None


def _face_detector():
    global _detector
    if _detector is None:
        if not YUNET.exists():
            raise RuntimeError(
                "מודל זיהוי הפנים חסר (models/face_detection_yunet_2023mar.onnx) — "
                "הרץ ./install.sh")
        _detector = cv2.FaceDetectorYN.create(str(YUNET), "", (320, 320),
                                              score_threshold=SCORE_MIN)
    return _detector


def _detect(img) -> list[dict]:
    h, w = img.shape[:2]
    det = _face_detector()
    det.setInputSize((w, h))
    _, faces = det.detect(img)
    out = []
    for f in (faces if faces is not None else []):
        fw = float(f[2]) / w
        if fw < MIN_FACE_W:
            continue
        out.append({"x": (float(f[0]) + float(f[2]) / 2) / w,
                    "w": fw, "conf": float(f[-1])})
    return out


def _sample_frames(path: Path, start_us: int, duration_us: int,
                   tmp: Path) -> list[Path]:
    """Pull ~SAMPLE_FPS downscaled frames out of one cut's source range."""
    seconds = max(0.1, duration_us / 1e6)
    fps = min(SAMPLE_FPS, MAX_FRAMES / seconds)
    subprocess.run(
        [str(FFMPEG), "-v", "error", "-nostdin",
         "-ss", f"{start_us / 1e6:.3f}", "-t", f"{seconds:.3f}", "-i", str(path),
         "-vf", f"fps={fps:.4f},scale={FRAME_W}:-2", "-frames:v", str(MAX_FRAMES),
         "-q:v", "4", str(tmp / "f%03d.jpg")],
        capture_output=True)
    return sorted(tmp.glob("*.jpg"))


# --------------------------------------------------------------------------
# draft plumbing
# --------------------------------------------------------------------------

def _segment_source(seg: dict, mat: dict, mc_idx: dict) -> dict | None:
    """The real video file (and time range) behind one timeline segment.

    For a multi-camera clip the material has no path of its own — the footage
    that is actually ON SCREEN is whichever camera `cur_camera_track_id` points
    at, and its time base lives in the subdraft. We must sample THAT camera,
    not some arbitrary angle.
    """
    src = seg.get("source_timerange") or {}
    mci = mat.get("multi_camera_info") or {}
    if not mat.get("path") and mci:
        inner = mc_idx.get(mci.get("cur_camera_track_id"))
        if not inner:
            return None
        speed = inner["inner_speed"]
        start = inner["inner_src_start"] + (src.get("start", 0) - inner["inner_tgt_start"]) * speed
        return {"path": Path(inner["path"]),
                "start_us": int(start),
                "duration_us": int(src.get("duration", 0) * speed),
                "camera": mci.get("cur_camera_track_id")}
    if mat.get("path"):
        return {"path": Path(mat["path"]),
                "start_us": int(src.get("start", 0)),
                "duration_us": int(src.get("duration", 0)),
                "camera": None}
    return None


def plan_reframe(draft_id: str) -> dict:
    """Work out one transform.x per landscape cut. Reads only — writes nothing."""
    draft = capcut.load_draft(draft_id)
    canvas = draft.get("canvas_config") or {}
    cw, ch = canvas.get("width") or CANVAS_W, canvas.get("height") or CANVAS_H
    if cw >= ch:
        raise ValueError("מסגור אוטומטי נועד לקנבס אנכי (9:16) — הפרויקט הזה לא אנכי")

    mc_idx = capcut._multicam_index(capcut.DRAFTS_DIR / draft_id)
    mats = {m["id"]: m for m in draft.get("materials", {}).get("videos", [])}

    segments, warnings, missing = [], [], set()
    for track in draft.get("tracks", []):
        if track.get("type") != "video":
            continue
        for seg in track.get("segments", []):
            mat = mats.get(seg.get("material_id")) or {}
            if mat.get("type") == "photo":
                continue  # spacers, logos, closing cards — not footage
            w, h = mat.get("width") or 1920, mat.get("height") or 1080
            if w <= h:
                continue  # already vertical: nothing to reframe

            src = _segment_source(seg, mat, mc_idx)
            if not src:
                continue
            if not src["path"].exists():
                missing.add(str(src["path"]))
                continue

            tmp = Path(tempfile.mkdtemp(prefix="ccstudio-reframe-"))
            try:
                frames = _sample_frames(src["path"], src["start_us"],
                                        src["duration_us"], tmp)
                faces_per_frame = []
                for fp in frames:
                    img = cv2.imread(str(fp))
                    faces_per_frame.append([] if img is None else _detect(img))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

            # deadzone is applied AFTER the per-camera lock below — applying it
            # here would split a static camera's cuts into moved/not-moved on
            # measurement noise, which is exactly the jump we're avoiding.
            fx, two_shot = decide_cut(faces_per_frame, len(frames), w, h, cw, ch,
                                      deadzone=0.0)
            segments.append({
                "segment_id": seg["id"],
                "start_us": (seg.get("target_timerange") or {}).get("start", 0),
                "camera": src["camera"],
                "source": src["path"].name,
                "group": src["camera"] or src["path"].name,
                "frames": len(frames),
                "hits": sum(1 for f in faces_per_frame if f),
                "people": len(cluster_faces(faces_per_frame, len(frames))),
                "fx": fx,
                "two_shot": two_shot,
                "w": w, "h": h,
            })

    lock_cameras(segments)
    for s in segments:
        fx = s.pop("fx")
        w, h = s.pop("w"), s.pop("h")
        settled = fx is not None and abs(fx - 0.5) >= DEADZONE
        s["face_x"] = None if fx is None else round(fx, 4)
        s["scale"] = fill_scale(w, h, cw, ch)
        s["transform_x"] = round(transform_x(fx, w, h, cw, ch), 4) if settled else 0.0

    if missing:
        volumes = sorted({p.split("/Volumes/")[1].split("/")[0]
                          for p in missing if "/Volumes/" in p})
        where = f" — חבר את הכונן {', '.join(volumes)}" if volumes else ""
        raise ValueError(f"קבצי המקור לא זמינים{where}")

    moved = [s for s in segments if s["transform_x"] != 0.0]
    skipped = [s for s in segments if s["transform_x"] == 0.0]
    return {
        "segments": segments,
        "moved": len(moved),
        "centered": len(skipped),
        "two_shots": sum(1 for s in segments if s["two_shot"]),
        "warnings": warnings,
    }


def apply_plan_to_draft(draft: dict, plan: dict) -> int:
    """Write the planned pan onto an in-memory draft. Returns segments touched."""
    by_id = {s["segment_id"]: s for s in plan["segments"]}
    touched = 0
    for track in draft.get("tracks", []):
        if track.get("type") != "video":
            continue
        for seg in track.get("segments", []):
            s = by_id.get(seg["id"])
            if not s:
                continue
            clip = seg.setdefault("clip", {})
            clip["scale"] = {"x": s["scale"], "y": s["scale"]}
            clip["transform"] = {"x": s["transform_x"], "y": 0.0}
            touched += 1
    return touched


def apply_reframe(draft_id: str, plan: dict | None = None) -> dict:
    """Pan every landscape cut onto its speaker. Re-runnable: the transform is
    recomputed from the footage each time, never applied relatively."""
    if capcut.capcut_running():
        raise RuntimeError("capcut_running")
    plan = plan or plan_reframe(draft_id)
    if not plan["segments"]:
        raise ValueError("לא נמצאו קאטים למסגור")

    draft_dir = capcut.DRAFTS_DIR / draft_id
    capcut._backup(draft_dir)
    draft = capcut.load_draft(draft_id)
    touched = apply_plan_to_draft(draft, plan)
    capcut._atomic_write(draft_dir, draft)
    return {"moved": plan["moved"], "centered": plan["centered"],
            "two_shots": plan["two_shots"], "segments": touched}
