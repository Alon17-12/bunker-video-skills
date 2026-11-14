# -*- coding: utf-8 -*-
"""The movement layer: one-way push-in + split screens on a 9:16 reels draft.

* ZOOM IN ONE DIRECTION. Every shot starts at its own scale and pushes in, and
  the size resets under the cut while the other camera is covering. In-then-out
  inside a single shot reads as a wobble.

  The *shape* of that push-in is read off three reels Alon approved (אורח O,
  פרויקט-דוגמה N, אורח G) and it is not a straight line: a fast punch of
  15–25%/s in the first ~0.5s after the cut, then a sustained ≈1.2–1.5%/s. And
  a shot shorter than --static does not move at all — a short reaction beat is
  already a movement, and pushing into one during silence is exactly what Alon
  rejected on אורח P אלון ("זום אין חד ומהיר, גם כשיש שתיקה").

* SPLIT SCREEN ON THE EXCHANGES. True simultaneous speech turns out to be five
  moments of 0.4-0.7s — far too short to hold a split. The moment that actually
  wants both faces is the EXCHANGE: where the cut would otherwise flip
  camera 1 → camera 2 → camera 1 inside a few seconds. Those spans become one
  continuous split instead of three cuts. Entry and exit are hard cuts, not
  slides — a cut is cleaner here and never shows a black half.

  Long one-camera holds may also be broken by a split, but only inside a
  **budget** (--split-share, ~11% of the reel, which is what Alon's own cut
  spends) and only where the conversation is actually busy. Dropping a split
  into the middle of a monologue puts a silent listener on screen for five
  seconds; that is worse than the long hold it was meant to fix, and it is how
  one build ended up 34% split screen.
"""
import sys, json, copy, os
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut
import argparse
ap=argparse.ArgumentParser(description="one-way push-in + split screens on a 9:16 reels draft")
ap.add_argument("project"); ap.add_argument("--write",action="store_true")
ap.add_argument("--from",dest="t_from",type=float,default=None,
                help="שניות בציר — להחיל תנועה ומסכים מפוצלים רק מכאן והלאה. "
                     "הכרחי כשמוסיפים רילס לפרויקט שאלון כבר ערך ביד.")
ap.add_argument("--to",dest="t_to",type=float,default=None)
ap.add_argument("--gap-max",type=float,default=3.00,help="a camera-2 island shorter than this is an exchange")
ap.add_argument("--span-max",type=float,default=8.60,help="longest exchange still worth holding as a split")
ap.add_argument("--hold-min",type=float,default=9.00,help="a one-camera hold this long may get a split in its middle")
ap.add_argument("--invent-split",action="store_true",
                help="לבנות מסך מפוצל גם כשאין בפרויקט הרכב מאושר להעתיק ממנו. "
                     "ברירת המחדל היא לא — ניחוש של סקייל ותפר נפסל בפריים הראשון.")
ap.add_argument("--split-share",type=float,default=0.18,
                help="חלק הזמן המרבי במסך מפוצל. נמדד ברילסים מאושרים: 11%% (אורח P אלון), "
                     "16.7%% (אורח O), 20.4%% (פרויקט-דוגמה N). 34%% היה הכישלון")
ap.add_argument("--static",type=float,default=2.5,help="שוט קצר מזה לא זז בכלל")
ap.add_argument("--intro",type=float,default=0.05,
    help="מיני זום-אאוט בפתיח: הפריים הראשון של כל ריל מתחיל גדול בשיעור הזה ומתכנס לגודל היעד (0 = בלי)")
ap.add_argument("--intro-s",type=float,default=1.0,help="משך זום-האאוט של הפתיח בשניות")
ap.add_argument("--entry",type=float,default=0.5,help="חלון האגרוף אחרי החיתוך")
ap.add_argument("--punch",type=float,default=0.0,
                help="חלק האמפליטודה שנצרך באגרוף הכניסה. 0 = ראמפ ליניארי (ברירת המחדל "
                     "השמרנית); 0.6–0.8 מחקה את הסגנון שנמדד בריל מאושר — אגרוף חד ואז דחיפה איטית")
