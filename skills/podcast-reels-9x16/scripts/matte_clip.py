"""Cut the speaker out of a stretch of a camera file — locally, no click in CapCut — as an HEVC .mov
with alpha (VideoToolbox; the format CapCut already accepted for the tsomet-20 banner) that imports like
any clip. `--prores` writes a ProRes 4444 master instead. This is the top layer of the "behind the figure"
sandwich (bottom: the original shot · middle: text / logo / article · top: this cut-out).

    python matte_clip.py "<source video>" <start_s> <duration_s> "<out.mov>" [--fps 30] [--model u2net_human_seg] [--scale 1.0]

Measured on the M4 Pro (CPU onnxruntime, 1920×1080): u2net_human_seg ≈ 1.1 s/frame (person only — the
chair and the mic arm vanish, a ghost of the arm stays), isnet-general-use ≈ 2.0 s/frame (keeps the chair
and the mic as foreground, which is what "behind the figure" wants in the studio shots — the default). So 4 s at 30 fps ≈ 2–4 min; process at 30 fps even for a 60 fps project (an overlay of
a still-sitting speaker does not need 60). Hair and the mic arm are the weak spots — look at the
first frame before running the whole range (`--preview` writes only frame 0 on magenta).

A Multi-camera clip shows its active camera through a NESTED segment with its own `clip.scale` /
`clip.transform` (0919: `דף תודה 1.mp4` at scale 1.0607, x +0.0607). The cut-out must be taken from the
same pixels, so bake that reframe with `--vf` before the matte, and matte the WHOLE outer shot so the
top copy can carry the identical keyframes as the bottom one (a partial span re-eases the curve and
drifts — GREEN test, 22.09).
"""
import argparse, io, os, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import paths
from PIL import Image

FF = str(paths.FFMPEG)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("start", type=float); ap.add_argument("dur", type=float); ap.add_argument("out")
    ap.add_argument("--fps", type=int, default=30); ap.add_argument("--model", default="isnet-general-use"); ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--preview", action="store_true"); ap.add_argument("--prores", action="store_true")
    ap.add_argument("--vf", default="", help="ffmpeg filter applied BEFORE the matte, e.g. the nested multicam reframe: \"scale=iw*1.0607:-2,crop=1920:1080:(iw-1920)/2+0.0607*960:(ih-1080)/2\"")
    a = ap.parse_args()
    from rembg import remove, new_session
    sess = new_session(a.model)
    probe = subprocess.run([FF, "-i", a.src], capture_output=True, text=True).stderr
    import re; m = re.search(r"(\d{3,5})x(\d{3,5})", probe); W, H = int(m.group(1)), int(m.group(2))
    if a.scale != 1.0: W, H = int(W * a.scale) // 2 * 2, int(H * a.scale) // 2 * 2
    dec = subprocess.Popen([FF, "-v", "error", "-ss", f"{a.start:.3f}", "-t", f"{a.dur:.3f}", "-i", a.src, "-vf", (a.vf + "," if a.vf else "") + f"fps={a.fps},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    if a.preview:
        raw = dec.stdout.read(W * H * 3); dec.kill()
        im = Image.frombytes("RGB", (W, H), raw); cut = remove(im, session=sess)
        Image.alpha_composite(Image.new("RGBA", (W, H), (255, 0, 255, 255)), cut).convert("RGB").save(a.out); print("preview →", a.out); return
    # HEVC-with-alpha through VideoToolbox: the format the tsomet-20 banner proved inside CapCut, and ~13× smaller
    # than ProRes 4444 (4 MB vs 53 MB for 2 s). --prores keeps the 4444 master instead.
    codec = ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"] if (a.prores or sys.platform != "darwin") else \
            ["-c:v", "hevc_videotoolbox", "-alpha_quality", "0.9", "-pix_fmt", "bgra", "-tag:v", "hvc1", "-b:v", "20M"]
    enc = subprocess.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(a.fps), "-i", "-", *codec, a.out], stdin=subprocess.PIPE)
    n, t0 = 0, time.time()
    while True:
        raw = dec.stdout.read(W * H * 3)
        if len(raw) < W * H * 3: break
        cut = remove(Image.frombytes("RGB", (W, H), raw), session=sess)
        enc.stdin.write(cut.tobytes()); n += 1
        if n % 30 == 0: print(f"  {n} frames, {(time.time() - t0) / n:.2f} s/frame", flush=True)
    enc.stdin.close(); enc.wait(); dec.wait()
    print(f"{a.out}: {n} frames @ {a.fps} fps, {W}x{H}, {time.time() - t0:.0f}s total")


if __name__ == "__main__":
    main()
