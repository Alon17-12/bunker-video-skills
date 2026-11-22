"""Mic-energy routing for a two-camera Bunker «רז».
  route.py <audio_dir> <cam1.mp4> <cam2.mp4> <out.json>
Measures clocks (cam1/cam2 audio vs Live-Mix, mics vs Live-Mix), the per-mic level every 0.1 s, and builds shots
[cam, t0, t1] on the CAMERA clock: the camera of whoever is talking (mic leads by 6 dB), backchannel (< 1.0 s) ignored,
cuts 0.2 s before the new speaker's first sound and never before the previous speaker stops, shots >= 2.0 s.
"""
import json, subprocess, sys, os
import numpy as np

FF = os.path.expanduser("~/ffmpeg-bin/ffmpeg")
SR = 16000
HOP = 0.1


def load(path, ss=None, t=None, chan_mix=True):
    cmd = [FF, "-v", "error"]
    if ss is not None: cmd += ["-ss", str(ss)]
    if t is not None: cmd += ["-t", str(t)]
    cmd += ["-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)


def lag(ref, sig, max_s=1.0):
    """seconds that sig is late relative to ref (sig[t+lag] ~ ref[t])"""
    n = len(ref) + len(sig)
    N = 1 << (n - 1).bit_length()
    c = np.fft.irfft(np.fft.rfft(sig, N) * np.conj(np.fft.rfft(ref, N)), N)
    m = int(max_s * SR)
    cand = np.concatenate([c[:m], c[-m:]])
    i = int(np.argmax(np.abs(cand)))
    k = i if i < m else i - 2 * m
    return k / SR, float(np.abs(cand).max() / (np.linalg.norm(ref) * np.linalg.norm(sig) + 1e-9))


def env_db(x):
    h = int(HOP * SR)
    n = len(x) // h
    r = np.sqrt(np.mean(x[: n * h].reshape(n, h) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(r)


def main():
    adir, cam1, cam2, out = sys.argv[1:5]
    live = os.path.join(adir, "Live-Mix.wav"); m1 = os.path.join(adir, "1_COMBO-1.wav"); m2 = os.path.join(adir, "2_COMBO-2.wav")
    dur = float(subprocess.run([os.path.expanduser("~/ffmpeg-bin/ffprobe"), "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", live], capture_output=True, text=True).stdout)
    clocks = {}
    for name, f in (("cam1", cam1), ("cam2", cam2), ("mic1", m1), ("mic2", m2)):
        res = []
        for at in (300.0, dur - 300.0):
            ref = load(live, at, 20)
            sig = load(f, at, 20)
            res.append(lag(ref, sig))
        clocks[name] = res
        print(name, "lag vs Live (s, corr):", [(round(a, 4), round(b, 2)) for a, b in res], flush=True)

    e1, e2 = env_db(load(m1)), env_db(load(m2))
    n = min(len(e1), len(e2)); e1, e2 = e1[:n], e2[:n]
    k = np.ones(3) / 3
    s1, s2 = np.convolve(e1, k, "same"), np.convolve(e2, k, "same")
    f1, f2 = np.percentile(s1, 10), np.percentile(s2, 10)
    v1 = (s1 > f1 + 14) & (s1 > s2 + 6)
    v2 = (s2 > f2 + 14) & (s2 > s1 + 6)
    lab = np.where(v1, 1, np.where(v2, 2, 0))

    # speech runs per speaker, gaps < 0.8 s merged
    runs = []
    for i, l in enumerate(lab):
        if l == 0: continue
        t = i * HOP
        if runs and runs[-1][0] == l and t - runs[-1][2] < 0.8:
            runs[-1][2] = t + HOP; runs[-1][3] += 1
        else:
            runs.append([int(l), t, t + HOP, 1])
    # backchannel: a run with < 1.0 s of voiced frames between two runs of the other speaker does not take the screen
    keep = [r for r in runs if r[3] * HOP >= 1.0]
    # merge consecutive same-speaker runs
    merged = []
    for r in keep:
        if merged and merged[-1][0] == r[0]:
            merged[-1][2] = r[2]
        else:
            merged.append(list(r[:3]))
    # shots on the mic clock: switch 0.2 s before the new speaker, not before the previous one stops
    shots = []
    for j, (c, a, b) in enumerate(merged):
        start = a - 0.2
        if shots:
            prev_end_speech = merged[j - 1][2]
            start = max(start, min(prev_end_speech, a))
            shots[-1][2] = start
        shots.append([c, start, b])
    if shots:
        shots[0][1] = 0.0; shots[-1][2] = n * HOP
    # min shot 2.0 s: a short shot takes the camera of the one before it
    changed = True
    while changed:
        changed = False
        for j in range(1, len(shots)):
            if shots[j][2] - shots[j][1] < 2.0 and shots[j][0] != shots[j - 1][0]:
                shots[j][0] = shots[j - 1][0]; changed = True
        m = []
        for s in shots:
            if m and m[-1][0] == s[0]:
                m[-1][2] = s[2]
            else:
                m.append(list(s))
        shots = m
    # mic clock -> camera clock: mic = Live + lag_mic ; cam = Live + lag_cam  ->  cam_t = mic_t - lag_mic + lag_cam
    lm = np.mean([x[0] for x in clocks["mic1"]]); lc = np.mean([x[0] for x in clocks["cam1"]])
    off = -lm + lc
    shots_cam = [[c, round(round((a + off) * 30) / 30, 4), round(round((b + off) * 30) / 30, 4)] for c, a, b in shots]
    tot = {c: sum(b - a for cc, a, b in shots if cc == c) for c in (1, 2)}
    talk = {1: float((lab == 1).sum() * HOP), 2: float((lab == 2).sum() * HOP)}
    json.dump({"clocks": clocks, "mic_to_cam": off, "floors": [float(f1), float(f2)], "talk_s": talk, "screen_s": tot,
               "shots": shots_cam, "env": {"e1": [round(float(x), 1) for x in s1], "e2": [round(float(x), 1) for x in s2]}},
              open(out, "w"))
    print(f"shots {len(shots_cam)}  talk {talk}  screen {tot}  mic->cam {off:+.4f}s", flush=True)


main()
