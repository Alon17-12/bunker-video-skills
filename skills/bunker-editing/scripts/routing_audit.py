#!/usr/bin/env python3
"""Routing QA of the live-switched «מקור»: which camera is on screen vs who is talking (the two mics), every 0.5 s.

    routing_audit.py <session dir> [--from 6.0 --to 842.1] [--out <session>/פרק/ניתוב.json] [--mic-cam 1=1,2=2,3=2]

--mic-cam: which camera shows each mic's speaker (default mic N = camera N). Three speakers on two cameras
(אלון + אייל + דולב, 21.10.2026): 1=1,2=2,3=2 — both guests share the two-shot, so either of them on camera 2 is right.

On screen: «מקור» at 2 fps, 64×36 grey, correlated with camera 1 and camera 2 at the same instant (offset 0 on the
RØDECaster) — the best match above 0.6 is the camera on air, otherwise "other" (a wide / a split / a transition).
Talking: the mic that leads by ≥ 6 dB over the half-second (mic clock = source + offsets.mic_src).
A MISS is a run ≥ 1.5 s where the speaker is clear and the other person's camera is on air. Short listener shots
(< 1.5 s) are reactions a director cuts on purpose and are not flagged.
Writes {samples, misses:[{from,to,on_air,speaker}]} and prints the misses.
"""
import argparse, json, subprocess
from pathlib import Path
import numpy as np

FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
W, H, FPS = 64, 36, 2


def frames(path, a, b):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(path), "-vf", f"fps={FPS},scale={W}:{H},format=rgb24",
                          "-f", "rawvideo", "-"], stdout=subprocess.PIPE, check=True).stdout
    rgb = np.frombuffer(raw, dtype=np.uint8).astype(np.float32).reshape(-1, H, W, 3)
    x = rgb.mean(3).reshape(len(rgb), -1)
    x -= x.mean(1, keepdims=True)
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-6), rgb


def seam(rgb):
    """a side-by-side split has a hard vertical edge at the centre: the jump between the two middle columns vs the
    typical column-to-column change of the same frame"""
    d = np.abs(np.diff(rgb, axis=2)).sum(3).mean(1)  # (frames, W-1)
    mid = d[:, W // 2 - 2:W // 2 + 1].max(1)
    return mid / (np.median(d, axis=1) + 1e-3)


def audio(path):
    raw = subprocess.run([FF, "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def runs_of(samples, min_miss, cam_of=None):
    """a MISS = consecutive samples where a full camera is on air and the OTHER person is clearly talking; a sample with
    the same camera and nobody clearly talking (a breath) keeps the run going; anything else (the right face, a split,
    a wide) ends it"""
    misses, run = [], None
    def close():
        if run and run["to"] - run["from"] >= min_miss and run["n"] >= 3:
            misses.append({k: run[k] for k in ("from", "to", "on_air", "speaker")})
    for x in samples:
        want = (cam_of or {}).get(x["spk"], x["spk"])
        wrong = x["air"] in (1, 2) and x["spk"] != 0 and want in (1, 2) and x["air"] != want
        if wrong and run and run["on_air"] == x["air"]:
            run["to"] = round(x["t"] + 1 / FPS, 2); run["n"] += 1
        elif wrong:
            close(); run = {"from": x["t"], "to": round(x["t"] + 1 / FPS, 2), "on_air": x["air"], "speaker": x["spk"], "n": 1}
        elif run and x["air"] == run["on_air"] and x["spk"] == 0:
            continue
        else:
            close(); run = None
    close()
    return misses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--from", dest="a", type=float, default=0.0); ap.add_argument("--to", dest="b", type=float)
    ap.add_argument("--out"); ap.add_argument("--min-miss", type=float, default=1.5)
    ap.add_argument("--mic-cam", default="")
    ap.add_argument("--rescan", action="store_true", help="re-read the samples of an earlier run (no video decode)")
    o = ap.parse_args()
    S = Path(o.session)
    out = Path(o.out) if o.out else S / "פרק" / "ניתוב.json"
    cam_of = {int(k): int(v) for k, v in (kv.split("=") for kv in o.mic_cam.split(",") if kv)}
    if o.rescan:
        samples = json.loads(out.read_text())["samples"]
        report(samples, runs_of(samples, o.min_miss, cam_of), out)
        return
    ing = json.loads((S / "ingest.json").read_text())
    b = o.b or float(ing["durations"]["source"])
    (src, srgb), (c1, _), (c2, _) = (frames(ing[k], o.a, b) for k in ("source", "cam1", "cam2"))
    n = min(len(src), len(c1), len(c2))
    sm = seam(srgb[:n])
    s1, s2 = (src[:n] * c1[:n]).sum(1), (src[:n] * c2[:n]).sum(1)
    off = float(ing["offsets"].get("mic_src", 0.0))
    ms = [audio(p) for p in ing["mics"]]
    def db(x, t):
        i0, i1 = int((t + off) * 16000), int((t + off + 1 / FPS) * 16000)
        return 10 * np.log10(np.mean(np.square(x[max(0, i0):max(i0 + 1, i1)])) + 1e-12)
    samples = []
    for i in range(n):
        t = o.a + i / FPS
        # 3 = split screen (both faces): never a miss
        air = 3 if sm[i] > 4.0 and max(s1[i], s2[i]) < 0.85 else 1 if s1[i] > max(0.6, s2[i]) else 2 if s2[i] > max(0.6, s1[i]) else 0
        ds = [db(m, t) for m in ms]
        k = int(np.argmax(ds)); rest = max(d for j, d in enumerate(ds) if j != k) if len(ds) > 1 else -120
        spk = k + 1 if ds[k] - rest >= 6 and ds[k] > -50 else 0
        samples.append({"t": round(t, 2), "air": air, "spk": spk, "c1": round(float(s1[i]), 2), "c2": round(float(s2[i]), 2), "seam": round(float(sm[i]), 1)})
    # misses: runs where a clear speaker is talking and the OTHER camera is on air (allowing silent/unclear samples inside)
    misses = runs_of(samples, o.min_miss, cam_of)
    report(samples, misses, out)


def report(samples, misses, out):
    on = {k: sum(1 for x in samples if x["air"] == k) for k in (0, 1, 2, 3)}
    out.write_text(json.dumps({"samples": samples, "misses": misses}, ensure_ascii=False))
    print(f"{len(samples)} samples · on air: cam1 {on[1]} · cam2 {on[2]} · split {on[3]} · other {on[0]} · misses {len(misses)}")
    for m in misses:
        print(f"  {m['from']:7.1f}–{m['to']:7.1f}  on air cam{m['on_air']} while mic{m['speaker']} talks ({m['to'] - m['from']:.1f}s)")


if __name__ == "__main__":
    main()
