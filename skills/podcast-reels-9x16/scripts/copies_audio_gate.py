# -*- coding: utf-8 -*-
"""Re-master the audio of the per-camera work copies so each layer carries ONLY its own speaker.

    python copies_audio_gate.py "<draft folder>" --prefix aviel [--target -16] [--margin 6] [--floor -30] [--write]

Why: the delivery format plays BOTH camera layers at volume 1 (each file carries its own mic). With the
RODECASTER channels gain-baked by +19…+26 dB, the *bleed* of the guest in the host's mic comes up to within
1 dB of the guest's own mic (0922 reel 3: cam1 −15.2 dBFS vs cam2 −14.3 dBFS on a guest-only stretch), a
few ms late — two near-equal delayed copies summed = a comb filter, "כאילו לא שומעים ממנו". Reel 5 also
exposed a second fault: an appended piece whose AAC was encoded separately and stitched with `-c copy`.
Both go away with ONE continuous audio encode per camera, gated by mic ownership:
  * ownership per 20 ms from the raw mic wavs on the copy clock (`ccstudio-<prefix>-mic1/2.wav`):
    mic n owns when its envelope beats the other by --margin dB (hysteresis: it keeps ownership until
    the other beats it by the same margin); neither owns silence → both sit at the floor;
  * gain per camera so the OWNED speech lands at --target LUFS (limiter at −1 dBFS);
  * the other camera's audio at --floor dB during the other's speech, 60 ms ramps, so room tone stays.
Video stream copied; the draft is not touched (segments keep volume 1). Read-only without --write.
"""
import argparse, os, re, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
FF = str(paths.FFMPEG); SR = 48000
ap = argparse.ArgumentParser(); ap.add_argument("draft"); ap.add_argument("--prefix", required=True); ap.add_argument("--target", type=float, default=-16.0)
ap.add_argument("--margin", type=float, default=6.0); ap.add_argument("--floor", type=float, default=-30.0); ap.add_argument("--hop", type=float, default=0.02)
ap.add_argument("--write", action="store_true"); A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.draft
def pcm(path):
    r = subprocess.run([FF, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True); return np.frombuffer(r.stdout, np.float32).copy()
def lufs_of(x):
    r = subprocess.run([FF, "-v", "info", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", "ebur128", "-f", "null", "-"], input=x.astype(np.float32).tobytes(), capture_output=True, text=False).stderr.decode(errors="ignore")
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r); return float(m[-1]) if m else None
m = {c: pcm(D / f"ccstudio-{A.prefix}-mic{c}.wav") for c in (1, 2)}; n = min(len(m[1]), len(m[2])); m = {c: m[c][:n] for c in m}
hop = int(SR * A.hop); k = n // hop
env = {c: 20 * np.log10(np.sqrt((m[c][:k * hop].reshape(k, hop) ** 2).mean(1)) + 1e-9) for c in m}
floor_db = {c: float(np.percentile(env[c], 15)) for c in m}
own = np.zeros(k, np.int8); cur = 0
for i in range(k):
    d12 = env[1][i] - env[2][i]; loud1 = env[1][i] > floor_db[1] + 8; loud2 = env[2][i] > floor_db[2] + 8
    if cur == 1 and (d12 < -A.margin and loud2): cur = 2
    elif cur == 2 and (d12 > A.margin and loud1): cur = 1
    elif cur == 0:
        if d12 > A.margin and loud1: cur = 1
        elif d12 < -A.margin and loud2: cur = 2
    if not (loud1 or loud2): cur = 0
    own[i] = cur
share = {c: float((own == c).mean()) for c in (1, 2)}; print(f"ownership: mic1 {share[1]*100:.1f}% | mic2 {share[2]*100:.1f}% | silence {(own==0).mean()*100:.1f}%")
ramp = int(0.06 / A.hop)
out = {}
for c in (1, 2):
    g = np.where(own == c, 1.0, np.where(own == 0, 1.0, 10 ** (A.floor / 20)))          # own speech 1, the other's speech at the floor, silence untouched
    g = np.convolve(g, np.ones(ramp) / ramp, mode="same")                                 # 60 ms ramps
    gs = np.repeat(g, hop); gs = np.concatenate([gs, np.full(n - len(gs), gs[-1])])[:n]
    owned = m[c][:k * hop].reshape(k, hop)[own == c].ravel()
    have = lufs_of(owned) if len(owned) > SR else lufs_of(m[c])
    gain = 10 ** ((A.target - have) / 20); y = m[c] * gs * gain
    peak = float(np.abs(y).max()); lim = min(1.0, 0.891 / peak) if peak > 0.891 else 1.0
    print(f"  cam{c}: owned speech {have:.1f} LUFS → gain {20*np.log10(gain):+.1f} dB · peak {20*np.log10(peak+1e-9):+.1f} dBFS → limiter ×{lim:.2f} · {len(owned)/SR:.0f}s owned")
    out[c] = (y, gain)
if not A.write: print("(dry run — add --write)"); sys.exit()
for c in (1, 2):
    y, gain = out[c]; wav = D / f"ccstudio-{A.prefix}-cam{c}.gated.wav"; mp4 = D / f"ccstudio-{A.prefix}-cam{c}.mp4"; tmp = D / f"ccstudio-{A.prefix}-cam{c}.tmp.mp4"
    subprocess.run([FF, "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", "alimiter=limit=0.891:attack=5:release=50", "-c:a", "pcm_s16le", str(wav)], input=y.astype(np.float32).tobytes(), check=True)
    subprocess.run([FF, "-v", "error", "-y", "-i", str(mp4), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", str(tmp)], check=True)
    os.replace(tmp, mp4); wav.unlink()
    r = subprocess.run([FF, "-hide_banner", "-i", str(mp4), "-vn", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    print(f"  ✓ cam{c}: audio re-muxed, integrated {re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1]} LUFS")
