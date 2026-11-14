"""Dialogue from the two mics, never from the Live-Mix (Alon approved the sound 12.10.2026).

Why: Live-Mix.wav is exactly 0.82*mic1 + 0.82*mic2. Each mic also hears the other speaker
~5.5 ms later at about -16 dB, so the sum comb-filters (notches every ~180 Hz). That is the
"metallic" sound Alon heard in the Guest J reels. Here the mic that is not speaking is ducked
to -20 dB (opens when it is within 6 dB of the other, 15 ms attack / 250 ms release), so each
voice reaches the mix once.

  master  <audio_dir> <out.wav> [--start S --dur D]
      The whole episode (or a range) on the Live-Mix clock, -16 LUFS, peaks under -1.5 dBTP.
      Prep turns it into public/mix.m4a + mix.wav, so the teaser (Remotion <Audio>) and the
      reels (capcut_project_v2.py) pick it up with no other change.
  windows <windows.json> <out_dir> <audio_dir> [--align-to <dir>]
      Retrofit: rebuild rN_dialogue.wav for a CapCut project already built from the Live-Mix.
      windows.json = {"r1": [[w0, w1], ...]} in Live-Mix seconds (the merged windows of
      capcut_project_v2.py). --align-to = folder with the old files; each new file is
      shifted to match its old copy sample for sample (normally 0; the limiter runs with latency=1)
      and cut to the same length, so the CapCut timing does not move. Files land at -14 LUFS:
      set the dialogue segments to volume 1.0.
  check   <audio_dir> <file.wav> <file_start_on_live_mix_clock> [--at <seconds into the file>]
      QA gate: how far the file is from the Live-Mix. A Live-Mix copy (even via mix.m4a) sits at about
      -37 dB or lower -> FAIL; the ducked mix differs by the removed bleed (-16..-22 dB) -> PASS. Threshold -32 dB (a Live-Mix copy measured -36.5..-40.8).
      The 12 s checked must be one uncut stretch on the Live-Mix clock (the start of a window).
"""
import json, math, os, subprocess, sys
import numpy as np

FF = os.path.expanduser("~/ffmpeg-bin/ffmpeg")
SR = 48000
FLOOR_DB, OPEN_DB, SPAN_DB = -20.0, 6.0, 6.0


def read(path, t0, dur, ch=1):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{max(0.0, t0):.6f}", "-t", f"{dur:.6f}", "-i", path,
                          "-ac", str(ch), "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    x = np.concatenate([np.zeros(int(round(max(0.0, -t0) * SR))), x])
    n = int(round(dur * SR))
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def mics(audio_dir):
    names = sorted(os.listdir(audio_dir))
    m1 = next(f for f in names if f.startswith("1_") and f.lower().endswith(".wav"))
    m2 = next(f for f in names if f.startswith("2_") and f.lower().endswith(".wav"))
    live = next(f for f in names if f.lower().startswith("live") and f.lower().endswith(".wav"))
    return [os.path.join(audio_dir, f) for f in (m1, m2, live)]


def xlag(a, b, maxlag):
    """lag k (samples) that best satisfies a[n + k] ~ b[n]"""
    n = len(a)
    c = np.fft.irfft(np.fft.rfft(a, 2 * n) * np.conj(np.fft.rfft(b, 2 * n)))
    c = np.concatenate([c[-maxlag:], c[:maxlag + 1]])
    return int(np.argmax(c)) - maxlag


