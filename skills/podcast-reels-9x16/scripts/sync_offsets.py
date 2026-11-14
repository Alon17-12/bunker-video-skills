"""Measure the offset between two recordings of the same room — the client's convenience file
against a camera angle, or a RODECASTER mic channel against the camera's embedded audio.

    python sync_offsets.py "<ref file>" "<other file>" [--at 60,900,1800] [--win 20] [--search 30]

Prints, per window, the lag that maximises the cross-correlation of the two 8 kHz envelopes
(coarse, ±search s) refined on the raw waveform (±0.05 s), as   other_time = ref_time + offset.
Three windows an hour apart agreeing to a few ms proves both the offset and the absence of drift;
disagreement means a spliced file or a clock that runs at a different rate — say so, do not average.
Assert `ss >= 0` everywhere: a negative seek is clamped by ffmpeg and returns a confident wrong number.
"""
import argparse, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import paths

FF = str(paths.FFMPEG)


def pcm(path, ss, t, sr):
    assert ss >= 0, f"negative seek {ss} on {os.path.basename(path)}"
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{ss:.3f}", "-t", f"{t:.3f}", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def envelope(x, sr, hop):
    k = len(x) // hop
    return np.sqrt((x[: k * hop].reshape(k, hop) ** 2).mean(1)) if k else np.zeros(1)


def best_lag(a, b, max_lag):
    """lag (samples) such that b[t] ≈ a[t - lag], via FFT cross-correlation; positive = b is later"""
    n = 1
    while n < len(a) + len(b): n *= 2
    A = np.fft.rfft(a - a.mean(), n); B = np.fft.rfft(b - b.mean(), n)
    cc = np.fft.irfft(B * np.conj(A), n)
    cc = np.concatenate([cc[-max_lag:], cc[: max_lag + 1]])
    lags = np.arange(-max_lag, max_lag + 1)
    i = int(np.argmax(cc)); return int(lags[i]), float(cc[i] / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def measure(ref, other, at, win, search):
    out = []
    for t0 in at:
        ss_other = max(0.0, t0 - search)
        a = pcm(ref, t0, win, 8000); b = pcm(other, ss_other, win + 2 * search, 8000)
        if len(a) < 8000 or len(b) < 8000: out.append((t0, None, 0.0)); continue
        ea, eb = envelope(a, 8000, 80), envelope(b, 8000, 80)                      # 100 Hz envelopes
        lag, score = best_lag(ea, eb, len(eb))                                     # coarse, 10 ms
        coarse = (ss_other - t0) + lag / 100.0                                     # other = ref + coarse
        # refine on the waveform at 48 kHz around the coarse estimate
        sr = 48000; ss_b = max(0.0, t0 + coarse - 0.06)
        a2 = pcm(ref, t0, min(win, 8), sr); b2 = pcm(other, ss_b, min(win, 8) + 0.12, sr)
        lag2, score2 = best_lag(a2, b2, int(0.12 * sr))
        fine = (ss_b - t0) + lag2 / sr
        out.append((t0, fine, score2))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ref"); ap.add_argument("other")
    ap.add_argument("--at", default="60,600,1500"); ap.add_argument("--win", type=float, default=20); ap.add_argument("--search", type=float, default=30)
    a = ap.parse_args(); at = [float(x) for x in a.at.split(",")]
    rows = measure(a.ref, a.other, at, a.win, a.search)
    print(f"other = ref + offset   ref={os.path.basename(a.ref)}  other={os.path.basename(a.other)}")
    for t0, off, sc in rows:
        print(f"  @{t0:7.1f}s  offset {off:+.4f}s  corr {sc:.3f}" if off is not None else f"  @{t0:7.1f}s  (no audio in window)")
    vals = [o for _, o, _ in rows if o is not None]
    if len(vals) >= 2: print(f"  spread {max(vals) - min(vals) * 1:.4f}s  mean {np.mean(vals):+.4f}s")


if __name__ == "__main__":
    main()
