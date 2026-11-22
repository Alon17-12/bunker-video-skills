"""Render a Bunker «רז»: cams 1+2 routed by the mics, Bunker LUT, 0.5 s fade in/out, dialogue from the mics.
  render.py <route.json> <cam1> <cam2> <dialogue.wav> <in_live> <out_live> <out.mp4> [--test START DUR]
in/out are on the Live-Mix clock (the dialogue.wav clock); the cameras are read at live + cam_lag.
"""
import json, os, platform, subprocess, sys

FF = os.path.expanduser("~/ffmpeg-bin/ffmpeg")
LUT = os.environ.get("BUNKER_LUT") or os.path.expanduser("~/Movies/CapCut/User Data/Resources/Lut/Bunker/Bunker.cube")
FADE = 0.5

route, cam1, cam2, dia, t_in, t_out, out = sys.argv[1:8]
t_in, t_out = float(t_in), float(t_out)
r = json.load(open(route))
cam_lag = sum(x[0] for x in r["clocks"]["cam1"]) / len(r["clocks"]["cam1"])  # cam_t = live_t + cam_lag
test = None
if "--test" in sys.argv:
    i = sys.argv.index("--test"); test = (float(sys.argv[i + 1]), float(sys.argv[i + 2]))

a_in, dur = t_in, t_out - t_in
if test:
    a_in, dur = t_in + test[0], test[1]
v_in = a_in + cam_lag
# cam-2 shots relative to the output clock (shots are on the cam clock); keep only those inside, merge with the window
terms = []
for c, s0, s1 in r["shots"]:
    if c != 2: continue
    a, b = s0 - v_in, s1 - v_in
    if b <= 0 or a >= dur: continue
    terms.append(f"between(t,{max(a,0)-0.001:.4f},{min(b,dur)-0.0335:.4f})")
enable = "+".join(terms) if terms else "0"
fades = ""
if not test or test[0] == 0:
    fades += f",fade=t=in:st=0:d={FADE}"
afade = f"afade=t=in:st=0:d={FADE}" if (not test or test[0] == 0) else "anull"
if not test or test[0] + test[1] >= t_out - t_in:
    fades += f",fade=t=out:st={dur - FADE:.3f}:d={FADE}"
    afade += f",afade=t=out:st={dur - FADE:.3f}:d={FADE}"
fc = (f"[0:v][1:v]overlay=x=0:y=0:enable='{enable}':eof_action=pass,"
      f"scale=in_range=tv:in_color_matrix=bt709,format=gbrp,lut3d=file='{LUT}':interp=tetrahedral,"
      f"scale=out_range=tv:out_color_matrix=bt709,format=yuv420p{fades}[v];[2:a]{afade}[a]")
cmd = [FF, "-v", "error", "-stats", "-y",
       "-ss", f"{v_in:.4f}", "-i", cam1, "-ss", f"{v_in:.4f}", "-i", cam2, "-ss", f"{a_in:.4f}", "-i", dia,
       "-t", f"{dur:.4f}", "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
       *(["-c:v", "h264_videotoolbox", "-profile:v", "high", "-b:v", "20M", "-maxrate", "30M"] if platform.system() == "Darwin"
         else ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]), "-r", "30",
       "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
       "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", out]
print(f"cam_lag {cam_lag:+.4f}  v_in {v_in:.3f}  dur {dur:.2f}  cam2 shots {len(terms)}", flush=True)
subprocess.run(cmd, check=True)
