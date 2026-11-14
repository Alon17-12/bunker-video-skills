# The nine stages, in full

Run them in order. Each stage ends with a number you can check; if the number
looks wrong, stop — every later stage inherits the error.

## 0. Where the episode lives

```
/Volumes/2T #1/RODECASTER_Video/<date> - <names>/
├── … - רז.mov                 1080p60 HEVC — the file the client watches
├── … - מקור.mp4               combined programme feed
├── … - וידיאו/… וידאו 1.mp4   ISO angle 1  (≈24GB, 1080p30)
│                 … וידאו 2.mp4 ISO angle 2
└── … - אודיו/Live-Mix.wav     + one wav per mic — "אודיו 1", "אודיو 2"
```

Angle *n* is filmed by the person on mic *n*. Confirm it by eye on one frame
before trusting it — everything downstream (who is on screen, which captions go
yellow) hangs off that mapping.

## 1. Sync the client's file to the angles

The `רז` file is a separate recorder with a separate start; it is **not**
aligned. `creation_time` is written at finalise and lies. Duration differences
lie too (it can start late *and* stop early).

Cross-correlate a 50Hz energy envelope of `רז` against `Live-Mix`, then refine on
the raw waveform. Measure in **three windows an hour apart** — agreement proves
both the offset and the absence of clock drift.

```
angle_time = raz_time + offset            # 03.08.26: +11.436s
```

**There are three clocks in the folder, not two.** The per-mic wavs, the
`Live-Mix`, and the angles' embedded audio each carry their own latency, even
when all three files have the same duration to the millisecond and look like one
recording. On 24.06.26 the mics ran **147.8 ms ahead of the angles** and the
`Live-Mix` 19 ms behind them — a mic clip pulled at face value would sit 4.4
frames out of lip sync. Measure `t_angle − t_mic` directly, in several windows;
do not chain it through the mix, and do not assume 0. Then cut the mic ranges
with the offset baked in (`ss = angle_start − offset`) so the mic file becomes a
drop-in parallel of the video work copy and both share one `source_timerange`.

## 2. Convert the marks, then argue with them

Transcribe ±5s around every converted mark and compare with the words the client
quoted. This catches a wrong offset instantly and gives word-level times to snap
cuts onto.

**When the number and the quoted words disagree, the words win.** Marks scrubbed
by eye run 2–3s off, and they often point at where a sentence *starts* when the
client meant its end. Move the cut to the word boundary and say which ones you
moved.

## 3. Work copies

Editing off 24GB files scrubs horribly. Encode one work copy per range **per
camera**, with 2s handles, straight **into the draft folder** — a scratchpad is
wiped when the session ends and the project dies with it.

```bash
ffmpeg -ss A -to B -i src -c:v h264_videotoolbox -b:v 40M -g 30 -c:a aac -b:a 256k out.mp4
```

Handles matter: keep a record of each copy's absolute start
(`abs = range_start - handle`) — every later audio read needs it to find the
right minute of the mic files.

## 4. Build the draft

Per reel: a 5s title card, the hook, then the body, back to back on the main
video track (which cannot hold gaps). The second angle goes on track 1 as a
full-coverage layer, split at the cut points, unwanted pieces at `alpha = 0`.

**Both layers cover every reel range end to end — this is the delivery format**
(see the house rule). The main track carries camera A for the whole of every
range; the layer above carries camera B for the whole of every range, cut at the
routing boundaries, each piece at a constant `alpha` of 1 or 0. The edit is then
correctable in CapCut with the Opacity slider, both mics stay in the mix, and
the canvas is covered at every frame by construction. What must *not* appear is
the whole raw source as a parallel copy — only the ranges that made the reel.

Clone from a donor project of the right shape, but strip the donor's
`smart_crops` — CapCut's own auto-reframe state will fight your explicit
transforms. Generate a real cover thumbnail or the gallery shows the donor's.

## 5. Vertical reframe

`reframe.plan_reframe` / `apply_reframe` find the face per cut and pan so the
speaker sits centred, one static transform per shot (a median across sampled
frames; a static frame can never judder).

**Render the actual crop and look at it.** The geometry is easy to get subtly
wrong and impossible to catch in JSON.

## 6. Multicam from the mics

Whoever's mic is louder is the speaker. Build a 100Hz energy envelope per mic,
mark speech, and:

* camera 1 gets the screen wherever mic 1 owns the sound — **including 0.4s
  interjections** (see the house rules; a minimum-shot rule silently deletes all
  of them),
* plus reaction beats so no camera is held too long,
* every cut snapped into a silence where **both** mics are quiet.

Choose a shot's in-point and out-point **as a pair**. Picking them independently
produces legal entries with no legal exit, the stretch gives up, and the camera
then sits still for half a minute.

The routing is a list of `(start, end, camera)` and it becomes `alpha` on the
upper layer, never a segment that exists only where its camera is shown. Keep
the **raw** turn boundaries from before the minimum-shot pass — the split-screen
stage needs them, and by the time absorption has run they no longer exist.

A reel must not close on the listener: drop any beat that runs to the clip end
and outstays a normal reaction.

## 7. Captions

Transcribe the *edited* timeline (`capcut.audio_plan` → `transcribe.build_timeline_audio`),
so captions line up with the cut as it is now.

Run the big model twice with different settings and diff — the script is
`hakapitan-captions/references/caption_qa_tiebreak.py --cache <work key>`, and
the full three-layer procedure (diff · read for meaning and spelling ·
independent QA agent) is in that skill's "QA the words" section. Do it before
reporting, not after Alon plays it. On this episode the
two passes agreed on 96.6% of words; the disagreements that changed meaning went
to a third tie-breaker (bigger beam, wider window, `vad_filter=False`). Report
the corrections you made.

Chunk to reel style: ~3 words, punctuation stripped, gap-free. Then a
readability pass that folds flicker-short cards — **re-derive the timing after
every merge** and keep a `stuck` set for cards that cannot merge, or one
un-mergeable card aborts the whole pass and leaves overlaps behind.

### Chunking: width, not characters; terms, not words

Two constraints decide where a card ends, and a character count satisfies
neither.

**Width.** The card must render on one line. Measure it:

```python
from PIL import ImageFont
f = ImageFont.truetype(FONT_PATH, int(round(font_size * PX_PER_SIZE_UNIT)))
fits = f.getlength(text) <= line_max_width * CANVAS_W
```

Calibrate `PX_PER_SIZE_UNIT` once against a real rendered frame (measure a known
string on screen, divide by what PIL reports at 100px). `line_max_width` is on
the text material — 0.82 here.

If a card overflows, **split it into two cards** at a word boundary and re-derive
the timings. Do not shrink the font (the style is fixed and a smaller line looks
broken next to its neighbours) and above all do not let CapCut wrap: CapCut
breaks at whatever column runs out of room, including mid-word, and orphans a
single letter onto line two.

**Terms.** Build an atomic-token list before chunking so a multi-word term is
never split across cards:

```
מלווה משקיעים · עסקת נדל"ן · בית ספר · החזר השקעה · צפון קפריסין · שוק ההון
```

Extend it per episode from the transcript — every domain has its own, and the
list is cheap to grow and expensive to skip. Treat each term as one token for
both the word-count target and the width measurement, so a card that would break
it becomes two cards instead.

Colour per word by the mic ratio, with a dead zone: calibrate on words whose
speaker is certain (here mic1/mic2 ≈ 0.05–0.15 for one man and 3.5–8.3 for the
other — a factor of fifty), then treat >2 as one speaker, <0.5 as the other, and
let anything between inherit from its nearest confident neighbour. Without the
dead zone it splits a single breath into two colours.

Then set `useLetterColor: true`, or none of it renders. See `capcut-json.md`.

## 8. Movement

One-way push-in per shot, split screens on exchanges and long holds, no shot
under ~1s. `scripts/reel_motion.py` does all three. Re-derive the visible
stretches from the live draft each run rather than from a plan file.

## 9. Grade

Attach the brand LUT to the adjust track and zero the donor template's manual
grade. Prove it with an ffmpeg `lut3d` before/after on a real frame.

## Delivering

One project. If a fast working copy and a client-named copy both exist, merge
them: move the light work copies into the kept folder, repoint every segment
(subtracting each work copy's absolute start from `source_timerange` **and**
from every keyframe `time_offset`), then move the other folder out of
`com.lveditor.draft` entirely.

Report with numbers, not adjectives: shot count, longest hold, cuts landing in
silence, captions, colours, missing media, overlaps.
