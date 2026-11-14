# -*- coding: utf-8 -*-
"""Render the timeline AUDIO of a reel project the way CapCut would mix it — base footage voice, beds with
volume keyframes and fades, SFX — to a wav, and report what a listener would call "a sound error":
clipping, silence inside a reel, a bed that stops dead, a piece that reads past its file, a level jump.

    python reel_audio_mix.py "<project>" --from 191.4 --to 258.9 --out /path/r3.wav

Read-only. Paths with CapCut's `##_draftpath_placeholder_…_##` prefix resolve to the draft folder.
"""
import argparse, json, os, re, subprocess, sys, numpy as np
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
US = 1_000_000; FF = str(paths.FFMPEG); SR = 48000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--from", dest="t0", type=float, default=0); ap.add_argument("--to", dest="t1", type=float, default=None); ap.add_argument("--out", default="")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]
res = lambda p: re.sub(r"##_draftpath_placeholder_[^#]+_##", str(D), p)
byid = {m["id"]: m for v in mats.values() if isinstance(v, list) for m in v if isinstance(m, dict) and "id" in m}
t0 = A.t0; t1 = A.t1 if A.t1 is not None else d["duration"] / US; n = int((t1 - t0) * SR); mix = np.zeros(n, np.float32); issues = []
def decode(path, s0, dur):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{s0:.4f}", "-t", f"{dur:.4f}", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32)
for t in d["tracks"]:
    if t["type"] not in ("video", "audio"): continue
    for s in t["segments"]:
        m = byid.get(s["material_id"]);  vol = s.get("volume", 1.0)
        if not m or vol <= 0 or (t["type"] == "video" and m.get("type") != "video"): continue
        a = s["target_timerange"]["start"] / US; b = a + s["target_timerange"]["duration"] / US
        if b <= t0 or a >= t1: continue
        src = s["source_timerange"]["start"] / US; path = res(m["path"]); name = t.get("name") or t["type"]
        if not os.path.exists(path): issues.append(f"{name} {a:.2f}: file missing {os.path.basename(path)}"); continue
        fdur = m.get("duration", 0) / US
        if m.get("type") != "photo" and src + (b - a) > fdur + 0.005: issues.append(f"{name} {a:.2f}: reads {src + (b - a) - fdur:.2f}s past the file end ({os.path.basename(path)})")
        x = decode(path, src, b - a); L = min(len(x), int((b - a) * SR)); x = x[:L].copy()
        if L < int((b - a) * SR) - SR // 20: issues.append(f"{name} {a:.2f}: decoded {L / SR:.2f}s of {b - a:.2f}s")
        g = np.full(L, vol, np.float32)
        for gr in s.get("common_keyframes", []):
            if gr["property_type"] == "KFTypeVolume":
                ks = sorted(gr["keyframe_list"], key=lambda k: k["time_offset"]); tt = np.arange(L) / SR + src
                g = np.interp(tt, [k["time_offset"] / US for k in ks], [k["values"][0] for k in ks]).astype(np.float32)
        for r in s.get("extra_material_refs", []):
            f = byid.get(r)
            if f and f.get("type") == "audio_fade":
                fi, fo = f["fade_in_duration"] / US, f["fade_out_duration"] / US
                if fi > 0: k = min(L, int(fi * SR)); g[:k] *= np.linspace(0, 1, k, dtype=np.float32)
                if fo > 0: k = min(L, int(fo * SR)); g[L - k:] *= np.linspace(1, 0, k, dtype=np.float32)
        y = x * g; i0 = int((a - t0) * SR); j0 = 0
        if i0 < 0: j0 = -i0; i0 = 0
        k = min(L - j0, n - i0)
        if k > 0: mix[i0:i0 + k] += y[j0:j0 + k]
        if name not in ("video",) and L > SR // 2:
            tail = 20 * np.log10(np.sqrt((y[-SR // 10:] ** 2).mean()) + 1e-9); body = 20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-9)
            if tail > body - 6 and fo == 0 and b < t1 - 0.05 and t["type"] == "audio" and (b - a) > 5: issues.append(f"{name} {a:.2f}–{b:.2f}: ends without a fade at {tail:.1f} dB")
peak = float(np.abs(mix).max()); clip = int((np.abs(mix) > 1.0).sum())
hop = SR // 100; kk = n // hop; e = 20 * np.log10(np.sqrt((mix[:kk * hop].reshape(kk, hop) ** 2).mean(1)) + 1e-9)
sil = e < -60; i = 0; gaps = []
while i < kk:
    if sil[i]:
        j = i
        while j < kk and sil[j]: j += 1
        if j - i >= 50: gaps.append((round(t0 + i / 100, 2), round((j - i) / 100, 2)))
        i = j
    else: i += 1
jumps = [(round(t0 + i / 100, 2), round(float(e[i + 1] - e[i]), 1)) for i in np.where((np.abs(np.diff(e)) > 30) & (np.minimum(e[1:], e[:-1]) > -45))[0]]
print(f"mix {t0:.2f}–{t1:.2f}: peak {20 * np.log10(peak + 1e-9):+.1f} dBFS · clipped samples {clip} · silences ≥0.5s {gaps[:8]} · level jumps >30dB inside sound {jumps[:8]}")
for x in issues: print("  ⚠️", x)
if not issues and not clip and not gaps: print("  ✓ nothing a listener would call an error")
if A.out:
    subprocess.run([FF, "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s16le", A.out], input=np.clip(mix, -1, 1).astype(np.float32).tobytes(), check=True); print("  wav:", A.out)
