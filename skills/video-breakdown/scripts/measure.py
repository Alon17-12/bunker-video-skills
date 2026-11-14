#!/usr/bin/env python3
"""Deterministic visual measurements for one reference video.

Every number this script emits is reproducible: same file in, same numbers out.
That is the whole point — it is the half of the rubric that must never come
from an opinion. It writes:

    evidence/shots.json     cut list, shot durations, motion energy per shot
    evidence/captions.json  timestamps where the on-screen text changed
    shots/                  one representative frame per shot
    captions/               one frame per caption change
    sheets/                 labelled contact sheets for reading many at once

usage: measure.py <video> <outdir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

# A cut is a spike in frame-to-frame difference. The floor stops a dark, noisy
# clip from reporting a cut every few frames; the MAD term adapts to how busy
# the footage already is.
CUT_FLOOR = 11.0
CUT_MAD_K = 6.0
MIN_SHOT_S = 0.25

# Captions change far more often than shots do, so they get their own detector
# over the lower band of the frame, where burned-in subtitles live.
CAP_BAND_TOP = 0.45
CAP_BAND_BOTTOM = 0.98
# Caption detection, calibrated 23.09.26 on three videos against counted truth
# (Hormozi reel ~40 cards / 41 s, captionless CNBC interview ~3-6, small-serif
# reel ~20-25). What survived the sweep:
#   text mask   = white top-hat (thin bright strokes) held for 75 % of 8 frames
#   text lines  = stroke clusters shaped like a line of text, with stroke fill
#                 >= 0.20 of their box (fabric texture forms lines but not fill)
#   change      = 1 - IoU between the line mask now and 8 frames back > 0.55,
#                 AND both sides settled (IoU >= 0.5 before and after) — a card
#                 is a jump between two stable states; drift is not
# Result: 26 / 9 / 23 against 40 / 3-6 / 20-25. This is a ±40 % estimate, not a
# count: the contact sheet is the evidence and the number is where to look.
CAP_PERSIST_FRAMES = 8
CAP_PERSIST_SHARE = 0.75
CAP_CHANGE_IOU = 0.55
CAP_SETTLE_IOU = 0.50
CAP_MIN_TEXT_PX = 40
CAP_MIN_GAP_S = 0.40
CAP_SAME_CARD_IOU = 0.85
CAP_STROKE_CONTRAST = 70
_TOPHAT_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
_LINE_KERNEL = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
LINE_MIN_W, LINE_MIN_H, LINE_MAX_H, LINE_MIN_ASPECT = 30, 3, 28, 2.5
LINE_FILL_DETECT = 0.20     # for change detection
LINE_FILL_PRESENCE = 0.15   # looser, for "are there captions at all" (CNBC → 0, reels → 300-800 px)

MAX_DURATION_S = 180        # beyond this the style-book premise breaks; warn, don't refuse
HOOK_S = 3.0

# Face height as a share of frame height, measured on the shot's middle frame.
# Bands are the conventional framing scale; "no_face" covers B-roll, screens, text.
FRAMING_BANDS = ((0.34, "close-up"), (0.20, "medium close-up"), (0.10, "medium"), (0.0, "wide"))
_FACE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

SHEET_ROWS = 3


def _text_mask(frame, height: int):
    """Thin bright strokes in the caption band — what burned captions are made of.

    A plain brightness threshold fails on a white wall: the brightest 3 % of the
    band is the wall, and it moves with the head (6 of 6 false positives on a
    CNBC interview, 23.09.26). A white top-hat (gray minus its opening) keeps
    only bright structures thinner than the kernel, so text survives and
    walls, shirts and windows vanish regardless of how bright they are.
    """
    band = frame[int(height * CAP_BAND_TOP):int(height * CAP_BAND_BOTTOM)]
    gray = cv2.cvtColor(cv2.resize(band, (256, 110)), cv2.COLOR_BGR2GRAY)
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, _TOPHAT_KERNEL)
    return (tophat >= CAP_STROKE_CONTRAST).astype(np.uint8)


def _text_lines(steady, fill_min):
    """Keep only stroke clusters shaped and filled like a line of text."""
    merged = cv2.dilate(steady, _LINE_KERNEL)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(merged, connectivity=8)
    keep = np.zeros_like(merged)
    for i in range(1, n):
        x, y, w, h, _ = stats[i]
        if w >= LINE_MIN_W and LINE_MIN_H <= h <= LINE_MAX_H and w / h >= LINE_MIN_ASPECT:
            if steady[y:y + h, x:x + w].sum() / (w * h) >= fill_min:
                keep[y:y + h, x:x + w] = 1
    return keep & merged


def _iou(a, b) -> float:
    union = int((a | b).sum())
    return 1.0 if union == 0 else int((a & b).sum()) / union


def _classify_motion(energy: float) -> str:
    if energy < 1.5:
        return "static"
    if energy < 4.0:
        return "slight"
    if energy < 9.0:
        return "moderate"
    return "fast"


def _peaks(values: np.ndarray, floor: float, mad_k: float):
    """Indices where `values` spikes above both the floor and the local spread."""
    if values.size == 0:
        return np.array([], dtype=int)
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median))) or 1e-6
    threshold = max(floor, median + mad_k * mad)
    return np.flatnonzero(values > threshold)


def _scan(video: Path):
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_diffs, count, recent, line_masks, presence_px = [], 0, [], [], []
    prev_hsv = None

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        count += 1

        small = cv2.resize(frame, (96, 54))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV).astype(np.float32)
        frame_diffs.append(0.0 if prev_hsv is None else float(np.mean(np.abs(hsv - prev_hsv))))
        prev_hsv = hsv

        recent.append(_text_mask(frame, height))
        if len(recent) > CAP_PERSIST_FRAMES:
            recent.pop(0)
        steady = (np.sum(recent, axis=0) >= CAP_PERSIST_SHARE * len(recent)).astype(np.uint8)
        line_masks.append(np.packbits(_text_lines(steady, LINE_FILL_DETECT)))
        presence_px.append(int(_text_lines(steady, LINE_FILL_PRESENCE).sum()))

    cap.release()
    return fps, width, height, np.array(frame_diffs), line_masks, np.array(presence_px), count


def _shots(fps, frame_diffs, total):
    cuts = [0]
    min_gap = max(1, int(MIN_SHOT_S * fps))
    for idx in _peaks(frame_diffs, CUT_FLOOR, CUT_MAD_K):
        if idx - cuts[-1] >= min_gap:
            cuts.append(int(idx))
    cuts.append(total)

    shots = []
    for n, (start, end) in enumerate(zip(cuts, cuts[1:]), start=1):
        interior = frame_diffs[start + 1:end]
        energy = float(np.mean(interior)) if interior.size else 0.0
        shots.append({
            "index": n,
            "start_s": round(start / fps, 2),
            "end_s": round(end / fps, 2),
            "duration_s": round((end - start) / fps, 2),
            "motion_energy": round(energy, 2),
            "motion": _classify_motion(energy),
            "_frame": start + (end - start) // 2,
        })
    return shots


def _caption_changes(fps, line_masks):
    """Jumps between two settled text-line states, at most one per 0.4 s."""
    K = CAP_PERSIST_FRAMES
    shape = (110, 256)
    masks = [np.unpackbits(m)[:shape[0] * shape[1]].reshape(shape) for m in line_masks]
    n = len(masks)
    changes, last = [], -1e9
    for i in range(2 * K, n - K):
        now, past = masks[i], masks[i - K]
        if max(int(now.sum()), int(past.sum())) < CAP_MIN_TEXT_PX:
            continue
        if 1.0 - _iou(now, past) <= CAP_CHANGE_IOU:
            continue
        if _iou(masks[i - 2 * K], past) < CAP_SETTLE_IOU or _iou(now, masks[i + K]) < CAP_SETTLE_IOU:
            continue
        t = i / fps
        if t - last >= CAP_MIN_GAP_S:
            changes.append({"t_s": round(float(t), 2), "_frame": int(i)})
            last = t
    return changes


def _dedupe_captions(video: Path, height: int, fps: float, changes):
    """Drop repeats where the card did not change.

    The detector fires at the leading edge of a change and can fire again as
    the persistence window finishes turning over ~0.5 s later, so a single card
    showed up twice on 4 of 9 sheet cells (Hormozi, 23.09.26). Judged on the
    same representation the detector uses — the line mask held over the next K
    frames — the two candidates are the same card and the second is dropped.
    The 0.85 threshold sits well above every real change measured (≤ 0.17).
    """
    cap = cv2.VideoCapture(str(video))
    kept, prev_mask = [], None
    for change in changes:
        cap.set(cv2.CAP_PROP_POS_FRAMES, change["_frame"])
        window = []
        for _ in range(CAP_PERSIST_FRAMES):
            ok, frame = cap.read()
            if not ok:
                break
            window.append(_text_mask(frame, height))
        if not window:
            continue
        steady = (np.sum(window, axis=0) >= CAP_PERSIST_SHARE * len(window)).astype(np.uint8)
        mask = _text_lines(steady, LINE_FILL_DETECT)
        if prev_mask is not None and _iou(mask, prev_mask) > CAP_SAME_CARD_IOU:
            continue
        kept.append(change)
        prev_mask = mask
    cap.release()
    return kept


def _framing(frame) -> tuple:
    """(face height / frame height, framing label). Largest face wins."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    scale = 480 / max(gray.shape)
    small = cv2.resize(gray, None, fx=scale, fy=scale)
    faces = _FACE.detectMultiScale(small, scaleFactor=1.15, minNeighbors=5, minSize=(24, 24))
    if len(faces) == 0:
        return 0.0, "no_face"
    ratio = float(max(h for (_, _, _, h) in faces)) / small.shape[0]
    label = next(name for floor, name in FRAMING_BANDS if ratio >= floor)
    return round(ratio, 3), label