args=ap.parse_args()
NAME=args.project
FRAME=16667                 # one frame at 60fps — a "cut" inside a keyframe track
ZOOM_PER_S=0.012            # sustained push-in per second of shot
ZOOM_MAX=0.10
SPLIT_ZOOM=0.03

def kf(t,v,curve="Line"):
    return {"id":capcut._new_id(),"curveType":curve,"time_offset":int(t),
            "left_control":{"x":0.0,"y":0.0},"right_control":{"x":0.0,"y":0.0},
            "values":[v],"string_value":"","graphID":""}
def put(seg,tracks):
    seg["common_keyframes"]=[{"id":capcut._new_id(),"material_id":"","property_type":p,
        "keyframe_list":[kf(*pt) for pt in sorted(pts)]} for p,pts in tracks.items()]
    seg["keyframe_refs"]=[]
def amp(L):
    # שוט קצר לא זז. זו לא קמצנות — האגרוף על ביט תגובה בן שנייה בזמן שתיקה
    # הוא בדיוק מה שאלון פסל.
    return 0.0 if L < args.static else min(ZOOM_MAX, ZOOM_PER_S*L)
def intro_ramp(t0,t1,s0_,A):
    """הפתיח (אלון, 0910): הפריים הראשון של הריל מתחיל ~5% גדול ומתכנס בחלקות לגודל
    היעד תוך ~1s (CurveInOut), ואז הדחיפה הרגילה. זה ההיפוך היחיד שמותר בתוך שוט —
    qa25 בדיקה 18 מוציאה את חלון הפתיח מהמדידה (--intro-s)."""
    e=int(min(args.intro_s*1e6,(t1-t0)*0.5))
    head=[(t0,s0_*(1+args.intro),"CurveInOut"),(t0+e,s0_,"CurveInOut")]
    body=ramp(t0+e,t1,s0_,amp((t1-t0-e)/1e6)) if t1-t0-e>0 else []
    return head+[pt for pt in body if pt[0]>t0+e]
def ramp(t0,t1,s0_,A):
    """נקודות הסקייל של שוט אחד: ליניארי, או אגרוף כניסה ואז דחיפה מתמשכת."""
    if A <= 0 or t1 <= t0: return [(t0,s0_),(t1,s0_)]
    if args.punch <= 0: return [(t0,s0_),(t1,s0_*(1+A))]
    e=min(args.entry*1e6,(t1-t0)*0.4)
    return [(t0,s0_),(t0+e,s0_*(1+A*args.punch)),(t1,s0_*(1+A))]

d=capcut.load_draft(NAME)
vm={m["id"]:m for m in d["materials"]["videos"]}
# פתיח = הקטע הראשון אחרי כרטיס (או תחילת הפרויקט) — שם נכנס זום-האאוט של הפתיח
card_ends={sg["target_timerange"]["start"]+sg["target_timerange"]["duration"]
           for tk in d["tracks"] if tk["type"]=="video" for sg in tk["segments"]
           if vm.get(sg["material_id"],{}).get("type")=="photo"}
# תפקיד הטראק לפי מה שיש בו, לא לפי מיקומו — tracks[0]/[1] נכון בפרויקט
# אחד והפוך באחר, וכאן הטעות נכתבת לקובץ.
_vt=[t for t in d["tracks"] if t["type"]=="video" and t["segments"]]
_photo=lambda tk: all(vm[s["material_id"]].get("type")=="photo" for s in tk["segments"])
_hidden=lambda tk: all(s["clip"].get("alpha",1)<0.5 for s in tk["segments"])
_foot=[tk for tk in _vt if not _photo(tk)]
BASE_TK=_foot[0]
TOP_TK=next((tk for tk in _foot[1:] if not _hidden(tk)),None)
if TOP_TK is None: raise SystemExit("לא נמצאה שכבת מצלמה שנייה — אין מה לנתב")
print("שכבות: תחתונה = %s | עליונה = %s" % tuple(
    os.path.basename(vm[tk["segments"][0]["material_id"]]["path"])[:34] for tk in (BASE_TK,TOP_TK)))
