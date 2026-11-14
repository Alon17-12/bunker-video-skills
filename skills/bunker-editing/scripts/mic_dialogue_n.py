"""Dialogue from N mics (3+ speakers), never from the Live-Mix — mic_dialogue.py generalised.

Same rule as the two-mic version (Alon approved the sound 12.10.2026): every mic that is not within OPEN_DB of
the loudest mic at that moment is ducked to FLOOR_DB, so each voice reaches the mix once (no comb filter).
Added for the 3-speaker pilot (אלון + אייל + דולב, 21.10.2026):
  - per-mic level match: each mic is gained so its OWN speech sits at the same level (the USB mic ran ~6 dB
    hotter than COMBO-2), measured on the moments that mic clearly leads;
  - a light voice chain on the master: high-pass 75 Hz, gentle compression, then -16 LUFS / -1.5 dBTP.

Added 21.10.2026 (Alon picked «G» after 5 rounds of samples on the same 28 s):
  --eq K=R      match mic K's long-term speech tone to mic R's (1/3-octave, ±9 dB, level-neutral, linear-phase FIR — zero
                shift). The USB mic (Alon, mic 3) ran ~8 dB short of bass and air next to the RØDECaster XLR inputs.
  --gate K      mic K opens only while the transcript has its speaker talking (0.25 s pre-roll, ±0.15 s), or when it
                clearly leads (≥ 6 dB, a laugh); otherwise −26 dB. For a mic that hears another speaker almost as loud as
                its own (Eyal's mic, next to Alon and gained +8.9 dB, was open 90 % of Alon's speech → Alon heard twice,
                late and roomy: «זה נשמע רחוק / פחות טוב»). `bleed` prints the matrix that shows which mic needs it.
                With --words (27.10.2026, אורח C, Alon: «הגרסה הזאת ממש טובה»): measured on the SAME voices through
                both mics (match_fir_same_voice) — R should be the XLR mic of a speaker sitting next to K's. The tone
                match above put another person's voice into the EQ (+9 dB at 111 Hz, −8 dB at 4.5 kHz → «מעוות ומלא gain»).
                Levels: with --words, RMS over each speaker's own words, measured after the EQ (the lead-median left the
                USB mic 3 dB over the others, on the limiter).
  --eq-boost D  old tone match only (no --words): cap its boost at +D dB (default 9).
  --words <transcript.json>   required with --gate (words {text,start_s,end_s,mic} on the Live-Mix clock)

  master <audio_dir> <out.wav> [--start S --dur D] [--eq 3=2] [--gate 2 --words <transcript.json>]
  bleed  <audio_dir>                                   how loud each speaker is in every other mic (dB under its own)
  windows <windows.json> <out_dir> <audio_dir>      {"r1": [[w0, w1], ...]} on the Live-Mix clock → rN_dialogue.wav (-14 LUFS)
  check  <audio_dir> <file.wav> <file_start_on_live_mix_clock> [--at S]
"""
import json, math, os, subprocess, sys
import numpy as np

FF = os.path.expanduser("~/ffmpeg-bin/ffmpeg")
FP = os.path.expanduser("~/ffmpeg-bin/ffprobe")
SR = 48000
FLOOR_DB, OPEN_DB, SPAN_DB = -20.0, 6.0, 6.0
CHAIN = "highpass=f=75,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=180:makeup=1"


def read(path, t0, dur):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{max(0.0, t0):.6f}", "-t", f"{dur:.6f}", "-i", path,
                          "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    x = np.concatenate([np.zeros(int(round(max(0.0, -t0) * SR))), x])
    n = int(round(dur * SR))
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def mics(audio_dir):
    names = sorted(f for f in os.listdir(audio_dir) if f.lower().endswith(".wav") and not f.startswith("._"))
    ms = [os.path.join(audio_dir, f) for f in names if f[:1].isdigit() and f[1:2] == "_"]
    live = next(os.path.join(audio_dir, f) for f in names if f.lower().startswith("live"))
    return ms, live


def xlag(a, b, maxlag):
    n = len(a)
    c = np.fft.irfft(np.fft.rfft(a, 2 * n) * np.conj(np.fft.rfft(b, 2 * n)))
    c = np.concatenate([c[-maxlag:], c[:maxlag + 1]])
    return int(np.argmax(c)) - maxlag


def measure_lag(audio_dir, at=300.0, dur=60.0):
    ms, live = mics(audio_dir)
    s = sum(read(m, at, dur) for m in ms)
    return xlag(read(live, at, dur), s, SR) / SR


def env_db(x, hop=480, win=1440):
    return 10 * np.log10(np.convolve(x ** 2, np.ones(win) / win, mode="same")[::hop] + 1e-12)


