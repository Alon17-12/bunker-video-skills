# HaKapitan snippets

Reusable pieces for the caption/transcript workflows. All Python runs with the
project venv and `sys.path.insert(0, "~/bunker-video-engine/app")`.

## Resolve a draft by name or unique substring

```python
import capcut
names = [d["name"] for d in capcut.list_drafts()]
draft = next((n for n in names if n == arg), None) or \
        next((n for n in names if arg in n), None)
```

## Inspect a draft before acting (never act blind)

```python
info = capcut.load_draft(draft)
print("duration:", round(info["duration"]/1e6/60, 1), "min")
for i, t in enumerate(info["tracks"]):
    print(i, t["type"], len(t.get("segments", [])), "flag", t.get("flag"))
caps = [c for c in capcut.extract_captions(draft) if c["duration_us"] < 25_000_000]
print("captions:", len(caps),
      "| locked:", capcut.draft_locked(draft),
      "| CapCut running:", capcut.capcut_running())
```
Text segments with `duration > 25_000_000` (25s) are headlines/hooks, not
captions — exclude them from coverage and never overwrite them.

## Window the audio plan to a time range

```python
def window_plan(plan, start_us, end_us):
    out = []
    for s in plan:
        tgt_end = s["target_start_us"] + s["target_duration_us"]
        if tgt_end <= start_us or s["target_start_us"] >= end_us:
            continue
        s = dict(s)
        if s["target_start_us"] < start_us:            # clip head into window
            cut = start_us - s["target_start_us"]
            s["target_start_us"] = start_us
            s["target_duration_us"] -= cut
            s["source_start_us"] += int(cut * s["speed"])
            s["source_duration_us"] -= int(cut * s["speed"])
        if tgt_end > end_us:                            # clip tail
            over = tgt_end - end_us
            s["target_duration_us"] -= over
            s["source_duration_us"] = int(s["target_duration_us"] * s["speed"])
        out.append(s)
    return out
```

## Atomic SRT writer (utf-8-sig BOM for Hebrew)

```python
def srt_time(us):
    ms = max(us, 0)//1000
    return f"{ms//3600000:02d}:{ms%3600000//60000:02d}:{ms%60000//1000:02d},{ms%1000:03d}"

def write_srt(caps, out_path):
    caps = sorted(caps, key=lambda c: c["start_us"])
    blocks = [f"{i+1}\n{srt_time(c['start_us'])} --> "
              f"{srt_time(c['start_us']+c['duration_us'])}\n{c['text']}"
              for i, c in enumerate(caps)]
    tmp = out_path.with_suffix(".srt.tmp")
    tmp.write_text("\n\n".join(blocks) + "\n", encoding="utf-8-sig")
    tmp.replace(out_path)   # atomic
```

## Verify a produced SRT

```python
import srt  # app/srt.py
cues = srt.parse_srt(path)
print("cues:", len(cues), "coverage 0 →", round(cues[-1]["end_us"]/1e6/60,1), "min")
print("ordered:", all(a["start_us"] <= b["start_us"] for a,b in zip(cues, cues[1:])))
print("overlaps:", sum(1 for a,b in zip(cues, cues[1:]) if b["start_us"] < a["end_us"]-1000))
print("BOM:", path.read_bytes()[:3] == b"\xef\xbb\xbf")
print("opening:", cues[0]["text"])   # must match the EDITED cut's opening
```
If the opening line matches a *raw recording* transcript instead of the edited
project, the times are on the wrong timeline — re-transcribe the project itself.

## Preserve existing captions when adding a new track

```python
before = json.dumps(info["tracks"][cap_track_i], sort_keys=True)
style = capcut.extract_style(draft, cap_track_i)          # donor from existing look
capcut.inject_captions(draft, new_caps, style, replace_existing=False)
after = capcut.load_draft(draft)
assert json.dumps(after["tracks"][cap_track_i], sort_keys=True) == before, \
    "existing caption track changed!"
```

## Clean progress monitor (write a tiny .py, run via Monitor)

Avoid nested shell-quoting: put the loop in a Python file and have the Monitor
tool run `python3 mon.py`. It reads a progress JSON, prints only on change,
exits on DONE or when the worker process disappears. See the pattern in
`full_transcript_srt.py`'s `prog()` writes — pair it with a reader that emits
one line per window and stops itself.

## GOTCHA: track indices are NOT stable — identify tracks by content

`capcut.load_draft` returns tracks in a normalized/render order, and adding a
track or segment (inject_captions, add_audio, logo surgery) reshuffles the
positions. A hardcoded `tracks[11]` that meant "my captions" one step ago can
mean "the logo track" the next — a real bug once moved 10 logos to the caption
height. Never address a track by numeric index across load/write cycles. Pick
it by a content signature and recompute every run:

```python
main_track = next(t for t in tracks if t["type"]=="video" and t.get("flag")==0)   # camera A
cap_track  = max((t for t in tracks if t["type"]=="text"), key=lambda t: len(t["segments"]))
logo_segs  = [s for t in tracks for s in t["segments"] if s["material_id"][:8].upper()==LOGO_ID]
```

After writing, re-verify by the same signature, not by index.

## Caption vertical position

CapCut's on-screen Y equals `transform.y × canvas_height`. For a 1920-tall
canvas, a caption the user calls "−450" is `transform.y = -450/1920 = -0.2344`;
"−700" is `-0.3646`. Set `segment.clip.transform.y`, not the material.

## Keyframe easing

`_kf` (cuts.py) writes linear (`curveType: "Line"`). For an eased zoom, mirror
CapCut's own reframe keyframes: `curveType: "FreeCurveInOut"` with
`left_control`/`right_control` bezier handles whose `x` is a time offset in µs
(e.g. ~60% of the interval). A fast punch-in = two scale keyframes ~1s apart,
base→base×1.05, both `FreeCurveInOut`. Zoom lives in `KFTypeScaleX`+`ScaleY`;
reframe pan uses `KFTypePositionX/Y`+`KFTypeScaleX` — a segment carrying
`KFTypeScaleY` (no Position) is a zoom you added, safe to remove/replace.

## Native karaoke (word highlight)

CapCut renders karaoke from the caption material's `words`
(`{start_time:[], end_time:[], text:[]}`, ms) plus `ktv_color` in `#RRGGBBAA`.
הקפטן-injected captions already carry `words`, so enabling karaoke is just
setting `ktv_color` (leave `is_words_linear=False`, matching working drafts).

## Detached long run (survives session teardown)

```bash
cd ~/bunker-video-engine
nohup .venv/bin/python full_transcript_srt.py "DRAFT NAME" \
    > ~/Desktop/.transcribe.log 2>&1 & disown
```
Then watch `~/Desktop/.<out>.progress.json`. The SRT on the Desktop is complete
up to the last checkpoint at all times.
