# The scripts — what each one measures and how to run it

All of them are read-only without `--write` and refuse while CapCut holds the draft.

## Getting the numbers

`scripts/mic_windows.py` prints, for a finished draft, everything the rules
above depend on — read it before deciding anything:

```bash
cd ~/bunker-video-engine
.venv/bin/python ~/.claude/skills/podcast-reels-9x16/scripts/mic_windows.py "<project>" \
    --audio "/Volumes/.../<episode> - אודיו" --report host,crosstalk,silence,shots
```

It reports: every stretch where mic 1 owns the sound, every stretch where
neither does, every silence ≥0.7s, and every shot with its length — each one
tagged with whether the right camera is on screen.

`scripts/face_scan.py` answers "where can the captions go?" **and "is the face
framed right?"** — it samples the timeline, finds every face, maps it onto the
finished canvas through that shot's scale and pan, and prints the caption band,
the `transform.y` that follows, the head width, and the horizontal distribution
per layer with the `transform.x` correction it would take to recentre. It reads
which track is which camera from the work-copy names instead of assuming
`tracks[0]`/`tracks[1]`, and tags rows `bottom`/`top` rather than `cam1`/`cam2`
— the old labels meant the layer, not the camera, and came out backwards on
every project where the upper layer is camera 2:

```bash
.venv/bin/python ~/.claude/skills/podcast-reels-9x16/scripts/face_scan.py "<project>" --every 1
```

`scripts/qa25.py` is the sign-off gate — thirty checks over the finished draft,
each printing the number it measured rather than a verdict. Run it last, and run
it **after CapCut has saved the project at least once**:

```bash
.venv/bin/python ~/.claude/skills/podcast-reels-9x16/scripts/qa25.py "<project>" \
    --faces faces.json --audio-cuts --zoom-cap 3.55 --pin eyes
```

The numbers each check prints are the report; the pass/fail is secondary. Four
of them carry the recent lessons:

* **28 — both cameras run end to end and the routing is opacity.** It prints the
  upper layer's coverage, how much of the time it is visible, any hole punched
  in the bottom layer, any alpha that is neither 0 nor 1, and the windows that
  are uncovered. A project routed the old way (segments only where shown, plus a
  separate sound layer) is reported as such and skipped rather than painted red.
  Measured: 98.9% on אורח G, 93.9% on פרויקט-דוגמה N, **7.3%** on my אורח P build.
* **29 — the face's horizontal centre**, from `face_scan.py`'s new `face_x`. The
  axis that went unmeasured while the guest sat at 76–82% of canvas width.
* **19b — the sustained zoom rate**, entry and exit windows excluded
  (`--zoom-rate`, `--zoom-entry`). Zero excursions on all three approved reels.
* **18 — "frozen"** now starts above `--static` (2.5s), because short shots are
  *supposed* to be still.

It reads the project's own frame rate, infers each track's role from what is in
it, and infers who is on top of a split from the material — because every one of
those was hard-coded to the אורח G build and every one of them turned a
clean project into a wall of red. `--zoom-cap` is per episode (3.55 was measured
there, it is not a constant) and `--pin eyes` is the default; pass `--pin top`
only for a project graded before the eye anchor.

Three checks used to encode the older build and now measure the rule instead of
the layout that happened to implement it:

* **14 — the caption colour follows the microphone**, not the camera on screen.
  Holding on the listener while the host drops a word is a decision, so
  "yellow while camera 2 is on screen" is a *number to read* (91% on אורח O, 59%
  on פרויקט-דוגמה N — both correct), never a failure. With `--audio-cuts` it
  decodes the two camera files and fails only on a caption whose colour
  contradicts the louder mic by more than 3dB. Measure over the **words**, not
  the card: `materials.texts[].words.start_time` is per word in milliseconds,
  a negative first offset is normal (the card was pulled back to the clip
  start), and clamping it to zero is what keeps the probe out of the previous
  clip. Both projects come back with zero contradictions; measuring the display
  window instead invents three.
* **17 — camera 2's audible coverage equals camera 1's**, window for window.
  That is the invariant that catches the failure that once deleted 102 seconds
  of the guest. Where there is no separate sound layer it falls back to the old
  end-to-end coverage test.
* **20 — the longest run on one camera with no split inside it.** A long shot
  is not the problem; nine seconds on one face without the split that is
  supposed to break it is.

All three need to know which camera sits in which layer, which the script reads
from the work-copy filenames (`-cam1`, `… 1 - …`, `… -2.mp4`). When it cannot
tell, it says so and skips — an old project whose base track holds the client's
convenience file reports "not checked", not 0%.

Two rules the harness itself taught, both of which produced confident nonsense
before they were fixed:

* **Take shot boundaries from the segments, never from sampling.** A sampled
  boundary lands a frame or two late, excludes the very keyframe that defines
  the shot's push-in, and reports 29 shots as "frozen" that all move.
* **A cut is two keyframes one frame apart.** Sample across it and you measure
  the reset to the next shot — which reads as a 116% zoom and a direction
  reversal in a shot that only ever pushes in.

When a check fails, fix the draft, then **re-measure the world it depends on**.
A face scan taken before a scale change describes the old geometry, and a fix
pass fed stale measurements will happily apply the same correction twice.

`scripts/reel_motion.py` applies stage 8 to an existing draft: one-way push-in
on every shot, exchange and long-hold split screens, sliver removal.

```bash
.venv/bin/python ~/.claude/skills/podcast-reels-9x16/scripts/reel_motion.py "<project>"        # dry run
.venv/bin/python ~/.claude/skills/podcast-reels-9x16/scripts/reel_motion.py "<project>" --write
```

`scripts/prep_from_srt.py` builds an **edit-prep** project straight from the
client's marking SRTs — the ask is often *"הכן לעריכה"*, not "finish it":

```bash
.venv/bin/python ~/.claude/skills/podcast-reels-9x16/scripts/prep_from_srt.py \
    --donor "<episode project>" --name "<new draft>" \
    --cam1 <visible angle> --cam2 <hidden angle> --offset 11.8356 \
    --block "רגעי שיא=highlights.srt" --reels reels.srt --hooks hooks.srt \
    --extra "סיינטולוגיה=2774:3598" --card 2            # dry run; add --write
```

Every marked range lands on the timeline in order, blocks separated by a white
card, both angles over identical windows (upper one `alpha 0, volume 0`) so the
multicam is his to do. Four things it gets right that are easy to get wrong:

* **`--cam1` is the *visible* angle, and the useful default is the dominant
  speaker in the selected material, not "camera 1".** On אורח S the guest holds
  77% of the marked windows (1805 half-second windows against 538), so his angle
  is the base and the host's is the hidden one.
* **Overlapping highlight windows merge; touching ones do not.** 63 marks became
  49 segments.
* **`--extra` is in source seconds** — those ranges usually come from the
  transcript, which may be on a different clock from the client's marks.
* **The frame grid at 30fps is 33333.33µs, not an integer.** Snapping a start
  that is already the exact sum of snapped durations moves it by a microsecond,
  and four one-microsecond gaps on the main track are four ripple-closes the
  moment CapCut opens the project. Snap durations; accumulate starts.

`scripts/apply_framing.py` is for the round that comes after he re-cuts the
first reel by hand and says *"תדייק את הבאים אחריו"*. It reads the framing per
camera and per role (full / split-top / split-bottom) out of the range he
approved and re-anchors the rest to it, keeping each shot's own push-in:

```bash
.venv/bin/python ~/.claude/skills/podcast-reels-9x16/scripts/apply_framing.py "<project>" \
    --from 0:127.6 --to 145.8:            # dry run; add --write
```

It groups by *rendered* geometry, so it never carries a scale from one angle to
another with a different crop, and it asserts afterwards that every segment
outside the target range is byte-identical. On אורח P אלון it moved 90 segments:
camera 2 from 3.3257 to his 1.7953, the split's bottom half from a letterboxed
strip at 1.0 to his filled 1.881, and the top half's seam from 0.4363 to 0.5076.
Camera 1 it left alone, because his median there already matched.

One trap it hit on the way: reading the camera number off the filename with a
"last digit" regex matched the **4 in `.mp4`**, so both angles landed in one
group and the pass was about to average two different framings into both. Strip
the extension first, and print the groups before writing.

`scripts/reel_captions.py` is stage 7 end to end on a draft that is already cut:
it rebuilds the timeline audio per mic from the main track's `source_timerange`,
transcribes both channels, resolves ownership per word, chunks, and injects a
`כתוביות` track cloned from a donor project's style.

```bash
.venv/bin/python ~/.claude/skills/podcast-reels-9x16/scripts/reel_captions.py "<project>" \
    --mic1 ".../1_COMBO-1.wav" --mic2 ".../2_COMBO-2.wav" \
    --cap-y -0.426 --terms terms.txt --shadow-white          # dry run
```

`--cap-y` is required on purpose: measure it against the faces, never inherit it.
`--reuse` skips the audio rebuild and the transcription while you iterate on the
chunking, and `--replace` drops a caption track you injected earlier. It prints
`שאר הטראקים ללא שינוי` after writing — that is the byte-for-byte comparison, and
if it ever says False, restore from the backup it just made.

Three more things it now handles, each because it did not:

* **A title card is not footage.** Its `source_timerange` starts at 0, so pulling
  the mics at that offset lays the opening seconds of the *episode* under a white
  frame, and the transcriber writes captions for it. Cards are gaps, both in the
  audio it builds and in the clip list — `--main-track` may hold them.
* **`--cap-size`, because a 9:16 donor's size is not a 16:9 caption.** The style
  clone carries the donor's `size` verbatim, and 20 on a 1080-wide canvas is not
  20 on a 1920-wide one. His own landscape captions run at an effective **10**
  (`size 8 × clip scale 1.278` on «דולב + תום», same font), against **20** in
  every 9:16 reel. `--width-limit` scales the donor's line-width ceiling with it.
* **`--min-dur`, and the floor pass runs *last*.** A card's life is set by the
  *next* card, so lengthening one in isolation is undone by the overlap clamp
  that follows — which is exactly what the old code did: it wrote a 12-frame
  minimum and then clipped it straight back off, and 126 of 1598 cards shipped
  under half a second. A short card now borrows frames from a neighbour (the
  next one first — a caption may lead its words, never trail them), and only
  merges into a same-speaker neighbour when the word gap is under `--max-gap`.
  Merging first is what glues a card across a 1.3s silence, which is the same
  defect wearing the other hat.

`scripts/apply_multicam.py` is stage 6 on a project whose two layers already
cover the same ranges — the alpha routing, from the mics:

```bash
.venv/bin/python ~/.claude/skills/podcast-reels-9x16/scripts/apply_multicam.py "<project>" \
    --audio ".../… - אודיו" --mic-offset -0.1485        # dry run; add --write
```

The lower track is forced to `alpha 1` throughout and never flips; the upper one
is split at the cuts and each piece gets a constant 0 or 1. Every cut is nudged
to the quietest hundredth within ±0.35s, but the nudge is clamped by its
neighbours so it can never create a shot under `--min-shot`. A burst on the other
mic between `--min-interject` (0.40s) and the floor **grows into** the floor
instead of being thrown away — that is the interjection rule, enforced rather
than written down. Re-running collapses the existing pieces back to the bottom
track's seams first, so a second pass re-decides instead of splitting the splits;
it is idempotent, which is how you check it.

All of them are read-only without `--write` and refuse while CapCut holds the draft.

One thing you do *not* have to defend against: when Alon later trims a chunk out
of the middle, CapCut ripple-shifts every track, captions included. A track
injected before his trim was still frame-accurate after it — verified by
recomputing the captions against the new cut and comparing the tails.

## Adding reels to a project he has already edited

This is now the common case, not the exception: the project holds reels he cut
and coloured by hand, and the ask is three more at the end. Every stage script
used to run over the **whole** project, which means `apply_multicam.py` would
collapse his alpha routing back to the bottom track's seams and re-decide it,
and `reel_motion.py` would drop split screens into the middle of his reels. All
three now take `--from` / `--to`, they print how many of his segments they left
alone, and the assertion afterwards is byte-for-byte against a backup taken
before the run — *"סגמנטים מלפני 240.5 ששונו: 0"* is the line to read.

Two smaller traps from the same round:

* **`--range` snaps outward to whole footage segments.** Passing `240.5` on a
  timeline whose previous clip runs to `240.58` pulled that clip in and
  re-captioned the tail of a finished reel. Start the range *after* the last
  segment you must not touch, and read back the range the script prints.
* **Read the microphone number off the LAST digit of the filename.** The regex
  took the first, so `03.08.26 - … - אודיו 1.wav` resolved to channel **0** and
  the run died — the same shape as the `.mp4` "4" that once merged two camera
  angles into one framing group. Strip the extension, take the last digit.

## Devices (22.09.26) — see `references/devices.md`