def smooth(g, hop_s=0.01, att=0.015, rel=0.25):
    out = np.empty_like(g); y = g[0]
    aa, ar = math.exp(-hop_s / att), math.exp(-hop_s / rel)
    for i, v in enumerate(g):
        a = aa if v > y else ar
        y = a * y + (1 - a) * v; out[i] = y
    return out


def match_gains(ms, at=300.0, dur=900.0, firs=None, words=None, lag=0.0):
    """dB to add per mic so each mic's own speech lands at the same level — measured after --eq, so a bass boost
    cannot leave that mic hotter than the rest. With a transcript: RMS over the words only that mic's speaker says
    (no overlap). The envelope-lead median left the USB mic 3–4 dB over the others, on the limiter (אורח C 27.10.2026)."""
    from scipy.signal import fftconvolve
    xs = [read(m, at, dur) for m in ms]
    for k, h in (firs or {}).items():
        xs[k] = fftconvolve(xs[k], h, mode="same")
    lead = []
    if words:
        n = len(xs[0])
        own = np.zeros((len(ms), n), bool)
        for w in words:
            i, j = int((w["start_s"] - lag - at) * SR), int((w["end_s"] - lag - at) * SR)
            if 0 <= i < j <= n and 0 < w["mic"] <= len(ms):
                own[w["mic"] - 1, i:j] = True
        solo = own & (own.sum(axis=0) == 1)
        for k in range(len(ms)):
            lead.append(10 * math.log10(np.mean(xs[k][solo[k]] ** 2) + 1e-12) if solo[k].sum() > 20 * SR else None)
    if not words or None in lead:
        e = np.array([env_db(x, hop=4800, win=4800) for x in xs])        # 0.1 s frames
        lead = []
        for k in range(len(ms)):
            others = np.max(np.delete(e, k, axis=0), axis=0)
            sel = (e[k] - others > 12) & (e[k] > -45)
            lead.append(float(np.median(e[k][sel])) if sel.sum() > 20 else float(np.percentile(e[k], 95)))
    ref = max(lead)
    return [ref - v for v in lead]