_LO=int((args.t_from or 0)*1e6)
_HI=int(args.t_to*1e6) if args.t_to is not None else 1<<62
_win=lambda s:_LO<=s["target_timerange"]["start"]<_HI
_keep_top=[s for s in TOP_TK["segments"] if not _win(s)]
_keep_bot=[s for s in BASE_TK["segments"] if not _win(s)]
bots=sorted((s for s in BASE_TK["segments"] if _win(s)),key=lambda s:s["target_timerange"]["start"])
top=sorted((s for s in TOP_TK["segments"] if _win(s)),key=lambda s:s["target_timerange"]["start"])
if args.t_from is not None or args.t_to is not None:
    print(f"חלון {_LO/1e6:.2f}–{min(_HI,1<<61)/1e6:.2f} · מחוץ לו נשארים "
          f"{len(_keep_bot)} תחתונים ו-{len(_keep_top)} עליונים ללא שינוי")
def vis(s): return s["clip"].get("alpha",1.0)>0.5
def was_split(s):
    # חצי מסך = מוסט מהמרכז וקטן מכיסוי מלא. חיפוש הערכים המדויקים ±0.5/±1.5
    # החמיץ כל פרויקט שנעץ את החצאים לתפר בסקייל אחר — והתוצאה גרועה: השוט
    # לא זוהה כפיצול, וכל הקיפריימים שלו נדרסו בדחיפה של מסך מלא.
    ck=next((c for c in s.get("common_keyframes",[]) if c["property_type"]=="KFTypePositionY"),None)
    ys=[k["values"][0] for k in ck["keyframe_list"]] if ck and ck["keyframe_list"] else [s["clip"]["transform"]["y"]]
    cs=next((c for c in s.get("common_keyframes",[]) if c["property_type"]=="KFTypeScaleX"),None)
    scs=[k["values"][0] for k in cs["keyframe_list"]] if cs and cs["keyframe_list"] else [s["clip"]["scale"]["x"]]
    return max(abs(v) for v in ys)>0.15 and min(scs)<2.4
splits={id(s) for s in top if vis(s) and was_split(s)}

# ⚠️ אין להמציא הרכב של מסך מפוצל. שתי משפחות חיות בעבודה של אלון והן לא
# נראות דומה — חצאים ממולאים עד התפר, מול 16:9 שלמים ב-scale 1.0 עם פסים
# שחורים. ב-0830 בניתי פיצול לפרויקט שאין בו אף פיצול מאושר, ואלון פסל אותו
# בפריים הראשון. אם אין בפרויקט הרכב להעתיק — לא מפצלים, ואומרים את זה.
# ⚠️ רק פיצולים *מחוץ* לחלון שהריצה הזאת מחליטה עליו נחשבים הרכב מאושר.
# פיצול שאני עצמי בניתי בריצה קודמת יושב בתוך החלון, ואם סופרים אותו הכלי
# מאשר את הניחוש של עצמו — בדיוק הלולאה שגרמה ל-QA לעבור 41/41 על מסגור פסול.
# ⚠️ `was_split` לבדו רופף מדי לשאלה «יש כאן הרכב להעתיק»: הוא סימן שוט
# רגיל ב-scale 3.1605 עם y +0.077 כחצי מסך. מסך מפוצל אמיתי הוא **זוג
# ממוראה** — שני חצאים באותו חלון זמן, על שתי שכבות, עם y בסימנים הפוכים.
def _mirrored(a, b):
    ya, yb = a["clip"]["transform"]["y"], b["clip"]["transform"]["y"]
    return (ya * yb < 0 and min(abs(ya), abs(yb)) > 0.3
            and abs(a["target_timerange"]["start"] - b["target_timerange"]["start"]) < 100_000)

_cand = [s for t in d["tracks"] if t["type"] == "video" for s in t["segments"]
         if was_split(s) and not _win(s)]
_existing = [a for a in _cand if any(b is not a and _mirrored(a, b) for b in _cand)]
if _existing:
    # אומרים *מאיפה* נלקח ההרכב — בלי זה השומר יכול לאשר ניחוש ישן משלי
    # ואי אפשר לדעת שזה מה שקרה.
    _e = sorted(_existing, key=lambda s: s["target_timerange"]["start"])[0]
    print("הרכב מסך מפוצל נקרא מ-%.2fs (scale %.4f, y %+.4f) — %d חצאים קיימים"
          % (_e["target_timerange"]["start"]/1e6, _e["clip"]["scale"]["x"],
             _e["clip"]["transform"]["y"], len(_existing)))