* `scan_drafts_devices.py [--json out]` — every draft on the machine: matting (and whether text sits between the matted and the unmatted copy), Blur uses with amount and the text over them, external assets by kind, text effects on disk or not. Run it before inventing a composition; the answer is usually in his own work. It reads ~200 drafts and takes a minute or two — give it a real timeout, and a dump already exists at `~/Movies/reel-captions-work/drafts_devices.json` (22.09.26).
* `devices.py` — `blur_effect(mats, amount)` clones the cached Blur effect (the only video effect on disk) with an intensity; returns the material id for a segment's `extra_material_refs`.
* `matte_clip.py "<src>" <start_s> <dur_s> "<out.mov>" [--fps 30] [--model isnet-general-use|u2net_human_seg] [--preview] [--prores]` — local Remove background → HEVC-with-alpha .mov (VideoToolbox). ~1–2 s/frame at 1080p on the M4 Pro; `--preview` writes frame 0 on magenta to check hair and the mic arm first. Trap: the camera drive must be mounted (`/Volumes/2T #2`), and rembg's models download on first use (~180 MB each).
* `web_capture.py "<draft>" page|image <url> --slug <ascii> [--selector css] [--full] [--out dir]` — page/element screenshot at 2× or an image download (SVG rasterised) into the draft folder as `ccstudio-web-<slug>.png`, with provenance in `ccstudio-web-sources.json`. It prints the page title and domain so the caller can catch a lookalike domain before it reaches the timeline. `--list` shows what was captured.

## Client reels from marked ranges, end to end (22.09.26, לקוח H2 «0922»)

The chain that built four 9:16 reels into the draft Alon created, in order — each step read-only
until `--write`, each one leaving a number to check:

1. `sync_offsets.py "<ref>" "<other>" --at t1,t2,t3 --search S` — envelope + waveform cross-correlation
   per window; `other = ref + offset`. Proved the cameras sample-aligned (0.000), the RODECASTER
   channels 137–168 ms ahead (drifting 20 ms over 34 min), Live-Mix +9 ms. **It cannot find the offset
   of an EDITED program file**: the client's «רז» here was a CapCut export (HEVC 60 fps, temp folder
   beside it), correlation stayed ≤0.07 at every search width and printed confident nonsense (−115 s).
   Word anchors settled it: local Whisper on ±10 s windows of both files, same sentence → cam = raz + 48.4
   (drifting to 48.8 by the end). When corr < 0.3, do not use the number.
2. `reels_build.py plan.json --write` — one concatenated work copy per camera (all ranges, 1.5 s handles,
   the camera's own mic muxed with the offset baked, gain baked to ≈ −18 LUFS with a limiter — the raw
   channels sit at −33/−42 LUFS and no slider reaches that), the same concatenation of the mic wavs, then
   the draft rebuilt IN PLACE from the donor's templates: white card 5 s + title, cam2 base / cam1 over
   at alpha 0, adjust track with the LUT on footage only, a music bed per reel with a 0.6/2.0 s fade.
   `--skip-encode` re-measures and rewrites without re-encoding.
3. `frame_shots.py "<project>" --write` — head width 0.355 W → scale (3.28–3.42 here), eye anchor,
   face centre at 0.50 W. **Correction to the rules:** the "33–38 %" figure is the head WIDTH; the approved
   פרויקט-דוגמה N has the face CENTRE at 0.49 (host) / 0.62 (guest). `face_scan.py --face-x 0.45,0.65`.
4. `apply_multicam.py … --audio <draft folder> --mic-offset 0 --bottom 0 --top 1 --top-cam 1` — the
   mic wavs in the draft folder are on the copy clock, so offset 0.