def measure_lag(audio_dir, at=300.0, dur=60.0):
    """seconds the Live-Mix runs behind the mic files (Guest J: 8020 samples = 0.167 s)"""
    p1, p2, pl = mics(audio_dir)
    total = probe(p1) if "probe" in globals() else None
    if total is None:                                   # short takes (sponsored clips, 29 s): measure inside the file
        out = subprocess.run([FF, "-i", p1], capture_output=True, text=True).stderr
        import re
        m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
        total = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else at + dur
    if at + dur > total:                                # 300 s into a 29 s take reads silence → a lag at the search edge
        dur = min(dur, max(4.0, total - 2.0)); at = max(0.0, (total - dur) / 2)
    s = read(p1, at, dur) + read(p2, at, dur)
    return xlag(read(pl, at, dur), s, min(SR, int(dur * SR) // 4)) / SR


def env_db(x, hop=480, win=1440):
    return 10 * np.log10(np.convolve(x ** 2, np.ones(win) / win, mode="same")[::hop] + 1e-12)


def smooth(g, hop_s=0.01, att=0.015, rel=0.25):
    out = np.empty_like(g); y = g[0]
    aa, ar = math.exp(-hop_s / att), math.exp(-hop_s / rel)
    for i, v in enumerate(g):
        a = aa if v > y else ar
        y = a * y + (1 - a) * v; out[i] = y
    return out


def ducked(p1, p2, t0, dur, margin=0.5):
    """mic-time t0..t0+dur, the quiet mic ducked"""
    a = read(p1, t0 - margin, dur + 2 * margin)
    b = read(p2, t0 - margin, dur + 2 * margin)
    diff = env_db(a) - env_db(b)
    floor = 10 ** (FLOOR_DB / 20)
    ga = smooth(np.clip((diff + OPEN_DB + SPAN_DB) / SPAN_DB, 0, 1) * (1 - floor) + floor)
    gb = smooth(np.clip((-diff + OPEN_DB + SPAN_DB) / SPAN_DB, 0, 1) * (1 - floor) + floor)
    t, th = np.arange(len(a)) / SR, np.arange(len(ga)) * 0.01
    y = a * np.interp(t, th, ga) + b * np.interp(t, th, gb)
    s = int(round(margin * SR))
    return y[s:s + int(round(dur * SR))]


def finish(raw, out, lufs, ch=2):
    meas = subprocess.run([FF, "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", raw, "-af", "ebur128", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    I = float([l for l in meas.splitlines() if l.strip().startswith("I:")][-1].split()[1])
    subprocess.run([FF, "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", raw,
                    "-af", f"volume={lufs - I:.2f}dB,alimiter=limit=0.84:attack=2:release=60:level=disabled:latency=1",
                    "-ac", str(ch), "-ar", str(SR), "-c:a", "pcm_s16le", out], check=True)
    os.unlink(raw)
    return I


def master(audio_dir, out, start=0.0, dur=None):
    p1, p2, pl = mics(audio_dir)
    lag = measure_lag(audio_dir)
    if dur is None:
        total = float(subprocess.run([os.path.join(os.path.dirname(FF), "ffprobe"), "-v", "error", "-show_entries", "format=duration",
                                      "-of", "csv=p=0", pl], capture_output=True, text=True).stdout)
        dur = total - start
    raw = out + ".raw.f32"
    with open(raw, "wb") as fh:
        t, step = start, 300.0
        while t < start + dur - 1e-6:
            d = min(step, start + dur - t)
            ducked(p1, p2, t - lag, d).astype(np.float32).tofile(fh)     # Live-Mix clock t = mic clock t - lag
            t += d
            print(f"  {t - start:7.1f}/{dur:.1f}s", flush=True)
    finish(raw, out, -16.0)
    print(f"master: {out}  (Live-Mix lag {lag * SR:.0f} samples)")


def windows(wfile, out_dir, audio_dir, align_dir=None):
    p1, p2, _ = mics(audio_dir)
    lag = measure_lag(audio_dir)
    for rid, wins in json.load(open(wfile)).items():
        old = os.path.join(align_dir, f"{rid}_dialogue.wav") if align_dir else None
        shift = 0
        for attempt in range(2):
            parts = []
            for w0, w1 in wins:
                d = math.ceil((w1 - w0) * 30 - 1e-6) / 30           # the cut's clip lengths are whole frames
                parts.append(ducked(p1, p2, w0 - lag + shift / SR, d))
            y = np.concatenate(parts)
            if not old or attempt:
                break
            ref = read(old, 1.0, 20.0)
            shift = -xlag(ref, y[SR:SR * 21], 4800)                 # normally 0; guards against any codec delay
            if shift == 0:
                break
        if old:
            n = int(subprocess.run([os.path.join(os.path.dirname(FF), "ffprobe"), "-v", "error", "-select_streams", "a:0", "-count_packets",
                                    "-show_entries", "stream=duration_ts", "-of", "csv=p=0", old], capture_output=True, text=True).stdout or len(y))
            y = np.pad(y, (0, max(0, n - len(y))))[:n]
        raw = os.path.join(out_dir, f".{rid}.raw.f32")
        y.astype(np.float32).tofile(raw)
        I = finish(raw, os.path.join(out_dir, f"{rid}_dialogue.wav"), -14.0)
        print(f"{rid}: shift {shift} samples, in {I:.1f} LUFS -> -14", flush=True)


def check(audio_dir, f, at_live, dur=12.0, into=0.0):
    """Is this file the Live-Mix (plain sum of both mics = comb-filtered, metallic)?
    Fit the file to the Live-Mix with one gain: a Live-Mix copy (even through AAC) leaves almost nothing
    (about -37 dB); the ducked mics differ from it by the bleed that was removed (-16..-22 dB).
    at_live = where the FILE starts on the Live-Mix clock (0 for a master); into = seconds into the file to test
    (a master: --at 300, i.e. real talk, not the opening silence)."""
    _, _, pl = mics(audio_dir)
    y = read(f, into, dur)
    if np.sqrt((y ** 2).mean()) < 1e-3:
        print("silence at this point -> pick another --at"); return None
    L = read(pl, at_live + into - 0.2, dur + 0.4)
    n = len(L); c = np.fft.irfft(np.fft.rfft(L, 2 * n) * np.conj(np.fft.rfft(np.pad(y, (0, n - len(y))), 2 * n)))
    m = int(0.4 * SR); c = np.concatenate([c[-m:], c[:m + 1]]); k = int(np.argmax(c)) - m
    rho = c.max() / np.sqrt((y ** 2).sum() * (L ** 2).sum() + 1e-20)
    if k < 0 or rho < 0.3:
        print(f"no match with the Live-Mix here (corr {rho:.2f}) -> wrong start time, not a verdict"); return None
    L = L[k:k + len(y)]
    g = (L @ y) / (L @ L + 1e-20)
    r = 10 * np.log10(((y - g * L) ** 2).mean() / ((y ** 2).mean() + 1e-20) + 1e-20)
    ok = r > -32
    print(f"distance from Live-Mix {r:.1f} dB (corr {rho:.2f})  ->  {'PASS (ducked mics)' if ok else 'FAIL: this is the Live-Mix, metallic'}")
    return ok



if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    opt = lambda k, dv=None: float(args[args.index(k) + 1]) if k in args else dv
    if cmd == "master":
        master(args[0], args[1], opt("--start", 0.0), opt("--dur"))
    elif cmd == "windows":
        windows(args[0], args[1], args[2], args[args.index("--align-to") + 1] if "--align-to" in args else None)
    elif cmd == "check":
        check(args[0], args[1], float(args[2]), into=opt("--at", 0.0))
    else:
        sys.exit(__doc__)