def speech_spectrum(xs, k, n=4096):
    e = np.array([env_db(x, hop=4800, win=4800) for x in xs])
    sel = np.where((e[k] - np.max(np.delete(e, k, axis=0), axis=0) > 12) & (e[k] > -45))[0]
    S, c = np.zeros(n // 2 + 1), 0
    for i in sel[::3]:
        seg = xs[k][i * 4800:i * 4800 + n]
        if len(seg) == n:
            S += np.abs(np.fft.rfft(seg * np.hanning(n))) ** 2; c += 1
    return S / max(c, 1)


BANDS = 70 * 2 ** (np.arange(0, 7.6, 1 / 3))


def _fir(g):
    from scipy.signal import firwin2
    fr = np.concatenate([[0], BANDS, [SR / 2]]) / (SR / 2)
    return firwin2(2047, np.clip(fr, 0, 1), 10 ** (np.concatenate([[g[0]], g, [g[-1]]]) / 20))


def _bands(S, f):
    return np.array([10 * np.log10(S[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].sum() + 1e-30) for c in BANDS])


def match_fir(ms, k, ref, at=300.0, dur=900.0, n=4096, boost=9.0):
    """linear-phase FIR that moves mic k's speech tone onto mic ref's (level stays with match_gains)"""
    xs = [read(m, at, dur) for m in ms]
    Sk, Sr = speech_spectrum(xs, k, n), speech_spectrum(xs, ref, n)
    f = np.fft.rfftfreq(n, 1 / SR)
    g = _bands(Sr, f) - _bands(Sk, f)
    g = np.clip(g - np.median(g[(BANDS > 300) & (BANDS < 3000)]), -9, boost)
    print(f"EQ mic {k + 1} → mic {ref + 1}:", " ".join(f"{int(c)}:{x:+.0f}" for c, x in zip(BANDS[::2], g[::2])), flush=True)
    return _fir(g)


def match_fir_same_voice(ms, k, ref, words, lag, at=300.0, dur=1500.0, n=4096):
    """FIR that makes mic k sound like mic ref, measured on the SAME voices (Alon: «הגרסה הזאת ממש טובה», אורח C 27.10.2026).
    Mic k's speaker is heard in mic ref too (bleed), and mic ref's speaker in mic k, so ref/k on one voice = the mic difference
    × a distance tilt; on the other voice the tilt is reversed, and the mean of the two keeps the mic difference. Matching to
    another person's voice (match_fir) bakes that voice in: +9 dB at 111 Hz and −8 dB at 4.5 kHz → boomy, dull, «מעוות».
    Needs the two speakers near enough that each is heard in the other's mic (≈ −10 dB there)."""
    xs = [read(ms[i], at, dur) for i in (k, ref)]
    N = len(xs[0]); f = np.fft.rfftfreq(n, 1 / SR)
    own = np.zeros((len(ms), N), bool)
    for w in words:
        i, j = int((w["start_s"] - lag - at) * SR), int((w["end_s"] - lag - at) * SR)
        if 0 <= i < j <= N and 0 < w["mic"] <= len(ms):
            own[w["mic"] - 1, i:j] = True
    solo = own & (own.sum(axis=0) == 1)
    diffs = []
    for spk in (k, ref):
        S = [np.zeros(n // 2 + 1), np.zeros(n // 2 + 1)]; c = 0
        for i in range(0, N - n, n // 2):
            if solo[spk, i:i + n].all():
                for a in (0, 1):
                    S[a] += np.abs(np.fft.rfft(xs[a][i:i + n] * np.hanning(n))) ** 2
                c += 1
        if c < 500:
            raise SystemExit(f"--eq {k + 1}={ref + 1}: only {c} solo frames of speaker {spk + 1} — use more of the file")
        diffs.append(_bands(S[1], f) - _bands(S[0], f))
    g = (diffs[0] + diffs[1]) / 2
    g = np.clip(g - np.median(g[(BANDS > 300) & (BANDS < 3000)]), -12, 10)
    print(f"EQ mic {k + 1} → mic {ref + 1} (same voices):", " ".join(f"{int(c)}:{x:+.0f}" for c, x in zip(BANDS[::2], g[::2])), flush=True)
    return _fir(g)


def talking(words, mic, t0, n, pre=0.25, pad=0.15):
    """10 ms frames (from t0, Live-Mix clock) where the transcript has `mic` speaking"""
    a = np.zeros(n, bool)
    for w in words:
        if w["mic"] == mic and w["end_s"] > t0 - 1 and w["start_s"] < t0 + n * 0.01 + 1:
            i, j = int((w["start_s"] - pad - pre - t0) / 0.01), int((w["end_s"] + pad - t0) / 0.01)
            a[max(0, i):max(0, j)] = True
    return a


def ducked(ms, gains, t0, dur, margin=0.5, firs=None, gate=(), words=None, lag=0.0):
    from scipy.signal import fftconvolve
    xs = [read(m, t0 - margin, dur + 2 * margin) * 10 ** (g / 20) for m, g in zip(ms, gains)]
    for k, h in (firs or {}).items():
        xs[k] = fftconvolve(xs[k], h, mode="same")                      # linear phase, centred: no shift
    e = np.array([env_db(x) for x in xs])
    floor = 10 ** (FLOOR_DB / 20)
    t = np.arange(len(xs[0])) / SR
    th = np.arange(e.shape[1]) * 0.01
    y = np.zeros_like(xs[0])
    for k, x in enumerate(xs):
        diff = e[k] - np.max(np.delete(e, k, axis=0), axis=0)
        if k in gate:
            tk = talking(words, k + 1, t0 - margin + lag, e.shape[1])
            fl = 10 ** (-26 / 20)
            g = smooth(np.maximum(tk.astype(float), np.clip((diff - 6.0) / 6.0, 0, 1)) * (1 - fl) + fl)
        else:
            g = smooth(np.clip((diff + OPEN_DB + SPAN_DB) / SPAN_DB, 0, 1) * (1 - floor) + floor)
        y += x * np.interp(t, th, g)
    s = int(round(margin * SR))
    return y[s:s + int(round(dur * SR))]


def finish(raw, out, lufs, ch=2):
    pre = out + ".chain.wav"
    subprocess.run([FF, "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", raw, "-af", CHAIN,
                    "-c:a", "pcm_f32le", pre], check=True)
    meas = subprocess.run([FF, "-hide_banner", "-i", pre, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float([l for l in meas.splitlines() if l.strip().startswith("I:")][-1].split()[1])
    subprocess.run([FF, "-v", "error", "-y", "-i", pre,
                    "-af", f"volume={lufs - I:.2f}dB,alimiter=limit=0.84:attack=2:release=60:level=disabled:latency=1",
                    "-ac", str(ch), "-ar", str(SR), "-c:a", "pcm_s16le", out], check=True)
    os.unlink(raw); os.unlink(pre)
    return I


def setup(audio_dir, eq=None, boost=9.0, words=None):
    ms, _ = mics(audio_dir)
    lag = measure_lag(audio_dir)
    firs = {k - 1: (match_fir_same_voice(ms, k - 1, r - 1, words, lag) if words else match_fir(ms, k - 1, r - 1, boost=boost))
            for k, r in (eq or {}).items()}
    gains = match_gains(ms, firs=firs, words=words, lag=lag)
    print("mics:", [os.path.basename(m) for m in ms], "gains dB:", [round(g, 1) for g in gains], f"lag {lag * SR:.0f} samples", flush=True)
    return ms, lag, gains, firs


def master(audio_dir, out, start=0.0, dur=None, eq=None, gate=(), words=None, boost=9.0):
    W = json.load(open(words))["words"] if words else None
    ms, lag, gains, firs = setup(audio_dir, eq, boost, W)
    gate = {k - 1 for k in gate}
    if gate and not W:
        raise SystemExit("--gate needs --words <transcript.json>")
    if dur is None:
        _, live = mics(audio_dir)
        total = float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", live],
                                     capture_output=True, text=True).stdout)
        dur = total - start
    raw = out + ".raw.f32"
    with open(raw, "wb") as fh:
        t, step = start, 300.0
        while t < start + dur - 1e-6:
            d = min(step, start + dur - t)
            ducked(ms, gains, t - lag, d, firs=firs, gate=gate, words=W, lag=lag).astype(np.float32).tofile(fh)
            t += d
            print(f"  {t - start:7.1f}/{dur:.1f}s", flush=True)
    finish(raw, out, -16.0)
    json.dump({"gains_db": gains, "lag_samples": round(lag * SR), "eq": {str(k + 1): True for k in firs}, "gate": sorted(k + 1 for k in gate)}, open(out + ".json", "w"))
    print(f"master: {out}")


def windows(wfile, out_dir, audio_dir):
    ms, lag, gains, _ = setup(audio_dir)
    for rid, wins in json.load(open(wfile)).items():
        parts = [ducked(ms, gains, w0 - lag, math.ceil((w1 - w0) * 30 - 1e-6) / 30) for w0, w1 in wins]
        raw = os.path.join(out_dir, f".{rid}.raw.f32")
        np.concatenate(parts).astype(np.float32).tofile(raw)
        I = finish(raw, os.path.join(out_dir, f"{rid}_dialogue.wav"), -14.0)
        print(f"{rid}: in {I:.1f} LUFS -> -14", flush=True)


def check(audio_dir, f, at_live, dur=12.0, into=0.0):
    _, live = mics(audio_dir)
    y = read(f, into, dur)
    if np.sqrt((y ** 2).mean()) < 1e-3:
        print("silence at this point -> pick another --at"); return None
    L = read(live, at_live + into - 0.2, dur + 0.4)
    n = len(L); c = np.fft.irfft(np.fft.rfft(L, 2 * n) * np.conj(np.fft.rfft(np.pad(y, (0, n - len(y))), 2 * n)))
    m = int(0.4 * SR); c = np.concatenate([c[-m:], c[:m + 1]]); k = int(np.argmax(c)) - m
    rho = c.max() / np.sqrt((y ** 2).sum() * (L ** 2).sum() + 1e-20)
    if k < 0 or rho < 0.3:
        print(f"no match with the Live-Mix here (corr {rho:.2f})"); return None
    L = L[k:k + len(y)]
    g = (L @ y) / (L @ L + 1e-20)
    r = 10 * np.log10(((y - g * L) ** 2).mean() / ((y ** 2).mean() + 1e-20) + 1e-20)
    ok = r > -32
    print(f"distance from Live-Mix {r:.1f} dB (corr {rho:.2f})  ->  {'PASS (ducked mics)' if ok else 'FAIL: Live-Mix'}")
    return ok


def bleed(audio_dir, at=300.0, dur=900.0):
    ms, _ = mics(audio_dir)
    gains = match_gains(ms, at, dur)
    xs = [read(m, at, dur) for m in ms]
    e = np.array([env_db(x, hop=4800, win=4800) for x in xs]) + np.array(gains)[:, None]
    print("row = mic, column = speaker; dB under that speaker's own mic (after level match). > -15 → consider --gate")
    for k in range(len(ms)):
        row = []
        for j in range(len(ms)):
            lead = (e[j] - np.max(np.delete(e, j, axis=0), axis=0) > 6) & (e[j] > -45)
            row.append("   —  " if j == k else f"{np.median(e[k][lead] - e[j][lead]):6.1f}")
        print(f"mic {k + 1}:", " ".join(row))


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    opt = lambda k, dv=None: float(args[args.index(k) + 1]) if k in args else dv
    sopt = lambda k: args[args.index(k) + 1] if k in args else None
    if cmd == "master":
        eq = dict(tuple(map(int, x.split("="))) for x in sopt("--eq").split(",")) if sopt("--eq") else None
        gate = [int(x) for x in sopt("--gate").split(",")] if sopt("--gate") else []
        master(args[0], args[1], opt("--start", 0.0), opt("--dur"), eq=eq, gate=gate, words=sopt("--words"), boost=opt("--eq-boost", 9.0))
    elif cmd == "bleed":
        bleed(args[0])
    elif cmd == "windows":
        windows(args[0], args[1], args[2])
    elif cmd == "check":
        check(args[0], args[1], float(args[2]), into=opt("--at", 0.0))
    else:
        sys.exit(__doc__)
