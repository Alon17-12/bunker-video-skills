import sys, json, subprocess, os, numpy as np
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import transcribe as T
FF=os.path.expanduser("~/ffmpeg-bin/ffmpeg")
live, out = sys.argv[1], sys.argv[2]
dur=float(subprocess.run([os.path.expanduser("~/ffmpeg-bin/ffprobe"),"-v","error","-show_entries","format=duration","-of","csv=p=0",live],capture_output=True,text=True).stdout)
res={}
for name, ss, t in (("start",0,90),("end",dur-170,170)):
    a=np.frombuffer(subprocess.run([FF,"-v","error","-ss",str(ss),"-t",str(t),"-i",live,"-ac","1","-ar","16000","-f","f32le","-"],capture_output=True).stdout,dtype=np.float32)
    w=T.transcribe(a)
    res[name]=[{"t":round(x["start_s"]+ss,2),"e":round(x["end_s"]+ss,2),"w":x["text"]} for x in w]
json.dump(res,open(out,"w"),ensure_ascii=False)
for k,v in res.items():
    print("==",k)
    line=[];t0=None
    for x in v:
        if t0 is None: t0=x["t"]
        line.append(x["w"])
        if len(line)>=10: print(f'{t0:8.2f} '+" ".join(line)); line=[];t0=None
    if line: print(f'{t0:8.2f} '+" ".join(line))
