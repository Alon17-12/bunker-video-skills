# -*- coding: utf-8 -*-
"""Approved voice chain for a single speaker in a room (Alon, 16.11.26, לקוחה D course: «מושלם! זה הסאונד»).

  ~/bunker-video-engine/.venv/bin/python voice_clean.py   # needs: uv pip install nara_wpe deepfilternet soundfile <source.wav|.mp4> <out.wav> [--match tone.json] [--lufs -16]

  1. WPE dereverb (nara_wpe, taps 40, delay 2, 5 iterations, 60 s blocks with 1 s cross-fade) — the room echo
  2. DeepFilterNet3 — noise (so NO afftdn afterwards: it thinned the voice and delayed it 25 ms)
  3. ffmpeg: highpass 60 · optional FIR tone match (--match: {"fc":[...],"gain":[...]}, e.g. a broadcast-sound
     take matched to the same speaker's mic) · gentle expander (2:1, −10 dB range) for the room tail between
     words · compressor 2.5:1 from −24 dB · body +3 dB @180 Hz · −1.5 dB @3 kHz · linear gain to --lufs ·
     limiter −1.5 dBTP
  4. sync: cross-correlate with the source and trim the measured filter delay (17–28 ms) so the voice sits on
     the picture again; prints the residual (must be 0.00 ms)

Measured on 30 s samples vs the previous chain: room tail 80–200 ms after a word −4 dB, pauses −17 dB.
Speed ≈ 0.5× realtime on an M4 Pro (CPU). Output mono 48 kHz / 24-bit, same timeline as the source.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
import numpy as np, soundfile as sf
from nara_wpe.wpe import wpe
from nara_wpe.utils import stft, istft

FF = str(Path.home() / "ffmpeg-bin" / "ffmpeg")
SR = 48000
ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--match"); ap.add_argument("--lufs", type=float, default=-16.0)
A = ap.parse_args()
src, out = Path(A.src), Path(A.out)


def load(p, ss=None, t=None):
    cmd = [FF, "-v", "error"] + (["-ss", str(ss), "-t", str(t)] if ss is not None else []) + \
          ["-i", str(p), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).copy()


# 1. WPE in blocks
x = load(src); B, O = 20 * SR, SR   # 20 s: 60 s blocks held ~4 GB each
y = np.zeros_like(x); w = np.zeros_like(x)
for s in range(0, len(x), B):
    a, b = max(0, s - O), min(len(x), s + B + O)
    S = stft(x[a:b][None], size=1024, shift=256)
    Y = wpe(S.transpose(2, 0, 1), taps=40, delay=2, iterations=5, statistics_mode="full").transpose(1, 2, 0)
    r = np.ones(b - a, np.float32)
    if a > 0: r[:O] = np.linspace(0, 1, O)
    if b < len(x): r[-O:] = np.linspace(1, 0, O)
    y[a:b] += istft(Y, size=1024, shift=256)[0][: b - a] * r; w[a:b] += r
wpe_wav = out.with_suffix(".wpe.wav"); sf.write(wpe_wav, y / np.maximum(w, 1e-6), SR)

# 2. DeepFilterNet3
from df.enhance import enhance, init_df, load_audio, save_audio  # noqa: E402
m, st, _ = init_df(); au, _ = load_audio(str(wpe_wav), sr=st.sr())
dry = out.with_suffix(".dry.wav"); save_audio(str(dry), enhance(m, st, au), st.sr()); wpe_wav.unlink()

# 3. tone + dynamics + level
match = ""
if A.match:
    T = json.loads(Path(A.match).read_text())
    match = "firequalizer=gain_entry='" + ";".join(f"entry({f},{g})" for f, g in zip(T["fc"], T["gain"])) + "',"
PRE = ("aformat=channel_layouts=mono,highpass=f=60:p=2," + match +
       "agate=threshold=0.03:ratio=2:range=0.32:attack=4:release=120:knee=4,"
       "acompressor=threshold=-24dB:ratio=2.5:attack=10:release=200:makeup=3,"
       "equalizer=f=180:t=q:w=0.8:g=3,equalizer=f=3000:t=q:w=1.0:g=-1.5")
r = subprocess.run([FF, "-hide_banner", "-nostats", "-i", str(dry), "-af", PRE + f",loudnorm=I={A.lufs}:TP=-1.5:print_format=json",
                    "-f", "null", "-"], capture_output=True, text=True)
I = float(json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))["input_i"])
tmp = out.with_suffix(".tmp.wav")
subprocess.run([FF, "-v", "error", "-y", "-i", str(dry), "-af", PRE + f",volume={A.lufs - I:.2f}dB,"
                "alimiter=limit=0.84:attack=3:release=60:level=false,aresample=48000", "-c:a", "pcm_s24le", str(tmp)], check=True)
dry.unlink()

# 4. sync back onto the source
ss = min(60.0, max(0.0, len(x) / SR - 35))
a_, b_ = load(src, ss, 30), load(tmp, ss, 30); n = min(len(a_), len(b_)); a_, b_ = a_[:n], b_[:n]
xc = lambda p, q: np.fft.irfft(np.fft.rfft(q, 2 * n) * np.conj(np.fft.rfft(p, 2 * n)))
c0 = xc(a_, b_); k0 = int(np.argmax(np.r_[c0[:4800], c0[-4800:]])); lag = k0 if k0 < 4800 else k0 - 9600   # both directions
if abs(lag) > 24:
    t2 = out.with_suffix(".t2.wav")
    fx = f"atrim=start_sample={lag},asetpts=N/SR/TB,apad=pad_len={lag}" if lag > 0 else f"adelay={-lag}S"
    subprocess.run([FF, "-v", "error", "-y", "-i", str(tmp), "-af", fx,
                    "-c:a", "pcm_s24le", str(t2)], check=True)
    t2.replace(tmp)
c = xc(a_, load(tmp, ss, 30)[:n]); k = int(np.argmax(np.r_[c[:4800], c[-4800:]])); k = k if k < 4800 else k - 9600
tmp.replace(out)
print(f"{out.name}: delay {lag / 48:.1f} ms trimmed → residual {k / 48:.2f} ms · in {I:.1f} LUFS → {A.lufs}", flush=True)
