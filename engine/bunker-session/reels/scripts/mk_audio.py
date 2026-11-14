#!/usr/bin/env python3
"""One dialogue track per reel, with a real crossfade on every cut → public/a/<id>.wav (48 kHz stereo, reel clock).

Remotion played each clip as its own <Audio> with a one-frame dip to 0.2 at both ends — every cut was a dropout and a
hard switch of the room tone (אלון+אייל+דולב 26.10.2026: «חיתוכי קול»). Here each clip is taken PAD s wider on both
sides and overlap-added with equal-power fades of 2·PAD centred on the cut, so the room never jumps and nothing drops.

    python3 mk_audio.py <session> [rN …]
"""
import json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from rpaths import session_paths

S, RM, PUB, WORK = session_paths(sys.argv[:2])
FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
SR, PAD = 48000, 0.035
src = PUB / "dialogue.m4a"
x16 = np.frombuffer(subprocess.run([FF, "-v", "error", "-i", str(WORK / "dialogue16k.wav"), "-f", "f32le", "-"], stdout=subprocess.PIPE,
                                   check=True).stdout, np.float32)
env = 20 * np.log10(np.sqrt((x16[: len(x16) // 160 * 160].reshape(-1, 160) ** 2).mean(1)) + 1e-9)
# the pad reaches PAD s OUTSIDE the clip — into a word that was cut out when the voice runs on («נו» of «אנחנו | היינו»).
# There the pad shrinks to a few ms, so the crossfade never plays a syllable of the cut-out word.
pad = lambda a, b: PAD if env[int(a * 100):max(int(a * 100) + 1, int(b * 100))].max() < -32 else 0.008
(PUB / "a").mkdir(exist_ok=True)


def pcm(f, t, d):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{max(0, t):.4f}", "-t", f"{d:.4f}", "-i", str(f), "-ac", "2", "-ar", str(SR),
                          "-f", "f32le", "-"], stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2)


# work/solo.json [{"from": src, "to": src, "mic": 2}]: one mic only over a crosstalk window — the host starts talking on the guest's
# last word and the cut takes both voices with it (לקוח I 4.11: «המילה בממ״ד נחתכת», «האלה נחתכת»). Level-matched to the dialogue.
SOLO = json.loads((WORK / "solo.json").read_text()) if (WORK / "solo.json").exists() else []
ING = json.loads((S / "ingest.json").read_text()) if SOLO else {}


def read(t, d):
    x = pcm(src, t, d).copy()
    for s in SOLO:
        a, b = max(t, s["from"]), min(t + d, s["to"])
        if b <= a:
            continue
        off = ING["offsets"].get("mic_src", ING["offsets"].get("mic", 0))
        m = pcm(ING["mics"][s["mic"] - 1], a + off, b - a)
        ref = pcm(src, s["from"] - 0.6, 0.6)                      # the voice just before the window sets the level
        mic_ref = pcm(ING["mics"][s["mic"] - 1], s["from"] - 0.6 + off, 0.6)
        m = m * (np.sqrt((ref ** 2).mean()) / max(1e-6, np.sqrt((mic_ref ** 2).mean())))
        i0, k = int(round((a - t) * SR)), min(len(m), len(x) - int(round((a - t) * SR)))
        f = min(k // 2, int(0.03 * SR))
        w = np.ones(k, np.float32)
        if f:
            w[:f] = np.linspace(0, 1, f) if a > s["from"] - 1e-6 and a > t else 1
            w[k - f:] = np.linspace(1, 0, f) if b < t + d - 1e-6 else 1
        x[i0:i0 + k] = x[i0:i0 + k] * (1 - w[:, None]) + m[:k] * w[:, None]
    return x


ids = sys.argv[2:] or [k for k in json.loads((PUB / "plans.json").read_text()) if not k.startswith("_")]
for rid in ids:
    cut = json.loads((PUB / f"{rid}.json").read_text())
    n = int((cut["duration"] + 0.5) * SR)
    out = np.zeros((n, 2), np.float32)
    cl = cut["clips"]
    ends = [c["src"] + c["end"] - c["at"] for c in cl]
    # one pad per cut, the same on both sides, so the two fades stay centred on it
    seam = [min(pad(ends[i], ends[i] + PAD), pad(cl[i + 1]["src"] - PAD, cl[i + 1]["src"])) for i in range(len(cl) - 1)]
    for i, c in enumerate(cl):
        if c.get("mute"):   # picture only — the listener held on screen after the last word («שפשוט יראו שאני יושב שם המום», 28.10)
            continue
        a = seam[i - 1] if i else 0.0
        # the last word rings out under the end card — unless the voice runs on into the next word («זה הבחינה. | התו…»)
        b = seam[i] if i < len(cl) - 1 else (0.25 if pad(ends[i], ends[i] + 0.25) == PAD else 0.02)
        x = read(c["src"] - a, c["end"] - c["at"] + a + b)
        m = len(x)
        g = np.ones(m, np.float32)
        fa, fb = min(m, int(2 * a * SR)), min(m, int((2 * b if i < len(cl) - 1 else b) * SR))
        if fa:
            g[:fa] = np.sin(np.linspace(0, np.pi / 2, fa))
        if fb:
            g[m - fb:] = np.cos(np.linspace(0, np.pi / 2, fb))
        at = int(round((c["at"] - a) * SR))
        j = min(n, at + m)
        out[max(0, at):j] += (x * g[:, None])[max(0, -at):j - at]
    with wave.open(str(PUB / "a" / f"{rid}.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(out, -1, 1) * 32767).astype("<i2").tobytes())
    print(f"{rid}: {len(cl)} clips → a/{rid}.wav {cut['duration']:.2f}s")
