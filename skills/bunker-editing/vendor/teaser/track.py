#!/usr/bin/env python3
"""Per-frame tracking of a shot for effects that stick to the body (MediaPipe Tasks).

    <venv>/bin/python track.py <video> <out_dir> --from 12.0 --to 16.0 [--fps 30] [--models <dir>] [--cutout]

Run it with the lab venv (`~/bunker-video-engine/.venv`, mediapipe 1.1 + opencv) and the models in
`podcast-teaser-lab/models/` (hand_landmarker.task, face_landmarker.task, selfie_multiclass_256x256.tflite,
pose_landmarker_full.task — official files from storage.googleapis.com/mediapipe-models).

Writes <out_dir>/track.json — one entry per output frame, coordinates normalised 0–1 in the SOURCE frame:
  face:  {eyeL, eyeR, nose, chin, top (crown estimate), size}   → glasses on the eyes, a brain on the head, a laser across
  hands: [{wrist, index, thumb, center, handed}]                 → an object that follows a hand
  goggles: bool — both hands up around the eyes (the "VR goggles" gesture in the keto teaser)
  point_head: bool — an index finger near the temple ("brain" gesture)
With --cutout also <out_dir>/cut/00001.png … : the person on a transparent background (selfie multiclass, person =
any class but background), for "guest over a colour" shots and for covers.
Feed the json into the Sticker / Laser components (assets/teaser/Track.tsx) after mapping source → canvas with the same
crop the <Cam> used (camToCanvas in Track.tsx).
"""
import argparse
import json
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

LAB = Path.home() / "podcast-teaser-lab"


def pt(lm):
    return [round(lm.x, 4), round(lm.y, 4)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--from", dest="t0", type=float, default=0)
    ap.add_argument("--to", dest="t1", type=float, default=0)
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--models", default=str(LAB / "models"))
    ap.add_argument("--cutout", action="store_true")
    a = ap.parse_args()
    M = Path(a.models)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    VIDEO = vision.RunningMode.VIDEO
    face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(M / "face_landmarker.task")), running_mode=VIDEO, num_faces=2))
    hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(M / "hand_landmarker.task")), running_mode=VIDEO, num_hands=2,
        min_hand_detection_confidence=0.4, min_tracking_confidence=0.4))
    seg = None
    if a.cutout:
        seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=str(M / "selfie_multiclass_256x256.tflite")), running_mode=VIDEO,
            output_category_mask=False, output_confidence_masks=True))
        (out / "cut").mkdir(exist_ok=True)

    cap = cv2.VideoCapture(a.video)
    t1 = a.t1 or cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    n = int(round((t1 - a.t0) * a.fps))
    frames = []
    for i in range(n):
        t = a.t0 + i / a.fps
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, bgr = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        ms = int(round(i * 1000 / a.fps))
        f = {"t": round(t, 3)}
        fr = face.detect_for_video(img, ms)
        if fr.face_landmarks:
            L = max(fr.face_landmarks, key=lambda l: max(p.y for p in l) - min(p.y for p in l))  # largest face
            ys = [p.y for p in L]
            size = max(ys) - min(ys)
            eyeL = np.mean([[L[k].x, L[k].y] for k in (33, 133)], axis=0)
            eyeR = np.mean([[L[k].x, L[k].y] for k in (362, 263)], axis=0)
            f["face"] = {"eyeL": [round(v, 4) for v in eyeL], "eyeR": [round(v, 4) for v in eyeR], "nose": pt(L[1]),
                         "chin": pt(L[152]), "top": [round(L[10].x, 4), round(L[10].y - size * 0.18, 4)], "size": round(size, 4)}
        hr = hands.detect_for_video(img, ms)
        hs = []
        for lm, hd in zip(hr.hand_landmarks, hr.handedness):
            hs.append({"wrist": pt(lm[0]), "thumb": pt(lm[4]), "index": pt(lm[8]),
                       "center": [round(float(np.mean([p.x for p in lm])), 4), round(float(np.mean([p.y for p in lm])), 4)],
                       "handed": hd[0].category_name})
        f["hands"] = hs
        if "face" in f and hs:
            fc = f["face"]
            ex, ey = (fc["eyeL"][0] + fc["eyeR"][0]) / 2, (fc["eyeL"][1] + fc["eyeR"][1]) / 2
            near = [h for h in hs if abs(h["center"][1] - ey) < fc["size"] * 0.6 and abs(h["center"][0] - ex) < fc["size"] * 1.3]
            f["goggles"] = len(near) == 2
            f["point_head"] = any(abs(h["index"][1] - fc["top"][1]) < fc["size"] * 0.5 and abs(h["index"][0] - ex) < fc["size"] * 1.0 for h in hs)
        if seg is not None:
            r = seg.segment_for_video(img, ms)
            bg = r.confidence_masks[0].numpy_view()  # class 0 = background
            fg = np.clip((0.75 - bg) / 0.5, 0, 1)  # smoothstep the soft mask: no ghost of the chair, no see-through body
            alpha = (fg * fg * (3 - 2 * fg) * 255).astype(np.uint8)
            alpha = cv2.GaussianBlur(cv2.resize(alpha, (bgr.shape[1], bgr.shape[0])), (5, 5), 0)
            cv2.imwrite(str(out / "cut" / f"{i + 1:05d}.png"), np.dstack([bgr, alpha]))
        frames.append(f)
    meta = {"video": a.video, "from": a.t0, "fps": a.fps, "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), "frames": frames}
    (out / "track.json").write_text(json.dumps(meta), encoding="utf-8")
    nf = sum("face" in f for f in frames); nh = sum(bool(f["hands"]) for f in frames)
    print(f"{len(frames)} frames · face {nf} · hands {nh} · goggles {sum(f.get('goggles', False) for f in frames)} · point_head {sum(f.get('point_head', False) for f in frames)}")


if __name__ == "__main__":
    main()