if not _existing and args.split_share > 0 and not getattr(args, "invent_split", False):
    print("⚠️ אין בפרויקט הזה אף מסך מפוצל להעתיק ממנו הרכב — מדלג על הפיצולים.\n"
          "   להראות ריל מאושר עם פיצול ולמדוד ממנו, או --invent-split כדי "
          "לבנות בכל זאת (סקייל ותפר יהיו ניחוש).")
    args.split_share = 0.0

# ---- find the exchanges and merge each span into one split segment ----
clip_of={}
for b in bots:
    a0=b["target_timerange"]["start"]; b0=a0+b["target_timerange"]["duration"]
    for s in top:
        if a0<=s["target_timerange"]["start"]<b0: clip_of[id(s)]=id(b)
new_spans=[]
for i in range(len(top)-2):
    a,g,c=top[i],top[i+1],top[i+2]
    if not(vis(a) and not vis(g) and vis(c)): continue
    if id(a) in splits or id(c) in splits: continue
    if len({clip_of.get(id(x)) for x in (a,g,c)})!=1: continue
    gap=g["target_timerange"]["duration"]/1e6
    span=(c["target_timerange"]["start"]+c["target_timerange"]["duration"]
          -a["target_timerange"]["start"])/1e6
    if gap<=args.gap_max and span<=args.span_max: new_spans.append((i,span))
merged=[]; skip=set()
for i,span in new_spans:
    if any(j in skip for j in (i,i+1,i+2)): continue
    a,g,c=top[i],top[i+1],top[i+2]
    a["target_timerange"]["duration"]=(c["target_timerange"]["start"]
        +c["target_timerange"]["duration"]-a["target_timerange"]["start"])
    a["source_timerange"]["duration"]=a["target_timerange"]["duration"]
    splits.add(id(a)); skip |= {i+1,i+2}
    merged.append((round(a["target_timerange"]["start"]/1e6,2),round(span,2)))
top=[s for j,s in enumerate(top) if j not in skip]

# a hold this long is a wall of one face; put both of them on screen in its middle
HOLD_MIN=args.hold_min; HOLD_SPLIT=3.80; SPLIT_GAP=12.0
def split_centres():
    return [ (s["target_timerange"]["start"]+s["target_timerange"]["duration"]/2)/1e6
             for s in top if id(s) in splits ]
holds=[]
for b in bots:
    t0=b["target_timerange"]["start"]; b1=t0+b["target_timerange"]["duration"]
    cov=sorted((s["target_timerange"]["start"],
                s["target_timerange"]["start"]+s["target_timerange"]["duration"])
               for s in top if t0<=s["target_timerange"]["start"]<b1 and vis(s))
    p=t0
    for a,e in cov:
        if a>p: holds.append((p,a))
        p=max(p,e)
    if p<b1: holds.append((p,b1))
# תקציב, לא כלל. "כל החזקה מעל 9 שניות מקבלת פיצול" הפך פעם ריל שלם ל-34%
# מסך מפוצל — כולם באמצע מונולוגים, עם המאזין השותק על חצי המסך. אלון עצמו
# מוציא כ-11%. החילופים (שהם באמת דו-שיח) נכנסים ראשונים ולוקחים מהתקציב.
FOOT=sum(b["target_timerange"]["duration"] for b in bots
         if not vm[b["material_id"]]["path"].endswith(".image"))/1e6
BUDGET=args.split_share*FOOT
used=sum(s["target_timerange"]["duration"] for s in top if id(s) in splits)/1e6
extra=[]; dropped=0
for a,b_ in sorted(holds,key=lambda h:-(h[1]-h[0])):
    if (b_-a)/1e6 < HOLD_MIN: break
    c=(a+b_)/2/1e6
    if any(abs(c-x)<SPLIT_GAP for x in split_centres()+[e[0] for e in extra]): continue
    if used+HOLD_SPLIT > BUDGET: dropped+=1; continue
    extra.append((c, c-HOLD_SPLIT/2, c+HOLD_SPLIT/2)); used+=HOLD_SPLIT
