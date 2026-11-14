#!/usr/bin/env python3
"""Frame-exact check of what a CapCut project shows: every frame n (t = round(n/30 s)), the top visible full-frame layer (camera tracks 0/1, «מצלמה 1», «מסך משולב») → runs of ≤3 frames (flashes) and black frames. 25.10.2026: caught 7 flashes in «1021 (1)» that the segment-level checks passed.

    frame_runs.py "<project>" ["<project>" …]
"""
import json, sys, bisect
from pathlib import Path
sys.path.insert(0,str(Path.home() / "bunker-video-engine/app")); import capcut
for name in sys.argv[1:]:
  d=json.loads(capcut._draft_file(capcut.DRAFTS_DIR/name).read_text())
  mats={m["id"]:m for m in d["materials"]["videos"]}
  vt=[i for i,t in enumerate(d["tracks"]) if t["type"]=="video"]
  full=[i for i in vt if i<=1 or (d["tracks"][i].get("name") or "") in ("מסך משולב","מסך מפוצל") or "מצלמה 1" in (d["tracks"][i].get("name") or "") or "split" in (d["tracks"][i].get("name") or "").lower()]
  N=int(d["duration"]*30/1e6); idx={}
  for i in full:
    S=sorted(d["tracks"][i]["segments"],key=lambda s:s["target_timerange"]["start"]); idx[i]=(S,[s["target_timerange"]["start"] for s in S])
  def ident(n):
    T=int(round(n*1e6/30)); best="BLACK"
    for i in full:
      S,st=idx[i]; k=bisect.bisect_right(st,T)-1
      if k<0: continue
      s=S[k]
      if T< s["target_timerange"]["start"]+s["target_timerange"]["duration"] and s["clip"]["alpha"]>0.5:
        m=mats[s["material_id"]]
        off=round((s["source_timerange"]["start"]-s["target_timerange"]["start"])*30/1e6) if m.get("type")!="photo" else 0
        best=(Path(m.get("path","")).name, off)
    return best
  ids=[ident(n) for n in range(N)]
  runs=[];cur=[ids[0],0,1]
  for n in range(1,N):
    if ids[n]==cur[0]: cur[2]+=1
    else: runs.append(cur); cur=[ids[n],n,1]
  runs.append(cur)
  bad=[(r[1],round(r[1]/30,2),r[2],r[0]) for r in runs if r[2]<=3]
  print(name,"full tracks",full,"frames",N,"shots",len(runs),"black",sum(1 for x in ids if x=="BLACK"),"runs<=3f",bad[:20])