def _write_frames(video: Path, total, items, outdir: Path, prefix: str):
    """Seek to the wanted frames only. Holding a decoded video in memory costs
    tens of GB at 1080p; there are never more than a few dozen frames to save."""
    outdir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    written = []
    for n, item in enumerate(items, start=1):
        idx = min(item["_frame"], total - 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        t = item.get("start_s", item.get("t_s", 0.0))
        if prefix == "shot":
            item["face_ratio"], item["framing"] = _framing(frame)
        path = outdir / f"{prefix}-{n:03d}_{t:07.2f}s.jpg"
        cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
        written.append((path, t))
    cap.release()
    return written


def _contact_sheets(written, outdir: Path, prefix: str):
    """Grids of labelled stills — far cheaper to read than one image per shot."""
    outdir.mkdir(parents=True, exist_ok=True)
    if not written:
        return []
    probe = cv2.imread(str(written[0][0]))
    cols, cell_w = (2, 540) if probe.shape[1] > probe.shape[0] else (3, 360)
    per_sheet = cols * SHEET_ROWS
    sheets = []
    for sheet_no, start in enumerate(range(0, len(written), per_sheet), start=1):
        chunk = written[start:start + per_sheet]
        tiles = []
        for path, t in chunk:
            img = cv2.imread(str(path))
            h = int(img.shape[0] * cell_w / img.shape[1])
            tile = cv2.resize(img, (cell_w, h))
            label = f"{int(t // 60):02d}:{t % 60:05.2f}"
            cv2.rectangle(tile, (0, 0), (150, 26), (0, 0, 0), -1)
            cv2.putText(tile, label, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            tiles.append(tile)

        cell_h = max(t.shape[0] for t in tiles)
        used_rows = -(-len(tiles) // cols)  # trim the blank rows off a partial sheet
        canvas = np.zeros((cell_h * used_rows, cell_w * cols, 3), np.uint8)
        for i, tile in enumerate(tiles):
            r, c = divmod(i, cols)
            canvas[r * cell_h:r * cell_h + tile.shape[0], c * cell_w:(c + 1) * cell_w] = tile

        path = outdir / f"{prefix}-{sheet_no:02d}.jpg"
        cv2.imwrite(str(path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])
        sheets.append(str(path))
    return sheets


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    video, out = Path(sys.argv[1]), Path(sys.argv[2])

    fps, width, height, frame_diffs, line_masks, presence_px, total = _scan(video)
    shots = _shots(fps, frame_diffs, total)
    changes = _dedupe_captions(video, height, fps, _caption_changes(fps, line_masks))
    text_px_median = int(np.median(presence_px)) if len(presence_px) else 0

    shot_files = _write_frames(video, total, shots, out / "shots", "shot")
    cap_files = _write_frames(video, total, changes, out / "captions", "cap")
    sheets = {
        "shots": _contact_sheets(shot_files, out / "sheets", "shots"),
        "captions": _contact_sheets(cap_files, out / "sheets", "captions"),
    }

    durations = [s["duration_s"] for s in shots]
    for item in shots + changes:
        item.pop("_frame", None)

    duration_s = total / fps
    framing_counts = {}
    for shot in shots:
        framing_counts[shot["framing"]] = framing_counts.get(shot["framing"], 0) + 1
    hook = {
        "window_s": HOOK_S,
        "cuts": sum(1 for sh in shots[1:] if sh["start_s"] < HOOK_S),
        "caption_changes": sum(1 for c in changes if c["t_s"] < HOOK_S),
        "first_shot_framing": shots[0]["framing"] if shots else None,
        "first_shot_motion": shots[0]["motion"] if shots else None,
    }
    warning = (f"{duration_s:.0f}s is over the {MAX_DURATION_S}s this skill is built for — "
               "shot stats still hold, but a style book of a long-form video is a different deliverable"
               if duration_s > MAX_DURATION_S else None)

    evidence = out / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "shots.json").write_text(json.dumps({
        "source": str(video),
        "fps": round(fps, 3),
        "resolution": f"{width}x{height}",
        "aspect": round(width / height, 3) if height else None,
        "duration_s": round(total / fps, 2),
        "shot_count": len(shots),
        "avg_shot_s": round(float(np.mean(durations)), 2) if durations else None,
        "median_shot_s": round(float(np.median(durations)), 2) if durations else None,
        "longest_shot_s": round(max(durations), 2) if durations else None,
        "shortest_shot_s": round(min(durations), 2) if durations else None,
        "cuts_per_minute": round(len(shots) / (total / fps) * 60, 1) if total else None,
        "framing_counts": framing_counts,
        "hook": hook,
        "warning": warning,
        "shots": shots,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    (evidence / "captions.json").write_text(json.dumps({
        "band": [CAP_BAND_TOP, CAP_BAND_BOTTOM],
        "captions_present": text_px_median >= CAP_MIN_TEXT_PX,
        "text_px_median": text_px_median,
        "accuracy": "change_count is a ±40% estimate — confirm against sheets/captions-*.jpg before it becomes a rule",
        "change_count": len(changes),
        "changes_per_minute": round(len(changes) / (total / fps) * 60, 1) if total else None,
        "changes": changes,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "duration_s": round(total / fps, 2),
        "shots": len(shots),
        "avg_shot_s": round(float(np.mean(durations)), 2) if durations else None,
        "caption_changes": len(changes),
        "captions_present": text_px_median >= CAP_MIN_TEXT_PX,
        "framing_counts": framing_counts,
        "hook": hook,
        "warning": warning,
        "sheets": sheets,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
