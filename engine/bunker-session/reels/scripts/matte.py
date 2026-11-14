#!/usr/bin/env python3
"""Person cut-out of a session camera for a source window (rembg u2net_human_seg) → public/fg/<name>.mov, ProRes 4444 with
alpha, full 1920×1080 @30, t=0 = src. Cut from the session's own graded select, so it lies exactly over the reel's camera
(אלון+אייל+דולב 27.10.2026: «השכבה השניה נשברת - צריך לסנכרן» — the teaser's matte was 4.3 s under a 7.6 s window).

    python3 matte.py <session> <name> <cam> <src> <dur>        (capcut-caption-studio venv: rembg)
"""
import json, os, shutil, subprocess, sys, tempfile
from PIL import Image, ImageFilter
from rembg import new_session, remove
from rpaths import session_paths

S, RM, PUB, WORK = session_paths(sys.argv[:2])
name, cam, src, dur = sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
FF = os.path.expanduser("~/ffmpeg-bin/ffmpeg")
sel = json.loads((PUB / "selects.json").read_text())
w = next((x for x in sel if x["from"] - 0.001 <= src and src + dur <= x["to"] + 0.001), None)
if w is None:
    sys.exit(f"{src}–{src + dur} is not inside one graded window")
tmp = tempfile.mkdtemp(dir=WORK)
subprocess.run([FF, "-v", "error", "-ss", f"{w['at'] + src - w['from']:.3f}", "-i", str(PUB / f"cam{cam}s.mp4"), "-t", f"{dur + 0.1:.3f}",
                "-vf", "fps=30", f"{tmp}/f%04d.png"], check=True)
sess = new_session("u2net_human_seg")
fs = sorted(f for f in os.listdir(tmp) if f.startswith("f"))
for i, f in enumerate(fs):
    im = Image.open(f"{tmp}/{f}").convert("RGB")
    m = remove(im.resize((960, 540)), session=sess, only_mask=True).resize(im.size, Image.BILINEAR)
    m = m.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(3))   # pull the edge in a little, soften it
    im.putalpha(m); im.save(f"{tmp}/a{i:04d}.png")
    os.remove(f"{tmp}/{f}")
(PUB / "fg").mkdir(exist_ok=True)
subprocess.run([FF, "-v", "error", "-y", "-framerate", "30", "-i", f"{tmp}/a%04d.png", "-c:v", "prores_ks", "-profile:v", "4444",
                "-pix_fmt", "yuva444p10le", str(PUB / "fg" / f"{name}.mov")], check=True)
shutil.rmtree(tmp, ignore_errors=True)   # exFAT: the ._ sidecars vanish with their files
print("ok", name, len(fs), "frames · src0", src)
