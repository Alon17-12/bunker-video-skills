#!/bin/zsh
# waits (up to 3h) for the 4K export (+ its SRT) in the Desktop folder, then cuts both into the 8 sections,
# each in its own sub-folder: "<name>/<name>.mp4" + "<name>/<name>.srt". If no SRT shows up within 4 min of the
# video being complete, the full-coverage SRT built from the caption base is used instead (logged).
setopt null_glob
OUT="~/Desktop/WhiteBoard 27.09 — פרומו וובינר (4K)"; SP="$(dirname "$0")"; FF=~/ffmpeg-bin/ffmpeg
for i in $(seq 1 1080); do
  SRC=$(ls -t "$OUT"/*.mp4 2>/dev/null | head -1)
  if [ -n "$SRC" ]; then
    s1=$(stat -f %z "$SRC"); sleep 20; s2=$(stat -f %z "$SRC")
    if [ "$s1" = "$s2" ] && [ "$s2" -gt 200000000 ]; then
      echo "$(date +%T) source: $SRC ($s2 bytes)"; ~/ffmpeg-bin/ffprobe -v error -select_streams v -show_entries stream=width,height,r_frame_rate -of csv=p=0 "$SRC"
      SRT=""; for j in $(seq 1 24); do SRT=$(ls -t "$OUT"/*.srt 2>/dev/null | head -1); [ -n "$SRT" ] && break; sleep 10; done
      if [ -z "$SRT" ]; then echo "$(date +%T) no SRT exported — using fallback from caption base"; SRT="$SP/0910_fallback.srt"; else sleep 5; echo "$(date +%T) srt: $SRT"; fi
      /usr/bin/python3 - "$SRC" "$OUT" "$SP/0910_sections.json" "$FF" <<'PY'
import json,subprocess,sys,os
src,out,plan,ff=sys.argv[1:5]
for p in json.load(open(plan)):
    os.makedirs(f"{out}/{p['name']}",exist_ok=True); dst=f"{out}/{p['name']}/{p['name']}.mp4"
    cmd=[ff,"-y","-loglevel","error","-ss",f"{p['start']:.3f}","-to",f"{p['end']:.3f}","-i",src,"-c:v","libx264","-preset","slow","-crf","15","-pix_fmt","yuv420p","-c:a","aac","-b:a","256k","-movflags","+faststart",dst]
    subprocess.run(cmd,check=True); print("cut",dst,flush=True)
PY
      /usr/bin/python3 "$SP/0910_split_srt.py" "$SRT" "$SP/0910_sections.json" "$OUT"
      echo DONE; exit 0
    fi
  fi
  sleep 10
done
echo TIMEOUT; exit 1