out=[]
for s in top:
    sa=s["target_timerange"]["start"]; sb=sa+s["target_timerange"]["duration"]
    inner=[(x,y) for _,x,y in extra if sa<=x*1e6 and y*1e6<=sb]
    if not inner or vis(s): out.append(s); continue
    x,y=inner[0]; x=int(x*1e6); y=int(y*1e6)
    for ca,cb,on in ((sa,x,False),(x,y,True),(y,sb,False)):
        if cb-ca<10_000: continue
        ns=copy.deepcopy(s); ns["id"]=capcut._new_id()
        mm=copy.deepcopy(vm[s["material_id"]]); mm["id"]=capcut._new_id()
        d["materials"]["videos"].append(mm); vm[mm["id"]]=mm; ns["material_id"]=mm["id"]
        idx=capcut._materials_index(d); refs=[]
        for r in s.get("extra_material_refs",[]):
            if r not in idx: continue
            ln,m0=idx[r]; cc=copy.deepcopy(m0); cc["id"]=capcut._new_id()
            d["materials"].setdefault(ln,[]).append(cc); refs.append(cc["id"])
        ns["extra_material_refs"]=refs
        ns["target_timerange"]={"start":int(ca),"duration":int(cb-ca)}
        ns["source_timerange"]={"start":int(s["source_timerange"]["start"]+(ca-sa)),
                                "duration":int(cb-ca)}
        ns["clip"]=copy.deepcopy(s["clip"]); ns["clip"]["alpha"]=1.0 if on else 0.0
        ns["common_keyframes"]=[]; ns["keyframe_refs"]=[]
        if on: splits.add(id(ns))
        out.append(ns)
top=sorted(out,key=lambda s:s["target_timerange"]["start"])
TOP_TK["segments"]=sorted(_keep_top+top,key=lambda s:s["target_timerange"]["start"])
BASE_TK["segments"]=sorted(_keep_bot+[s for s in BASE_TK["segments"] if _win(s)],
                           key=lambda s:s["target_timerange"]["start"])

# ---- rewrite every keyframe ----
nz=0
for b in bots:
    t0=b["target_timerange"]["start"]; dur=b["target_timerange"]["duration"]
    src0=b["source_timerange"]["start"]
    base=b["clip"]["scale"]["x"]; bx=b["clip"]["transform"]["x"]
    if (vm[b["material_id"]].get("material_name") or "")=="ccstudio-card.png" \
       or vm[b["material_id"]]["path"].endswith(".image"):
        L=dur/1e6
        put(b,{"KFTypeScaleX":[(src0,base),(src0+dur,base*1.05)],
               "KFTypeScaleY":[(src0,base),(src0+dur,base*1.05)],
               "KFTypePositionX":[(src0,bx),(src0+dur,bx)],
               "KFTypePositionY":[(src0,b["clip"]["transform"]["y"]),(src0+dur,b["clip"]["transform"]["y"])],
               "KFTypeRotation":[(src0,0.0),(src0+dur,0.0)]})
        continue
    cover=sorted((s["target_timerange"]["start"],
                  s["target_timerange"]["start"]+s["target_timerange"]["duration"],
                  id(s) in splits)
                 for s in top if t0<=s["target_timerange"]["start"]<t0+dur and vis(s))
    sc=[];px=[];py=[]
    def add(a,b_,scale0,scale1,x0,x1,y0,y1):
        sc.append((src0+(a-t0),scale0)); sc.append((src0+(b_-t0),scale1))
        px.append((src0+(a-t0),x0));     px.append((src0+(b_-t0),x1))
        py.append((src0+(a-t0),y0));     py.append((src0+(b_-t0),y1))
    def push(a,b_,x,y):
        """שוט מלא: הצורה נקבעת ב-ramp, המיקום קבוע לאורכו"""
        A=amp((b_-a)/1e6)
        for t,v in ramp(src0+(a-t0),src0+(b_-t0),base,A): sc.append((t,v))
        px.extend([(src0+(a-t0),x),(src0+(b_-t0),x)])
        py.extend([(src0+(a-t0),y),(src0+(b_-t0),y)])
    p=t0
    for a,b_,is_sp in cover:
        if a>p:                                     # camera 2 alone: push in
            end=a-FRAME if is_sp else a
            push(p,end,bx,0.0); nz+=1
        if is_sp:                                   # camera 2 into the top half
            A=amp(min((b_-a)/1e6,4.0))*0.5+SPLIT_ZOOM
            add(a,a+FRAME,base/2,base/2,bx/2,bx/2,0.5,0.5)
            add(a+FRAME,b_-FRAME,base/2,base/2*(1+A),bx/2,bx/2,0.5,0.5)
            add(b_-FRAME,b_,base/2*(1+A),base,bx/2,bx,0.5,0.0)
            nz+=1
        p=max(p,b_)
    if p<t0+dur:
        push(p,t0+dur,bx,0.0); nz+=1
    def dedup(pts):
        o={}
        for t,v in pts: o[int(round(t))]=v
        return sorted(o.items())
    put(b,{"KFTypeScaleX":dedup(sc),"KFTypeScaleY":dedup(sc),"KFTypePositionX":dedup(px),
           "KFTypePositionY":dedup(py),"KFTypeRotation":[(src0,0.0),(src0+dur,0.0)]})