5. `face_scan.py` → `--cap-y`; `reel_captions.py … --mic-offset 0 --shadow-white`; QA the words with
   `caption_qa_tiebreak.py --audio <key>-m2.npy --words <key>-words.json` (the guest's mic, not m1);
   fix the words cache; `--reuse --write`.
6. `reel_punches.py "<project>" --words <key>-words.json --write` — 8 % punches on sentence starts (pause
   ≥0.45 s or the transcriber's `.?!`), ≥4.5 s apart, 0.35 s, position re-solved so the face stays put;
   1 s zoom-out from +5 % on each reel's first frame. For a monologue reel whose client complained about
   camera jumping, this is the rhythm instead of reaction cuts.
7. `reel_stills.py "<project>" out.png t1 t2 …` — 9:16 composite stills (both layers, cards, titles,
   captions) — look before qa25. `qa25.py … --zoom-cap 3.7 --face-x 0.45,0.65`.

qa25 notes from this run: check 14 compares colour to the CAMERA files, so baked per-camera gains bias
it by their difference (9 dB here) — read the raw mic wavs for ownership; check 20 (hold > 9 s without
a split) fails by design when there is no split composition to copy; check 26 counts the cards as
uncovered by the LUT, which is what a white card wants.

### Round 2 on «0922» (22.09.26): a fifth reel, cutaways, b-roll, and the bed that played silence

Alon's four notes after opening the build — «איפה הריל החמישי», «בירולס… לפחות אחד בסרטון», «את המוזיקה לא
שומעים», «3 קטעים שרואים אותי מהנהן» — and the scripts they produced. He had also trimmed reel 1 by hand
(2.43 s off its tail, rippled): everything below is ADDITIVE, nothing rebuilds from the plan.

* **The silent beds.** The bed material was cloned from the donor's online-library track and kept its
  `effect_id`; CapCut re-resolved all four on open to `…/Cache/music/<hash>.mp3` — one cache file for four
  "different" beds, and nothing audible. A local file must be a local material: `type extract_music`,
  `category_name local`, `effect_id ""`, fresh `music_id` / `local_material_id`, the file copied into the
  draft folder (`ccstudio-music-*.mp3`). `reel_append.py` normalises every bed on the track; bed level
  raised 0.09 → 0.16 (≈ −16 dB under the voice) because the −21 dB he could not hear.
* `reel_append.py plan.json --reel N --encode` then `--write` — encodes the new range with the same
  encoder, gain-bakes it to −16 LUFS, concatenates it onto the END of the existing work copies and mic
  wavs (`-c copy`; earlier source times untouched), then clones card / title / base / over / adjust / bed
  from the last reel on the timeline. Followed by `frame_shots.py --from <t>`, `apply_multicam.py --from
  <t-0.01> --to <end+0.01>` (the range test is strict — a footage segment at 193.8667 is outside
  `--from 193.87`), `reel_captions.py --range a:b --add` (a second «כתוביות» track; merge it into the first
  afterwards) and `reel_punches.py --from <t>`. `--from` on frame_shots / reel_punches leaves the earlier
  reels' keyframes alone — without it both scripts recompute everything, and after a hand trim the old
  words cache is 2.4 s off.
* `reel_cutaways.py "<project>" --windows a:b,…` — reaction windows on the OVER layer (alpha 1, still,
  keyframes trimmed to each piece with an interpolated boundary key). Windows for 0922 came from a YuNet
  pass over the hidden camera at 10 fps: vertical face motion (a nod) per 2 s window, kept where
  mic1 − mic2 < −5 dB (listening, not talking), one per third of the reel, snapped to the speaker's
  nearest pause, clear of the b-roll and of the first 3 s / last 2.5 s; 1.8 s each (1.5 s in the 21 s reel).
* `reel_broll.py "<project>" --items items.json` — one `broll` track above the adjust layer and below
  every text track, muted, hard cuts, 1.08→1.0 settle on a clip / 1.0→1.06 push on a still; no SFX, no
  duck, no inset. Items are literal to the sentence (`why` records it). Clips: `kling3_0_turbo` 9:16 720p
  5 s = 7.5 credits (seedance_2_5 1080p is 35; 480p 4 s still 12) → upscaled to 1080×1920 h264, audio
  stripped. Real material: the gov.il «דירה בהנחה» page (`dira.moch.gov.il` was on a maintenance page —
  the title check caught it), framed as a rounded card on a blurred, darkened plate (PIL; the 16:9
  `framed_asset` idea in 9:16), card bottom at 0.50 H so the caption band stays clear.
* qa25 after the round: 4b flags ids that CapCut itself duplicated on Alon's save (one material entry per
  segment, same id) — not ours; 18 lists hidden (alpha 0) pieces as frozen; 19b sees the interpolated
  boundary key of a hidden piece as a 0.2 s "punch"; 20 and 26 as before.
* **Round 3 (his notes on round 2):** `copies_audio_gate.py "<draft>" --prefix <p> --write` (ownership-gated
  re-master of both copies' audio, one continuous AAC per camera — also the cure for a piece stitched by
  `-c copy`), `reel_ripple.py "<project>" --cuts a:b,…` (silence cuts across every track: footage split,
  adjust/bed/title trimmed, captions shifted, eased boundary keys), ease pass on `Line` keys, hook title
  and click SFX cloned from his own segments. While he holds the draft, park the writes on a `pgrep -x
  CapCut` watcher with a guard that the reel is unchanged (`r5/parked.sh` pattern).

### Bunker's own content reels, one talking head, 23.09.26 («רילס לבונקר» = `0923`)

Three raw clips he laid on a 16:9 timeline (reel 1 two angles, reels 2–3 one), audio inside the mp4s,
no separate wavs. The same chain, with what changed:

* `reels_build.py` — a shoot may point `mic1` at the camera file (the RODECASTER mix is in it) and have
  `cam2: null` (the hidden layer gets that reel's own picture with `volume=0` so the concatenated copy
  stays continuous; no over segment is made). Beds are now LOCAL materials (the 0922 lesson, finally in
  the builder) and LOOP in pieces when the `.full` master (68–76 s) is shorter than the reel.
* order: build → `frame_shots.py --cap 3.30` (ONE framing per reel — the script now groups by the
  footage between two cards, not by piece; the cap: 1080p source, face 9 % of the frame, ×3.55 would put
  the punches at ×1.21 of cover and check 8 fails) → `reel_ripple.py` (18 pauses ≥ 0.5 s from the source
  audio, −9.75 s) → `reel_captions.py --mono --mono-own 2 --all-white --cap-y -0.19` → `sentence_split_captions.py`
  (now picks the LARGEST text track; it used to take the first = the titles) → `reel_punches.py` with the
  words' `mic` forced to the base camera (a mono cache says mic 2, the base here is cam 1), `--pause 0.22`
  (the ripple leaves ≈ 0.25 s of every pause, so those are the sentence starts), `--first-after 1 --last-before 0.8 --gap 3.5`
  (pieces are 3–8 s) — and the intro zoom-out only on the first piece after a card (21 intros before the fix)
  → `reel_cutaways.py` with sentence-start windows to the side angle (6 × 2.5–4.5 s, 23 % of reel 1) →
  `reel_broll.py` from his own folder `~/VideoAssets/בירולס שלי` (113 files; contact sheet
  first, three frames per candidate, iPhone portrait clips need `scale=1080:1920:force_original_aspect_ratio=increase,crop`)
  → `reel_logo.py --scale 0.43 --y -0.40` (the mark is 70 % of the file width → 30 % of the canvas, the
  0910 pair with captions at −0.19) → register → stills (`reel_stills.py` now pastes a logo PNG with its
  alpha; it drew a white box before) → qa25 23/31: 14 (mono, n/a), 18 (jump-cut pieces under 8 s without a
  sentence start), 20/28 (one camera), 26 (cards).


## 0923 «רילס לבונקר» — the premium layer (23.09.26, Alon: «מה אפשר לשפר כדי להפוך אותם לפרימיום?» → «תתחיל»)

Measured first: 22.7 visual events/min and a 2.1 s median shot were already inside the reference band; what
was missing was the graphics + sound layer every reference shares. Order of impact, then what was written:

| # | Device | Script | Numbers on 0923 |
|---|---|---|---|
| 1 | keyword supers, top band (y +0.78), Bunker red `#d01020` (dominant colour of the logo PNGs), white for the rest, Grow 0.35 / Fade Out 0.25, size fit ≤ 860 px in [22, 40] | `reel_supers.py --plan supers.json` | 31: 3 hooks, 3 name cards (2 lines, size ≤ 24, y +0.80), 2 CTA «תשאירו פרטים» (spoken, so literal), 23 keywords |
| 2 | hook on the face in the first 3 s of every reel, over the intro zoom-out | same, `kind: hook` | «אל תפיקו פודקאסט» · «יודע מי אתה?» · «מה קרה קודם?» |
| 3 | sound: click (his 0922 shutter click, localised from the cache) on every b-roll, swoosh («swoosh quick 1» from his SFX folder) on every super, bed ×0.71 under b-roll with 0.3 s ramps | `reel_sound.py --click … --swoosh …` | 40 hits (10 + 30; one swoosh inside 0.25 s of a click skipped), 11 ducked windows |
| 3b | voice compressed in the cam1 copy: acompressor −18 dB / 2.5:1 / 6 ms / 120 ms, trim to −16 LUFS, limiter 0.891 | `copies_audio_compress.py --file ccstudio-bunker-cam1.mp4` | −15.2 / LRA 5.1 → **−16.0 / LRA 3.2**; backup in `~/Movies/reel-captions-work/0923-….pre-compress.m4a` |
| 4 | framed real-product inserts: his finished reels from `~/VideoAssets/exports` in a rounded card 523×930 at y 130 (bottom 1060 < caption band 1077) with a soft shadow on a blurred, darkened plate of the same reel, muted, through the b-roll track | ffmpeg (mask + shadow PNGs from PIL) → `reel_broll.py` items `ccstudio-broll-f*-*.mp4` | 4: pricing reel on «לצלם פודקאסט» (94.05), the 90 % reel on «תוכן אורגני» (136.92, replaced desk b-roll), client reel with the logo on «רילס» (178.53, replaced phone b-roll), guest in the Bunker tee on «שיוצר תוכן ומשפיע» (211.73) |
| 5 | holds > 7 s covered by supers | (plan) | longest visual hold now 6.6 s (was 9.1) |
| 7 | keyword in the accent inside the captions, only where no super is active | `reel_caption_highlights.py --phrases …` | 6 cards |
| 8 | name card «אלון גבאי / הבונקר · אולפן פודקאסטים» after each hook; CTA = the spoken «תשאירו פרטים» | `reel_supers.py` kinds `name` / `cta` | 3 + 2 |
| 9 | LUT over the cards (adjust segments extended back to the card start); over layer muted | `reel_polish.py --mute-over --lut-over-cards` | qa25 check 26 ✅; over layer 18/18 muted |
| — | the caption hole found on the way: 228.6–235.9 s had speech and no cards; «זה טוב» was «לא היה טוב» | `reel_caption_add.py --cards cards.json` | +9 cards, 1 retext → 309 |

**Skipped, and why.** Glare II on the first punch: a transition needs a cut at the punch and its `is_overlap`
semantics (does it eat time from both sides?) are unverified — a wrong guess shifts 309 captions. Left for a
CapCut-side test. Second angle on reels 2–3: no footage. Loudness of the export: needs his render.

**Verified by:** diff against the frozen base (`draft_info.0923-premium-base.json`: base track 24/24 byte-identical,
over layer differs only in `volume`, adjust only in ranges, captions 300/300 identical + 9 added + 7 materials
changed (retext + highlights), bed pieces only in `common_keyframes`); 0 overlaps on 10 tracks, 0 dangling refs,
0 Line keys in moving groups; stills at 16 times (`stills_v3.png`, `stills_v4.png`); qa25 21/31 — new fail 24 is
the red highlight by design, 8/9 are the pre-existing framing tolerances (base untouched), 14/18/20/28 as before.

**Traps met.** (1) `line_max_width` 0.82 = wrap at 886 px — a 905 px super becomes two lines; `--max-px` 860.
(2) RTL numbering «1. עוגנים» is a bidi gamble in CapCut; the count lives in «3 טיפים», the items are bare words.
(3) `register_media.py` lists every file in the folder — the compressor's `.pre-compress.m4a` backup showed up in
the Media panel; backups live in `~/Movies/reel-captions-work/`. (4) One RODECaster mix on both copies: the over
layer at volume 1 doubled the voice for all of reel 1 (+6 dB, comb on any sub-frame offset).


### 0923 round 2 (23.09.26) — Alon's seven notes on the premium layer
Kept: hooks (3), framed product reels, caption keyword colour, compressed voice, LUT over cards, muted over layer.
Removed: 28 keyword/name/CTA supers (→ `supers_hooks.json`). Changed: beds → trap_hype / gritty_hiphop / funk_groove
(`reel_music.py`, trap master made from raw at −16.3 LUFS); logo → real HEB_2 file as a local photo material
(`reel_logo.py` identity fix); b-roll 10 → 19, all ≤ 3 s, 7 new pieces from «בירולס שלי» + 2 emoji pops
(`reel_broll.py` overlay items, `--pop` in `reel_sound.py`); 18 caption fixes incl. a delete (`reel_caption_add.py`
`del`); click 0.35 after the mix peaked +1.4 dBFS on «חיילים משוחררים»; SFX spacing 0.6 s (the 0.29 s click+swoosh
pair at 224.5 was the only reel-3-specific audio event = the likely «שגיאה בסאונד»). New: `reel_audio_mix.py`,
`reel_music.py`. Higgsfield: 0.5 credits, no allowance → `higgsfield_comic_plan.json` in the work folder.
Parked chain pattern: `parked2.sh` (zsh: use `${r%%:*}` not `set -- $r` — zsh does not word-split).


### 0923 round 3 (23.09.26) — «תקן את הדברים גלובלית»
New: `reel_pauses.py` (pause → cuts), `reel_cut_polish.py` (punch hygiene, 5 rules), `reel_caption_punct_split.py`,
`reel_polish.py --align-angle-cuts`; `reel_music.py` spans from the card; `reel_broll.py` items take `x`/`y` pans and
`overlay`; `reel_sound.py` ducks only under full-frame inserts, `--pop` for photo items; `reel_caption_highlights.py`
with no phrases clears. Run order after silence cuts: ripple → broll (times remapped through the cuts) → music → sound →
cut_polish → punct split → register → mix QA → qa25 → stills. Numbers: 10 cuts (−2.9 s, 4:16.2), 22 b-roll/overlay
items (2 Higgsfield DOP clips, 3 numbered titles, a «3» badge, 2 arrows), 35 size changes, shortest hold 2.35 s (the
intro), 312 captions, mix peaks −0.8/−0.8/−2.0 dBFS, qa25 22/31 (8/9 framing tolerances, 14/18/20/28 single-camera).
Traps: ripple boundary keys sit ±1 µs outside the piece (tolerant range checks); a cut that matches a whole sliver
leaves a sub-frame piece (dropped); PIL without raqm draws Hebrew reversed (draw `word[::-1]`); a scale edit must
rescale the pan keys (rule 4 repairs pos/scale ratio).

## 0923 round 4 — his own footage as b-roll (23.09)

Alon exported five Photos albums (733 items, «בירולס לרילס 2026») and asked for the reels to use them. Three
scripts turn a raw folder into cut b-roll:

* `broll_catalog.py "<folder>" --out <workdir>` — probes every video/photo (duration, size, orientation,
  shot date), one frame at 30 % per clip, numbered contact sheets of 48. Re-runs only probe new files, so it
  can run while the export is still landing. **Look at every sheet** — the pick is by eye, literal to the
  sentence (0923: the 2026 studio footage sat at indices 318–393; everything before it was 2024 client shoots).
* `broll_preview.py <catalog_dir> --idx 372,353 --out pv.jpg` — three frames (10/50/90 %) per candidate to
  judge motion; when a pick still lands on a whip pan, tile the raw at 2 fps (`fps=2,tile=8x2`) and read the
  offset off the tiles (n1-notes: writing is 3.6–5.0 s; n2-studio: the logo holds 0–1.5 s, set from 2.5 s).
* `broll_cut.py "<project>" --catalog <dir> --plan plan.json --items items.json` — cuts
  `ccstudio-broll-<name>.mp4` (1080×1920 cover-crop, CRF 18, no audio, +0.4 s tail) into the draft folder and
  writes the items file for `reel_broll.py` with `off` baked in. **iPhone HLG/PQ (bt2020, arib-std-b67) is
  tone-mapped to bt709** via `zscale`+`tonemap=hable`; a plain scale renders grey and washed-out next to SDR
  footage. `"recut": true` on a plan entry re-encodes just that one.
* `register_media.py --prune --write` — drops registry rows whose file is gone (after replacing a b-roll set);
  without it the Media panel keeps 19 dead entries.

Merge: keep the overlay items (badge, numbered titles, arrows) and the Higgsfield clips from the previous
items file, add the new cuts, sort by `t`, then `reel_broll.py --write` → `reel_sound.py --write` →
`register_media.py --prune --write` → stills at every new time → mix QA. Result on 0923: 28 items (27 ≤ 3 s),
0 overlaps, his tracks byte-identical, mix peak −0.7 dBFS / 0 clipping.

Exporting from Photos: `osascript` `export {media item id …} to POSIX file … with using originals`, batches of
4 inside `with timeout of 1800 seconds` (the default 2-minute AppleEvent timeout kills a batch of 10 iCloud
items), skip by filename already on disk, stop under 5 GB free. Photos drops the connection now and then
(−609); the on-disk skip makes a restart free.

Round-4 honesty pass (same day): `reel_broll.py --under-adjust` puts the b-roll track BELOW the adjust layer so
his grade covers the phone footage too (track order became video, video, broll, adjust, …; check every
b-roll segment lies inside an adjust segment — 25/25); `reel_sound.py --duck 1.0` strips the bed's volume keys
and writes none; three semi-literal picks («איך העסק נראה», «מגיע אליך», «עדויות») dropped — literal or nothing.

## 0923 round 5 — his five notes on the r4 build (23.09 evening)

1. **Every PNG overlay rendered as a white square** — same trap as the logo: `reel_broll.py` cloned photo
   materials from the online white card, CapCut re-linked them on open. Fixed in `reel_broll.py` (local
   identity on every photo material); `qa_r5.py` asserts `source 0` / empty `material_id` on all photos.
2. **B-roll back ABOVE the adjust layer** — «ה-LUT מעוות אותם». `--under-adjust` stays available, off by default.
3. **`reel_music.py --start footage`** (now the default): the bed starts on the first footage frame after the
   card, not on the card. The card is silent again — his call this time.
4. **Silence pass 2**: `reel_pauses.py --min 0.35 --keep 0.10 --floor -30` → 21 cuts, 3.95 s; after the
   ripple `reel_broll_heal.py` re-joins b-roll pieces the ripple split (7), else each piece gets its own
   click; then `reel_cut_polish.py` (15 new size changes) and `reel_sound.py`.
5. **`reel_caption_width_split.py --max-px 740`**: 10 cards over the ≈770 px caption wrap split at a word
   boundary — that was the «ירידת שורה באמצע מילה». Quote «ב"אני אחשוב על זה"» merged into one card.
   Flash cards (< 0.3 s: «כי», «אם יש») merged into the next card with `reel_caption_add.py` — delete and
   add in SEPARATE runs, and take `t1` from the next card's exact start minus a frame: the add refuses any
   touching card after snapping.

## 0923 round 6 — typographic titles, one-line captions (23.09 late)

* «הכותרות והאייקונים ילדותיים»: the PIL badge / numbered-circle PNGs are gone. Chapter titles are now
  `reel_supers.py` kind `title` — `"01\nעוגנים"`: accent kicker at 0.6× over a white keyword (26–36), Grow in /
  Fade out, top band, one plan file with the hooks (`supers_r6.json`). The «3» icon is a super «3 טיפים» with
  the digit in accent. His own white arrow PNG stays (local identity).
* «אסור פיצול ל-2 שורות»: `reel_caption_width_split.py --max-px 640` (46 more splits, 364 cards). 640 is a
  conservative bound: the hooks at 855–863 px render on one line, so the true wrap is ≥ 770, but nothing was
  measured on a caption render. A quote that must stay whole is retexted by hand and sits under the bound
  («"אני אחשוב על זה"» 654 px, the ב prefix dropped) — re-running the splitter would cut it again.
* ⚠️ `reel_stills.py` paints a text card in ONE colour (its first style) — a super with an accent range looks
  all-red or all-white on the sheet. Verify per-range colours in the JSON (`styles[].fill` + `size`), not on
  the still.
* Items file after a ripple: rebuild from the draft (`qa_r5.py` dumps `broll_items_r5_fromdraft.json`) and
  carry `overlay`/`x`/`y` over from the old items by file name — the old times are stale.

## 0923 round 8 — «הפעם אני רוצה את זה מושלם» (24.09)

* **Lead-in silence**: measure the voice onset after each card (`reel_pauses` skips the first 0.3 s after a
  card, so it never saw them: 0.62 / 0.39 / 0.50 s). Ripple `card_end : onset − 0.12` and rebuild the bed with
  `reel_music.py --start footage --fade-in 0.15` (a 0.6 s fade on a 0.5 s lead-in is what he heard as silence).
* **Animated captions**: `reel_caption_anim.py --in Grow --dur 0.14` — one cached CapCut wrapper per card.
* **Motion titles**: `motion_title.py` renders ProRes 4444 alpha .mov (kicker · accent rule · Heebo-ExtraBold
  keyword with a soft wipe, in 0.55 / out 0.35). They go on a SECOND overlay track: `reel_broll.py --name titles`
  (sits right above `broll`); `reel_sound.py --broll broll,titles` gives them a swoosh (file name contains
  `title`/`counter`). `reel_stills.py` now keeps video alpha, so the sheet shows them over footage.
* **Higgsfield, the character route that works**: `mcp__higgsfield__create_character` accepts only
  Higgsfield-hosted URLs — catbox/0x0 are «Invalid image url» (that was the 2026-09 "character failed").
  Upload via the claude.ai MCP (`media_upload` → curl PUT to the presigned S3 URL → `media_confirm`; needs no
  credits) or reuse `show_medias`. `image_reference_url` on Soul is NOT a character reference: it rebuilds the
  reference photo's composition and the enhancer rewrites the prompt into a caption of it (two wasted portraits).
  Use `custom_reference_id` = the character id. Character «Alon Gabay»: f421a9c0-0d27-43a1-bede-e1c6e8d81d7d.
* Extra literal b-roll from the 2025 shoots (meeting, phone, TV, selfie, night mic, desk camera) via
  `broll_cut.py` with `"cx"` for a wide source; items anchored to caption TEXT after a ripple (`r8_timing.json`),
  never to remembered times.
* Motion titles carry a soft dark scrim (rounded, blur 55, α 0.45) behind the block — without it «02» vanished
  over the stage spotlights of the Higgsfield crowd scene. If CapCut shows ProRes 4444 alpha as black boxes,
  the same four titles exist as HEVC-alpha (`hevc_videotoolbox -alpha_quality 0.9 -pix_fmt bgra -tag:v hvc1`,
  the format of his own «באנר יוטיוב HEVC שקוף») in `bunker-0923/titles-hevc/` — swap the files, same names.

### `reel_caption_pop.py` — caption entrance as eased keyframes (0923 r9)
`python reel_caption_pop.py "<project>" [--lo 0.86 --hi 1.04 --t1 0.13 --t2 0.26] --write`. Drops any cached
animation wrapper on the track and writes a scale pop 0.86 → 1.04 → 1.00 (CurveInOut, seg-local `time_offset`)
on every card. Born when Alon called the cached `Grow` preset at 0.14 s «רובוטית ומהירה». Cards shorter than
1.6 × t2 get a proportionally shorter pop. Idempotent.

### `reel_motion_energy.py` — camera motion from the voice (0923 r9)
`python reel_motion_energy.py "<project>" [--tracks 0,1] --audio <pre-compression voice> --write`. Every camera
shot ≥ 2 s: eased entry punch +3 % over 0.5 s, drift 0.6 %/s, then in/out punches (6–10 %, 0.42→0.28 s) on
caption cards that start a sentence or carry a stressed word — stress = peak 50 ms RMS after the word minus the
local median (±1.5 s), measured on the timeline through the source map. **Measure on the PRE-compression audio**:
after the −16 LUFS / LRA 3 compressor every word peaks within 2 dB and nothing is "loud". Absolute lid
`--ceiling 1.15` × the smallest framed scale (0923: 3.30 → 3.79; Alon stopped a head at 3.83). Position is
re-solved per key for an eye line at 0.34 H; b-roll / titles / logo tracks are never touched. Alon's brief:
«תנועות חדות יותר כשיש גלי קול חזקים יותר ולפי התמלול, תמיד easing». Dry run prints punches/min, in/out, max scale.

### `reel_localize_materials.py` — repair the online-material trap on an existing draft (0919, 29.09)
`python reel_localize_materials.py "<project>" --write`. Every video / photo material that has a real local file
but carries the white card's ONLINE identity (material_id 7106436387146108187, «Trending», source 1) gets the
local identity (material_id "" · category "local" · source 0 · check_flag 63043327). The card itself stays.
0919 had 65 such materials — every b-roll, scrim, rule and logo cloned from the card before `reel_broll.py`
learned the fix — and Alon saw them as «הבירולס בכלל לא עובדים». Run it on any draft built before 23.09
that shows white boxes; `register_media.py --write` after it.

### `reel_repoint_materials.py` — the second half of the white-box repair (0919, 29.09)
`python reel_repoint_materials.py "<project>" --write`. A material cloned from «白» can also keep the card's
`path` — CapCut's online cache image — so after the identity fix it is STILL the white picture. This repoints
every material whose `material_name` exists in the draft folder at that file (absolute path, like a hand
import) and refreshes `duration` / `width` / `height` from ffmpeg. 0919: 65 materials. Run both scripts, then
`register_media.py --write`; check a still — logos / rules built against 1920×1080 placeholder dims may change size.

## 0923 round 10 — «עוד בי-רול, אנימציות Remotion, כתוביות עם מסגרת וצל» (30.09)

* **His hand-edits are the base.** Between r9 and r10 Alon edited the draft in CapCut (two b-rolls and a bed removed,
  three captions deleted, the reel-1 arrow given a 0.01→0.11 grow, a blur plate under the hook). A track rebuild
  (`reel_broll.py`, `reel_sound.py`) would have erased all of it. Freeze his state first (`draft_info.<p>-r10-base.json`),
  diff by TRACK NAME not index (he adds tracks), and only add.
* `reel_broll_add.py "<project>" --items adds.json [--trim file=dur,…] [--remove file,…] [--write]` — appends items to the EXISTING
  `broll` track (nearest b-roll segment as template, reel_broll's 1.08→1.0 settle, local identity) and a click per item
  on the existing `sfx` track; `--trim` shortens a segment (tail keyframe follows); `--remove` drops a segment + its click (0923 r10: the «phone call» pick
  was a guest adjusting a mic — a still after the write is what caught it). Refuses overlaps. QA after: his
  tracks byte-identical vs the base, old b-roll segments untouched except the trims.
* `reel_caption_stroke.py "<project>" [--write]` — the house stroke+shadow on every caption material (המלצות הבונקר
  recipe: stroke 0.0353, shadow d8 ∠−45 α0.65 diffuse 0, mirrored on the material, `shadow_point = d×0.1272792`).
  It REMOVES `styles[].effectStyle` first: a text effect owns outline+shadow and strokes beside it double up. Effect OR
  recipe, never both. Not verifiable headless — `render_draft.py` draws captions through ASS with its own outline.
* Remotion inserts for a 9:16 reel (`~/bunker-reel-anim`, 1080×1920 30 fps, Heebo, Bunker dark +
  `#D71921`): one literal device per sentence, ≤ 2.6 s, content kept above y≈1000 so the caption band stays quiet;
  `npx remotion render <Comp> --codec h264 --crf 16` → ffmpeg `scale=in_range=full:out_range=tv,format=yuv420p` + bt709
  tags into the draft folder (Remotion's H.264 is full-range yuvj420p). Stills of every comp looked at before the render.

## 0923 round 11 — gentler pop, kinetic stacks by plan, designed SFX (30.09)

* «האנימציה של הכתוביות אגרסיבית מדי» → `reel_caption_pop.py --lo 0.95 --hi 1.012 --t1 0.16 --t2 0.32` (was 0.86/1.04
  @0.13/0.26). A 14 % overshoot reads as a jolt 360 times a reel; 5 % with a 1 % overshoot is the «עדין» he asked for.
* `reel_kinetic.py "<project>" --plan kinetic.json [--zone 920,1205] [--write]` — the 0910 kinetic stacks
  (`kinetic_headlines.py` v5 look) for ANY reel, without the 0910 hard-codes: a stack CONSUMES whole caption cards
  (`from`/`to` = card boundaries) and shows their words (roll / replace / words modes, sizes s/m/b 15/18/25, entrance
  + exit cycles, pages by pause, RTL word rows with a click on the first + highlighted words, a swoosh on roll/replace
  starts on `sfx text` lanes cloned from the project's own swoosh/click segments). Word times inside a card are split by
  character share — good enough for cards ≤ 1.5 s, and no word-level cache is needed. The script refuses a line that
  does not spell the consumed cards' words in order, so nothing is lost or shown twice. Zone = above the logo: measure
  the logo's top edge (0923: scale 0.43 → 255 px tall, top 1216) and leave ≥ 270 px, or a b + l pair paginates.
* `reel_sfx_place.py "<project>" --items sfx.json [--write]` — one composite wav per animated insert on the `sfx`
  track, replacing the generic click at that time (`sfx 2` lane on a clash). Composites are mixed offline
  (`~/Movies/reel-captions-work/bunker-0923/sfx/build_anim_sfx.py`: library hits at the animation's own beats +
  numpy-synthesized accelerating ticks; `amix … apad=whole_dur … alimiter`; peak −6 dBFS; segment volume 0.35 ≈ the
  click's −1.5 dBFS file at 0.30). ⚠️ `amix` ends at the LONGEST input, not at `atrim` — pad to the insert length.

## Phone selfies, portrait source (לקוח M «לקוח M החמוד», 04.10)

* `reels_build.py` works on a portrait WhatsApp source unchanged (`cam2: null`, `handle 0`, `fps 30`). `frame_shots.py`
  does NOT — it assumes a 16:9 source ("0.396× fill"); measure the face with YuNet yourself.
* `reel_pauses.py` floor must sit above the outdoor noise: measure the 10th percentile of the voice copy (here −33 dBFS)
  and use ≈ −26. Selfies open with 1.5–2 s of dead air — cut card_end : onset − 0.10 so the first word is frame one.
* `reel_blur_frame.py "<project>" --plate <blurred copy> --eyes <reel start>:<eye line>,… [--scale 0.80] [--write]` — when
  the face is too big for a caption band (head 0.44 W, chin 0.75 H): sharp layer at 0.80 on a new track (head → 0.355 W,
  eyes → 0.34 H, chin ≈ 0.52 H), track 0 becomes a ffmpeg-baked blurred copy (CapCut's Blur effect is not injectable
  once its cache is gone). Run LAST among the camera stages. Captions at y −0.27 then sit inside Meta's Reels ad safe
  zone (text between 14 % and 65 % of the height).
* Voice limiter at −1 dBFS + bed at 0.10 clipped 55 samples → voice segments at 0.89.

## «לקוח M החמוד» round 2 — inserts, kinetic, CTA button on a client selfie (04.10)

* Free tools only (Alon: no Higgsfield, nothing paid): Remotion inserts (`src/Client M.tsx` in bunker-reel-anim — the
  client's landing orange `#F47D20` on cream `#FFF6EC`, Heebo), offline SFX composites (`client-1004/sfx/build_anim_sfx.py`,
  run with the capcut venv — system python 3.9 chokes on the f-strings), CapCut keyframes.
* `reel_broll_add.py --tpl-track "client sharp"` — when the `broll` track holds only stills (arrows), clone the
  video template from the camera track; the recipe resets scale/keys anyway.
* `reel_kinetic.py --hl-color f47d20` — the highlight in the client's colour (default stays the 0910 yellow). Zone for
  a selfie with the blur frame: 980,1245 (chin ≈ 998, Meta floor 1248); m+b and l+b stacks paginate there — fine, calmer.
* `reel_overlay_still.py "<p>" --file cta.png --at t:dur,… [--width-px 600] [--y-px 1075] [--track cta]` — a PNG CTA
  button over the arrow, own track, eased entrance 0.62→1.04→1.0 + one 3 % breath; template = an existing still.
* Hook supers: at size 30 a hook is ≈ 855 px in CapCut — the headless render draws it at a third of that, so "the hook
  is small" from a headless frame is NOT a finding. Check y instead: centre 250 px sat inside Meta's top 14 % → 0.63.
* Reel renders exclude the title card: reel-local t = timeline t − block start − card (5 s).

## CapCut draft → Remotion render (05.10, «תוכן הבונקר (0923)»)

* `capcut_to_remotion.py "<project>" --out <dir>` — one JSON per reel (footage between the white cards; the card is
  dropped). Every video/photo/text/audio segment becomes a layer: z = track order, reel-local t0/t1, CapCut geometry +
  keyframes (video `time_offset` = SOURCE µs → segment-local; text already local), curve names, in/out animations,
  Compound clips expanded at their z, `lut: true` under the adjust track, `matting.flag` → `matte` dir, camera audio as
  its own layer, cache-only library audio listed as `missing`.
* `~/Movies/reel-captions-work/bunker-0923/remotion/prepare.py` — the per-project step: hard-link assets into
  `bunker-reel-anim/public/<dir>`, bake the cube into the camera copies (ffmpeg lut3d, CRF 16), rebuild Remove-background
  as ProRes 4444 from CapCut's own masks (`matting/<id>/2/mask/<source µs>` = raw u8 448×256 per frame), substitute missing
  library audio (VOID → gritty_hiphop, pen → Marker, shutter → Cam shutter, mouse → ccstudio click).
* `bunker-reel-anim/src/draft/DraftReel.tsx` — renders it: fit = min(W/w,H/h), centre (W/2+tx·W/2, H/2−ty·H/2);
  CurveInOut/Out/In = bezier(.42,0,.58,1)/(0,0,.58,1)/(.42,0,1,1), the START key's curve shapes the span; text px = 6×size,
  stroke/shadow scale with the glyph, leading 0.98 (1.12 pushed a 2-line hook off the top).
* Traps: HEVC-alpha titles decode BLACK in Remotion → use the ProRes 4444 copies; a reel block ends at the card, but the
  footage can end earlier → trim `dur` to the last main-track frame or the reel ends on black + logo; Glare II transition
  not reproduced.
