#!/usr/bin/env python3
"""decode a video to 64x36 gray uint8 frames at 30 fps → .npy (for frame-exact routing work)"""
import subprocess, sys, numpy as np
from pathlib import Path
src, out = sys.argv[1], sys.argv[2]
raw = subprocess.run([str(Path.home() / "ffmpeg-bin/ffmpeg"), "-v", "error", "-threads", "4", "-i", src, "-an", "-vf", "fps=30,scale=64:36:flags=area,format=gray",
                      "-f", "rawvideo", "-"], stdout=subprocess.PIPE, check=True).stdout
np.save(out, np.frombuffer(raw, np.uint8).reshape(-1, 64 * 36))
print(out, len(raw) // 2304)