for s in top:
    s0=s["source_timerange"]["start"]; L=s["source_timerange"]["duration"]
    base=s["clip"]["scale"]["x"]; bx=s["clip"]["transform"]["x"]
    if not vis(s): s["common_keyframes"]=[]; s["keyframe_refs"]=[]; continue
    if id(s) in splits:
        A=amp(min(L/1e6,4.0))*0.5+SPLIT_ZOOM
        pts={"KFTypeScaleX":[(s0,base/2),(s0+L,base/2*(1+A))],
             "KFTypePositionX":[(s0,bx/2),(s0+L,bx/2)],
             "KFTypePositionY":[(s0,-0.5),(s0+L,-0.5)]}
    else:
        A=amp(L/1e6)
        t_start=s["target_timerange"]["start"]
        first=args.intro>0 and (t_start==0 or t_start in card_ends)
        pts={"KFTypeScaleX":intro_ramp(s0,s0+L,base,A) if first else ramp(s0,s0+L,base,A),
             "KFTypePositionX":[(s0,bx),(s0+L,bx)],
             "KFTypePositionY":[(s0,0.0),(s0+L,0.0)]}
    pts["KFTypeScaleY"]=pts["KFTypeScaleX"]; pts["KFTypeRotation"]=[(s0,0.0),(s0+L,0.0)]
    put(s,pts); nz+=1
if args.write:
    pid=capcut._capcut_pid()
    if pid is not None and f"{capcut.DRAFTS_DIR/NAME}/" in capcut._capcut_open_files(pid):
        raise SystemExit(f"{NAME}: פתוח כרגע ב-CapCut")
    capcut._backup(capcut.DRAFTS_DIR/NAME)
    f=capcut._draft_file(capcut.DRAFTS_DIR/NAME); t=f.with_suffix(".tmp")
    t.write_text(json.dumps(d,ensure_ascii=False,separators=(",",":"))); json.loads(t.read_text()); t.replace(f)
allsp=sorted((s["target_timerange"]["start"]/1e6,s["target_timerange"]["duration"]/1e6)
             for s in top if id(s) in splits)
print(f"מסכים מפוצלים: {len(allsp)} | חילופי דיבור: {merged} | החזקות ארוכות: {[round(e[0],2) for e in extra]}")
_sp=sum(l for _,l in allsp)
print(f"חלק הזמן במסך מפוצל: {100*_sp/max(FOOT,1e-9):.1f}% מתוך תקציב {100*args.split_share:.0f}%"
      + (f" | {dropped} החזקות נשארו בלי פיצול מחוסר תקציב — זו החלטה, לא השמטה" if dropped else ""))
for a,l in allsp: print(f"   {a:7.2f}  ({l:4.2f}s)")
print(f"שוטים עם תנועה חד-כיוונית: {nz}")
print("(הרצה יבשה — הוסף --write כדי לכתוב)" if not args.write else "נכתב.")
