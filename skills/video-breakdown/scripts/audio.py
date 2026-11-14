#!/usr/bin/env python3
"""Deterministic audio measurements for one reference video.

Answers the questions an ear answers but a guess should not: how fast is the
music, how loud is it under the voice, and are the cuts being punctuated by
sound hits. Writes evidence/audio.json.

Honest about its limits — it reports that a sharp hit lands at 00:04.21 and
that it coincides with a cut. It does not claim to know the hit is a whoosh.
Naming the sound is the listening pass's job, not this script's.

usage: audio.py <video> <outdir>
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 16000
WIN = 1024
HOP = 512
HOP_S = HOP / SR

BPM_MIN, BPM_MAX = 60.0, 180.0
HIT_MAD_K = 8.0
SILENCE_PEAK = 1e-4
CUT_TOLERANCE_S = 0.15


def _ffmpeg() -> str:
    for candidate in (
        Path.home() / "ffmpeg-bin" / "ffmpeg",
        Path.home() / "bunker-video-engine" / "bin" / "ffmpeg",
    ):
        if candidate.exists():
            return str(candidate)
    found = shutil.which("ffmpeg")
    if not found:
        raise SystemExit("ffmpeg not found")
    return found


def _decode(video: Path) -> np.ndarray:
    proc = subprocess.run(
        [_ffmpeg(), "-v", "error", "-i", str(video),
         "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # A file with no audio stream at all (a video-only DASH segment, a muted
    # export) makes ffmpeg exit non-zero. That is a finding, not a crash.
    if proc.returncode != 0 or not proc.stdout:
        return np.zeros(0, dtype=np.float32)
    return np.frombuffer(proc.stdout, dtype=np.float32)


def _spectrogram(samples: np.ndarray) -> np.ndarray:
    count = 1 + max(0, (len(samples) - WIN) // HOP)
    if count < 2:
        raise SystemExit("audio too short to analyse")
    window = np.hanning(WIN).astype(np.float32)
    frames = np.lib.stride_tricks.as_strided(
        samples, shape=(count, WIN),
        strides=(samples.strides[0] * HOP, samples.strides[0]),
    ) * window
    return np.abs(np.fft.rfft(frames, axis=1))


def _tempo(flux: np.ndarray):
    """Autocorrelate the onset envelope; a real beat shows up as a periodic peak.

    Calibrated 23.09.26 against a synthetic 120 BPM click and a talking head.
    Peak prominence does NOT separate them — the talking head scored higher
    (2.32 vs 1.61), because syllables are periodic too. What separates them is
    whether the winning lag is a true local maximum: the click's is, the
    speech's is a point on a decaying slope. So that is the only gate, and no
    confidence score is invented on top of it.

    Resolution is the 32 ms hop: ~3 BPM near 120. Reported values are that
    coarse on purpose.
    """
    centred = flux - flux.mean()
    corr = np.correlate(centred, centred, mode="full")[len(centred) - 1:]
    # Round inward so every candidate lag maps to a BPM inside the range.
    lo = int(np.ceil(60.0 / BPM_MAX / HOP_S))
    hi = min(int(np.floor(60.0 / BPM_MIN / HOP_S)), len(corr) - 2)
    if hi <= lo + 1:
        return None
    window = corr[lo:hi + 1]
    lag = lo + int(np.argmax(window))
    if not (corr[lag] > corr[lag - 1] and corr[lag] > corr[lag + 1]):
        return None
    return round(60.0 / (lag * HOP_S), 1)


def _db(value: float, reference: float) -> float:
    if value <= 0 or reference <= 0:
        return -99.0
    return round(float(20 * np.log10(value / reference)), 1)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    video, out = Path(sys.argv[1]), Path(sys.argv[2])

    samples = _decode(video)
    evidence = out / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    if samples.size == 0 or float(np.max(np.abs(samples))) < SILENCE_PEAK:
        silent = {"duration_s": round(len(samples) / SR, 2), "audio_present": False,
                  "note": ("no audio stream in the file — if this came from Instagram, the download "
                           "was the embed preview, not the reel" if samples.size == 0 else
                           "the track is silent — there is no music, speech or SFX to measure")}
        (evidence / "audio.json").write_text(
            json.dumps(silent, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(silent, ensure_ascii=False, indent=2))
        return

    spec = _spectrogram(samples)
    rms = np.sqrt(np.mean(spec ** 2, axis=1))
    flux = np.diff(spec, axis=0, prepend=spec[:1])
    flux = np.sum(np.maximum(flux, 0), axis=1)

    peak = float(np.max(rms)) or 1e-9
    # Frames in the quietest third are the gaps between phrases. Whatever is
    # still sounding there is the bed under the voice.
    gap_level = float(np.median(rms[rms <= np.percentile(rms, 33)]))
    speech_level = float(np.median(rms[rms >= np.percentile(rms, 66)]))

    bpm = _tempo(flux)

    median = float(np.median(flux))
    mad = float(np.median(np.abs(flux - median))) or 1e-6
    hits = [
        {"t_s": round(i * HOP_S, 2), "strength": round(float((flux[i] - median) / mad), 1)}
        for i in np.flatnonzero(flux > median + HIT_MAD_K * mad)
    ]
    # Collapse hits that are really one transient smeared over a few frames.
    merged = []
    for hit in hits:
        if merged and hit["t_s"] - merged[-1]["t_s"] < 0.12:
            merged[-1] = max(merged[-1], hit, key=lambda h: h["strength"])
        else:
            merged.append(hit)

    on_cut = None
    shots_file = out / "evidence" / "shots.json"
    if shots_file.exists():
        shots = json.loads(shots_file.read_text(encoding="utf-8"))["shots"]
        cuts = [s["start_s"] for s in shots[1:]]
        if cuts:
            matched = sum(
                any(abs(cut - hit["t_s"]) <= CUT_TOLERANCE_S for hit in merged)
                for cut in cuts
            )
            on_cut = {
                "cuts": len(cuts),
                "cuts_with_a_hit": matched,
                "share": round(matched / len(cuts), 2),
                "tolerance_s": CUT_TOLERANCE_S,
            }

    duration = len(samples) / SR
    payload = {
        "duration_s": round(duration, 2),
        "audio_present": True,
        "tempo_bpm": bpm,
        "tempo_basis": ("periodic peak in the onset envelope, +/-3 BPM"
                        if bpm else "no periodic beat found - likely speech-led or no music bed"),
        "bed_under_speech_db": _db(gap_level, speech_level),
        "bed_vs_peak_db": _db(gap_level, peak),
        "speech_vs_peak_db": _db(speech_level, peak),
        "transient_hits": len(merged),
        "hits_per_minute": round(len(merged) / duration * 60, 1) if duration else None,
        "hits": merged[:80],
        "hits_on_cuts": on_cut,
        "note": "timings and levels are measured; naming a sound is not this script's job",
    }
    (evidence / "audio.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "hits"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
