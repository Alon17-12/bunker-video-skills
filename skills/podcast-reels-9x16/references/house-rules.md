# House rules — earned, not guessed

Every rule here came from Alon rejecting the alternative. They are the body of the skill; `SKILL.md` is the map. Read the section that matches the stage you are on, and read `gotchas.md` for the failures behind them.

## House rules (earned, not guessed)

These came from Alon rejecting the alternative. Follow them.

**Timing.** The client's numbers refer to their convenience file, not the
angles. Cross-correlate to get the offset — file metadata lies. **When the
number and the quoted words disagree, the words win**; the numbers are scrubbed
by eye and are routinely 2–3s off. Say which ones you moved and why.

**The mics are on their own clock too, and it is not the cameras'.** There are
*three* offsets in a RODECASTER episode, not one, and the third is the easy one
to miss: on אורח S the isolated `n_COMBO-n.wav` channels run **148ms ahead of
the camera files** — cameras carry the desk's main out, the mics are pre-fade.
That is nearly five frames of lip-sync, and it silently poisons the multicam and
the caption timings as well as the sound. Measure it the same way as the client
file (cross-correlate three or more windows), and **check it against itself**:
Live-Mix sat 160ms behind the COMBOs and 20ms ahead of the cameras, and
0.160 − 0.020 = 0.140 is what makes the number trustworthy rather than merely
consistent. Everything downstream takes it as `--mic-offset`.

**Who is on screen.** Camera *n* belongs to mic *n*. Cut to whoever's mic
carries the voice — *including* his 0.4–1.0s interjections. A planner with a
1.6s minimum shot throws every one of those away, and the guest ends up on
screen while the host delivers the punchline. Either cut to him for a short
reaction punch, or centre a split screen on the line, or extend the shot that is
already on him. Never leave him off screen.

**Both cameras run end to end, and opacity is the edit.** This is the delivery
format, not an implementation detail — Alon asked for it by name:
*"איפשרת לראות את שתי הרצועות לאורך כל הדרך — עם עריכה של השקיפות (100 / 0).
הייתי רוצה שזה יעבוד גם באופן הזה מעכשיו והלאה."* Lay **both** angles across
every reel range on two stacked tracks, split at the cut points, and decide who
is seen with `clip.alpha` 1 or 0 per piece. Never route by laying camera 2 only
where camera 2 is shown.

The point is that my routing stops being final. He opens the project, sees both
angles, and fixes any decision with a slider: reveal a shot I dropped
(Opacity 0 → 100), drop a cut he dislikes (100 → 0), move a cut (⌘B, then
Opacity per piece). No footage is ever lost and the boundaries already sit
inside silences. A build where the losing camera's frames were deleted forces
him back to me for every change, which is the opposite of the job.

Four things this constrains:

* **End to end means the reel ranges, not the episode.** He rejected a build
  that carried the whole source alongside the cut — *"לא צריך את המקור כהעתק,
  שמור רק את הקטעים שנבחרו לרילס"*. Both layers hold exactly the ranges that
  made the reel, aligned to the same `target_timerange`.
* **A flip is a hard cut, not a ramp.** Split the layer at the cut and give each
  piece a *constant* `alpha`; that is what CapCut surfaces as the clip's Opacity
  and it is the control he actually reaches for. An alpha keyframe pair works
  visually but hides the boundary from the panel — use it only inside a piece
  you have a reason not to split.
* **The bottom layer never flips.** It holds one camera at `alpha 1` for the
  whole range as the fallback picture, and only the layer above it toggles.
  Punching a hole in the bottom to "hide" a shot shows black wherever the top is
  hidden too — that is the twenty-five-seconds-of-half-black failure in another
  costume. Alpha is also a cut, not a fade: 0 or 1, never 0.4, and never a ramp
  longer than a frame.
* **The push-in belongs to the piece it is on.** Keyframes on a hidden piece
  still interpolate into the visible part; clamp them there too.

`scripts/qa25.py` check 28 measures this: full coverage on both layers, the
visible/hidden share, and any frame with two full-frame layers showing.

**Sometimes the multicam is already his.** Alon may hand you a project he is
cutting himself — "התחלתי לבצע מולטי קאם, אל תיגע, רק תוסיף כתוביות". Then the
caption track is the only thing you own, and you prove it afterwards: reload the
draft and compare each of his tracks against the pre-run backup **byte for
byte**, not by segment count. Two things break that comparison if you are not
careful:

* His multicam is usually **alpha, not track order** — both cameras run the full
  length on two stacked tracks and `alpha` 1/0 on the upper one decides who is
  seen. So "which camera is on screen" is not "which track has a segment", and
  the boundaries that matter for captions (the real jumps in source time) are
  the **lower** track's segment boundaries; an alpha flip inside one of them is
  a camera change over continuous audio, which a caption may cross.
* **Do not renormalise `render_index`.** CapCut hands out non-contiguous values
  (a track whose segments read 1, 2, 3 while the adjust track reads 0) and
  rewriting them to a tidy 0,1,2,3 is a silent edit to his project. Restore
  every one of his segments to the value it had, and give only the new track
  `max + 1`.

**Never cut into dead air.** Every cut lands inside a silence where both mics
are quiet — but a shot that is *itself* mostly silence is a mistake. No shot
under ~1s. If the camera would flip back for a fraction of a second of silence,
hold the previous camera until the real transition.

**Zoom moves in one direction.** Each shot starts at 100% and pushes in;
the reset to 100% happens under the cut while the other camera covers. In-then-out
inside a single shot reads as a wobble. Amplitude scales with shot length
(≈1.2%/s, capped ~10%) so a 2s beat barely breathes and a 10s hold travels.

**The number the eye judges is the rate, not the amplitude** — and the rate is
not one number. Measuring three reels he approved (אורח O, פרויקט-דוגמה N, אורח G)
gives the same shape in all of them:

| Where | Rate | Example |
|---|---|---|
| first ~0.5s after the cut | **15–25%/s** — a deliberate punch | 3.1605 → 3.5576 in 0.5s |
| the body of the shot | **≈1.2–1.5%/s** | 3.55 → 3.40 over 5s |
| last ~0.5s before the cut | occasionally another punch | 3.5416 → 3.8 in 0.9s |

So a fast entry is *his style*, not a defect, and a uniform slow ramp across the
whole shot is not what he cuts either. What he rejected on אורח P —
*"יש קטעים של זום אין חד ומהיר, גם כשיש שתיקה (בעיקר על מצלמה 2)"* — was 3%
over a **1.1s reaction cut during silence**: a punch on a shot with nothing
happening in it, on the listener's camera. The rule that separates the two is
not the rate, it is what the shot is:

* a shot under ~2.5s sits **completely still**; a reaction beat is already a
  movement,
* a shot whose own mic is silent does not push in — the zoom follows the voice,
* everything else: punch in on entry, then ≈1.5%/s.

Check 18 therefore stops calling a shot "frozen" below the static length, and
check 19b measures only the **sustained** rate, excluding the entry and exit
windows. All three approved reels come back with zero excursions; my אורח P build
came back with the reaction punches.

**And the zoom has an absolute ceiling, not only a relative one.** A per-shot
amplitude cap does not bound anything: every pass that raises a shot to clear a
face raises its floor too, and after three rounds of corrections a shot was
sitting at 3.83 — 26% of the source width, a head filling the frame. Alon
stopped it there. Bound each shot between two numbers instead:

```
floor = what THIS shot's lowest chin needs to clear the caption band
ceiling = the smallest scale at which EVERY chin in the reel still clears it
shot runs floor → min(ceiling, floor·(1+amp))
```

The ceiling is measured, not chosen: sweep candidate values against the face
scan and take the tightest one with zero overlaps — on this episode exactly
**3.55** (28.2% of the source width), against 3.40 that Alon approved by hand
and 3.7+ that he rejected. If a shot's floor exceeds the ceiling, the caption
band is too tall for the footage; say so rather than silently cropping past it.

**And the number that carries across episodes is the rendered head, not the
scale.** A scale ceiling is only meaningful for one camera at one distance: on
צומת 20 the host's angle is a wide two-shot where his face is 8.7% of the source
width, and the guest's is a tighter single at 11.3%. Framing both to the same
*scale* would make one a portrait and the other a landscape. Frame instead to
what the viewer sees — head about **13% of the canvas height below the top edge**
and **33–38% of the canvas width across** — and let the scale land where it
lands (here 3.2 on one angle and 3.9 on the other, both correct). Then verify
the numbers you actually care about: head size, headroom, and chin against the
caption band.

Clamp keyframes in the *hidden* stretches too. A key the camera never shows
still anchors the interpolation into the visible part and drags it over the
ceiling.

**`scale` is meaningless until you know the material's `crop`.** CapCut crops at
the material level and then *contains* the cropped rectangle in the canvas, so
the scale that fills the frame is a property of the angle, not of the project.
On `0810` camera 1 is uncropped 16:9 and fills at **3.1605**; camera 2 carries a
square crop `(0.3486,0.1038)-(0.8283,0.9566)` — 921×921 of the source — and
fills at **1.7778**. Copying 3.33 from one angle to the other is how the guest
ended up as a face with the top of his head cut off, at nearly double the
linear zoom Alon uses, while every number in the JSON looked like its neighbour.

So: compute the rendered rectangle before comparing anything.

```
w,h = source_w·(x1−x0), source_h·(y1−y0)        # the crop, in pixels
ar   = w/h
rw,rh = (1080·s, 1080·s/ar)  if ar ≥ 1080/1920  else (1920·s·ar, 1920·s)
fill  = 1920 / rh(s=1)                           # the scale that covers the canvas
```

Head size, chin, face centre and "does this cover the canvas" all follow from
`rw,rh` — never from `607.5·s`, which is only true for uncropped 16:9. Checks
6, 7, 8, 10, 11 and 12 all measure through this now, and `face_scan.py` maps the
face box through the crop rectangle before it maps it onto the canvas.

**Measure the horizontal, and measure it on the render.** `transform.x = 0`
does not mean "centred" — it centres the *source*, and nobody sits in the middle
of a two-shot. On אורח P אלון every one of my 128 shots was written at x = 0 and
the guest's face landed at **76–82% of canvas width**, pressed into the right
edge, through four rounds of corrections and a QA that passed 41/41 — because
every check I had measured the vertical. The rule was already in this file
(33–38% of canvas width); nothing enforced it.

Derive x the same way as the eye anchor, from a frame he approved:

```
face_px(x, s) = 540 + x·540 + 540·s·(2·cx − 1)      cx = face centre ÷ source width
x = (target_px − 540 − 540·s·(2·cx − 1)) / 540      target ≈ 0.33–0.38 · 1080
```

and re-solve it at every scale so the face stays put as the shot pushes in —
which is check 9, the pan growing with the scale. Then clamp: if the material's
left edge would come off the canvas, spend the slack instead of tearing a black
band. `scripts/face_scan.py` now reports `face_x` per sample and prints the
distribution, so this is one number to look at rather than a frame to squint at.

**Split screen earns its place.** Genuine simultaneous speech is rare (five
moments of 0.4–0.7s in a 4-minute cut) and far too short to hold. The moment
that actually wants both faces is the **exchange** — where the cut would flip
camera 1 → camera 2 → camera 1 inside a few seconds. Collapse that whole span
into one split. Also split the middle of any hold ≥9s. Enter and exit on a
**hard cut**, not a slide: a slide shows a black half while the second angle
travels in.

**And the split has a time budget, measured off reels he cut himself.** Across
his own work the share of footage time in split screen is **11%** (אורח P אלון
reel 1), **16.7%** (אורח O) and **20.4%** (פרויקט-דוגמה N) — so the budget is roughly
a sixth of the reel, and it is worth re-measuring per project rather than
carrying one number. My אורח P build came back with **34%**: 49 splits, every one
exactly 5.2s. Two bugs, both worth recognising by their shape:

* The splits were all *hold-breaks* dropped into the middle of monologues. A
  long hold on a speaking face is a mild problem; putting the silent listener
  next to him for five seconds is a worse one. Break a hold only where something
  is actually happening on the other mic.
* The exchange rule never fired **once**, because it ran after the minimum-shot
  pass had absorbed the short interjections — so the 1→2→1 pattern it looks for
  no longer existed anywhere in the plan. Capture the turn boundaries from the
  **raw** routing, before absorption, and keep them.

Then spend the budget instead of applying a rule: score each candidate window by
how many turn boundaries fall inside it, take the densest first, skip anything
overlapping one already taken, and stop at the share you measured. You get
splits where the conversation is fastest, which is where they belong.
`reel_motion.py --split-share` (default 0.18) enforces it and prints how many
long holds it left unsplit — that is a decision to report, not an omission to
hide.

**And never crop the switched file across a split of its own.** The רז is a
finished 16:9 program: it cuts, and it also composites its own **side-by-side**
splits. Take a 9:16 crop of one of those and you land *between* the two panes —
the right edge of one person and the left edge of the other, which in practice
means two torsos and no face at all. Measured on אורח S reel 1 (15.08): **11 of
25 sampled frames, ~45% of a 37s reel, with nobody's head in frame**, shipped to
the client and approved by every structural check we had.

The seam direction is the tell, and it is free to check: **ours is horizontal**
(halves stacked, 1080×960 each), **the switcher's is vertical**. A vertical seam
in a 9:16 output is never a split you built — it is proof you are rendering the
program file instead of the cameras. Grab one frame and look.

So when the ISO path is unavailable and the רז is all you have, the fallback is
not "centre-crop it anyway":

* find the stretches where the רז is composited (a vertical seam that holds), and
* crop those to **one pane** — the open mic already says whose — never across the
  seam; or
* move the reel's window off that stretch, or hand it to a person.

A reel with a face in every frame is the floor, not a nice-to-have. Nothing else
in this file matters on a frame where nobody's head is visible.

**And if the project has no split to copy from, do not build one.** Two families
exist in his work and they look nothing alike, so a split with a guessed scale
and seam is a coin flip he will reject on sight — which is what happened on
0830, a project whose three approved reels contain **zero** split screens.
`reel_motion.py` now scans for an existing split before spending the budget and
skips the pass with a message when there is none; `--invent-split` overrides it,
and the flag's name is the warning. The right move is to ask which approved reel
to measure from.

**Copy the split's composition; do not choose it.** Two families exist in his
work and they look nothing alike: halves *filled* to the seam (scale ≈1.58–1.75,
pinned as below), and full uncropped 16:9 halves at `scale 1.0` stacked with
black bands above, between and below (`y = +0.4363` / `−0.5637` on this canvas).
Reel 1 of אורח P אלון is the second kind and I shipped the first. Open the approved
reel and read which one it is.

**Verify the style you cloned, don't just clone it.** `reel_captions.py` copies a
prototype material out of the donor's caption track, and on 0830 that prototype
came out wrong in a way no count would show: **no house text effect, a black
`background_color` box behind every word, `border_width` 0.036 instead of 0.08,
and `strokes`/`shadows` written into `content`.** Alon saw it in the first frame
of the first playback.

The cause is worth recognising because it generalises: the prototype was
*whichever segment came last for that colour*, and exactly one caption of 262 in
the donor carries no effect. One bad row out of hundreds decided the whole
deliverable. Take the **modal** material per colour, and then assert the three
things that contradict each other — an effect *plus* injected strokes/shadows,
or an effect *plus* a background colour, is not a style, it is a mistake. With a
text effect applied the effect **owns** the outline and the shadow; the panel
sliders do nothing and injecting `strokes`/`shadows` beside it is the specific
move that must never happen. The script now prints the chosen prototype's
effect id, border, background and stroke/shadow flags, and exits on a
contradiction.

**A Compound clip is not footage either.** The card rule below was written for
`type == "photo"`, and a Compound clip is `type: "video"` with an **empty
path** — so it walked straight through the filter on 0830, its
`source_timerange` started at 0 like a card's, and the engine transcribed the
*opening seconds of the episode* onto the first 2.5 seconds of the reel. Alon
read the result as invented words, which is exactly what it was. Test for a real
file on disk, not for the type field, and print what you skipped.

**A cache belongs to the cut it was built from.** `--reuse` after the editor has
re-trimmed the timeline replays the old word offsets onto new footage: on 0830
he cut 39 seconds out between two runs and every card afterwards sat over
something else. The script now stores a signature of the clip list and refuses
to reuse across a change. Cheap; the failure it prevents is invisible in every
count you would otherwise print.

**Captions.** Reel style: ~3 words, punctuation stripped, gap-free, nothing
under ~0.5s. Colour per *word*, not per card — the host mostly drops single
words into the guest's sentence. A card holding both speakers becomes two
lines, one colour per line, never two colours on one line.

**A card is a breath, and the cards are balanced.** Two rules do almost all the
work, and Alon has flagged both when they were missing:

* **Break on any pause longer than ~0.25s.** Three words with half a second of
  silence between the second and the third read as an error, because the card
  is still sitting there while nobody is talking. Cut the words into runs at
  speaker change, at a cut, and at every gap over the threshold — nothing else.
* **Break where the energy dips, not where the word list says there is a gap.**
  The transcriber emits touching word intervals, so `next.start − prev.end` is
  0.00s at almost every candidate break and scoring on it is scoring on noise.
  Measure the actual RMS dip at the boundary and prefer the deepest one; back it
  with two word lists — nothing may *end* a card that leans forward (של, את, עם,
  כמו, כי, מה, הכי, חוץ) and nothing may *start* one that leans back (אותי, לו,
  בי, שלהם). See `references/gotchas.md`.
* **Then split each run *optimally*, not greedily.** Filling three words at a
  time and letting the remainder fall out leaves an orphan: a four-word run
  becomes «באה ואומרת דבר» + «כזה» instead of «באה ואומרת» + «דבר כזה». Score
  each candidate card `(max_words − words)²` and take the cheapest partition
  (a five-line DP over the run) — it prefers 2+2 over 3+1, 3+2+2 over 3+3+1,
  and it costs nothing. Feed it the same width and duration limits so the
  partition is legal by construction.

A run of one word is fine when the word stands alone — «אוקיי», «וואו»,
«מטורף» are real beats. An orphan is a word torn off a phrase, not an
interjection.

**A card's life on screen is set by the *next* card, not by its own words.**
Captions are gap-free, so a card ends when the following one starts — which
means the chunker cannot enforce a minimum duration no matter how it scores, and
mine happily emitted cards that lived **0.067s** while every one of them passed
its own duration limit. Add a floor pass *after* chunking: any card shorter than
the house minimum (~0.42s, read off his reel) merges into a same-speaker
neighbour, or borrows time from one, and then re-derive every timing. Report the
minimum and the median you ended with — those two numbers are what "the captions
flicker" turns into.

**Write caption times on the frame grid.** CapCut re-rounds every segment to
`1e6/fps` on its own, so a card whose end and the next card's start are two
different microsecond values become two different frames — a one-frame hole,
ninety times in a row, which is what a viewer calls "the captions flicker".
Snap both edges and set each card's end to *the same number* as the next card's
start.

**Transcribe each microphone on its own, never the mix.** A summed track carries
both voices into every word, and the model guesses: on this episode the mix
produced «איך אתה שם שנה כל החיים» where the isolated channels produced «איך
אתה משנה את כל החיים» — which an independent transcript of the same moment
confirms word for word. Build one timeline-aligned array per mic, transcribe
both, and keep each word only where its own mic actually owns the sound. The
speaker colour then falls out of which channel the word came from, instead of
being inferred afterwards.

Two more things the transcript must respect, both invisible in the JSON:
**a caption may not straddle a cut** — the words either side come from different
minutes of the episode, so the text would sit over footage that never said it;
clip every card to its clip and drop what is left shorter than ~0.35s. And
**check every card against its own speaker's energy** — a card over a silent
channel is a hallucination, not a line.

If the client sent a full-episode transcript, align it by timecode and use it as
a *second opinion*, not as truth — it is usually machine-made too, and on this
episode it was demonstrably garbled in places where mine was right. Report the
agreement rate and list what disagrees; don't silently overwrite one with the
other.

The disagreements sort themselves into three piles, and only one is worth your
time. Inflections and spelling («אסתמה»/«אסטמה») change nothing. Words both
transcripts hear the same way stay, however odd they read — two independent
listeners agreeing is evidence, not error. What you are hunting is the third
pile: a token neither source renders as a real word, where the meaning is
unambiguous once you look at both. «חמש הכידות במתמטיקה» against the client's
«חמש אחיות מתמטיקה» is Alon's own reel title, «חמש **יחידות**». «היסטוריקה» is
«הסטויקה»; «מרקוס אראליאס» is «מרקוס אורליוס». Ten such fixes on 947 words —
apply them to the **word list before chunking**, so the colour and the card
widths are computed from the corrected text, and print each one with its
evidence.

Two mechanical traps in that list: a word the model splits in two («ב» + «-AI»,
«צ» + «לקוח M») has to be rejoined before chunking or the card breaks mid-word, and
the apostrophe in «צ'לקוח M» is stripped by the punctuation pass — write the
Hebrew geresh `׳` (U+05F3) instead.

**A caption is one line.** Chunk so every card fits the frame on a single line
at the house font size, measured in **rendered pixels** with the real `.ttf`,
never in characters — 'w' is nearly three times an 'i'. If a card does not fit,
**split it into two cards**; do not let it ride and do not shrink the font.
Letting CapCut wrap it is the worst option: it breaks at whatever column runs
out of width, and it will orphan a single letter on the second line
(«משקיעים היא מאוד פשוט / ה»). Two-line cards exist for exactly one reason —
the deliberate two-speaker split above.

**Captions never cover a face.** Do not eyeball this and do not inherit the
template's position — measure. `scripts/face_scan.py` detects the face in each
shot's source frame and maps it through that shot's own scale and pan onto the
finished canvas, so you get the chin position *as rendered*. Put the caption's
**top edge** just below the lowest chin, and check the bottom edge against the
safe area (~0.86 of frame height, below which platform UI starts).

**And the caption height never changes.** A caption that jumps makes the eye
chase it. One `transform.y` for every caption in the project — move the
**frame**, never the caption.

Those two rules collide when a split screen is already cut and you are not
allowed to touch it. On the אורח P אלון reel the full-frame chins topped out at
0.674 of frame height — a band at 0.690–0.736 sits on the chest all through the
reel — but inside the two split sections the *lower* speaker's chin fell to
0.79–0.845, and clearing that needs a band starting at 0.85, past the safe area.
No single height exists. Don't split the difference silently: place the band for
the composition that dominates, then say exactly how many cards land on a face
and for how long, and offer the two fixes that do work — raise the lower frame,
or move only those cards. Which one it is, is the editor's call, not yours.

**White text on a light shirt needs its own shadow.** The house style already
carries a black outline (`border_width` ≈ 0.08), and it disappears against a
white shirt or a bright chair. Turn the shadow on for the *white* speaker only —
`has_shadow`, black at ~0.9 alpha, distance ≈ 7, smoothing ≈ 0.45 — and nudge
the border to ~0.10. A shadow is a separation from the background; an outline is
a separation from the letter. You need both here, and the yellow speaker needs
neither.

Which frame you move decides everything downstream, and the order matters: the
eye anchor first, then the full-frame lift, then the split halves, and only then
is it known how high the caption can sit. The arithmetic for each — and the trap
where a split pinned at a constant ±0.5 drifts off the seam as it zooms — is in
`references/framing.md`.

**A term is one caption.** A multi-word term never straddles two cards:
«מלווה משקיעים», «בית ספר», «עסקת נדל"ן», «החזר השקעה», «צפון קפריסין».
Treat each as a single atomic token before chunking, and keep the episode's
domain terms in a list you extend as you meet them — the transcript is the
first place to look for them.

**One project.** Ship a single CapCut project. If a working copy exists too,
move its folder out of `com.lveditor.draft` — deleting the registry entry alone
does nothing, CapCut rescans the directory and puts it straight back.

**Each mic belongs inside its own camera file, not on an audio track.** Alon does
not want two waveforms sitting in the timeline — the sound should travel with the
picture. Mux mic *n* into camera *n*'s work copy (`-c:v copy`, so nothing is
re-encoded) and give every footage segment `volume 1`. Both cameras then play
their own speaker at all times, opacity decides only who is *seen*, and the
editor sees a clean timeline.

The trap that follows is severe: **the moment you route by laying discrete
camera-2 segments only where camera 2 is shown, camera 2's microphone exists only
there too.** On one episode that silently deleted 102 seconds of the guest's
voice — every stretch where the host was on screen.

The opacity build above closes this by construction: both layers cover every
frame, so both mics are always in the mix, and `volume 1` on every segment of
both layers is correct — the two files carry *different* isolated mics, so
nothing doubles. That is one of the reasons to prefer it. Two conditions:

* Mux the **isolated** mic, never the Live-Mix — a mix in both files sums each
  voice twice with a few ms of offset, which combs.
* A video track with `attribute: 1` is **muted**, whatever `volume` its segments
  carry. A whole reel set shipped silent this way while every volume in the JSON
  read 1.0. Check the track flag, not just the segments.

If you inherit a project routed the old way — discrete visible segments only —
keep a second full-length layer at `alpha 0, volume 1` for the sound and set the
visible ones to `volume 0`. Either way the invariant is the same and check 17
asserts it: the audible coverage of camera 2 equals camera 1's, to the
microsecond.

## The brand layer

Grade, intro music and logos are fixed across צומת 20 reels and every value is
already on disk — **read them off the neighbouring project rather than deciding**
**them**, including how many logos this reel gets (two, two with the guest's mark,
one, or *none* for a הבונקר customer's reel) and where the two slots sit. The
adjust track grades everything beneath it, so it belongs above the cameras and
below the titles and captions; leave it on top and the LUT eats your captions.

Full detail — the slot coordinates, the four delivery cases, the music, and the
three consequences that have each been got wrong — in `references/brand-layer.md`.
`scripts/qa25.py` check 27 measures all of it.

## Reels from an hour the editor already laid out (0830 (1) פרויקט T2, 15.09.26)

The project held the whole episode as **two full-length layers** (camera 2 under, camera 1 on
top at alpha 1 — one camera visible throughout) and Sivan sent three timecode ranges plus
"split where I marked, I'll delete precisely" and "a running timer on reel 3 so I can name what
to cut". Four things that decided the build:

* **Whose clock are the numbers on?** Not the cameras'. Every quoted sentence was missing at
  the camera time and present at that time in the switcher's file (`… רז 2.mp4`) — the רז runs
  39.14s behind the cameras (identical in three cross-correlated windows). Transcribe ±7s at the
  marks on **every candidate file** before believing any of them; the mic clock (COMBOs 0.146s
  ahead) is a third offset on top.
* **"As is" means copy his layering, not route it.** Both layers over the reel range with the
  same scale/transform/alpha/volume as the hour, a white card (his 9.77s photo) before each
  reel, appended after the timeline end. Split *both* layers at the delete marks (word
  boundaries from the transcript — «קודם» … «דג.») so ⌘-delete removes exactly the phrase.
* **The donor is a track, not a project.** The biggest text track of `0830 (1)` is an older
  reel set with a black background box; the style he approved lives on track 9 (all white).
  `reel_captions.py --donor-track N --all-white` (new) clones that track and uses the cool
  prototype for both speakers; ownership still comes from the mics so nothing is dropped.
* **A timer is a text track.** One card per second, `mm:ss` in Assistant-Bold (bamberger has
  no digits) on a black box at the top right (x 0.62, y 0.80); plus an SRT of the timer and of
  the reel's captions relative to the reel start, so she can quote a time from either. Word
  fixes go into the words cache before `--reuse` (הטניה→הפרויקט T2, חבדניקית→חב״דניקית,
  היעצה→היצר, ויעשר→והסר, «ולפנצ ר»→«ולפנצ׳ר»); the prefix-join list now includes «ה» for «ה-14».

## What Alon's own pass over 0922 corrected (22.09.26) — rules, not preferences

Read off the diff between my write and his save (`draft_info.json` vs the last `ccstudio-backup`):

* **Every moving keyframe has ease.** His keys are `CurveInOut` (497) / `FreeCurveInOut` (45), the first
  key of a move `CurveIn`; `Line` only on holds. My cutaway boundary keys and b-roll keys were `Line` —
  "שים לב שהם תמיד צריכים להיות עם ease". `reel_cutaways.py`, `reel_broll.py`, `reel_ripple.py` write
  eased keys; a pair of keys with a value change and `Line` on either end is a defect.
* **Silences inside a reel get cut.** Reel 3 became five pieces: pauses of 0.5–1.2 s removed whole, the
  cut landing inside the silence (src 73.383–74.367, 76.85–77.5, 103.667–104.667, 107.35–108.05,
  125.817–126.3), plus 0.28 s off the head. Reel 1 −0.98 s, reel 4 −1.2 s. `reel_ripple.py --cuts` does
  this from the both-mics-quiet pauses (≥ 0.5 s → ≈ 0.25 s left).
* **Both layers at volume 1 doubles the guest.** With the channels gain-baked (+17…+26 dB), the guest's
  bleed in the host's mic sits 1 dB under the guest's own mic, a few ms late — a comb filter ("משהו
  במיקרופון של מצלמה 2 ממש מוזר, כאילו לא שומעים ממנו"). `copies_audio_gate.py` re-masters both copies
  in one continuous encode: each camera's audio carries its own speaker (mic ownership by 6 dB margin,
  hysteresis), the other at −30 dB, room tone kept. The delivery format is unchanged (both segments at 1).
* **A hook title over the reel's opening**: he added «האם כדאי לוותר על\nהמחיר למשתכן?» on reel 3's first
  4.55 s — system font, size 15, scale 1.33, `y +0.6875` (top), with a text animation. Clone his segment
  for the same device on another reel (done on reel 5). He deleted the framed gov.il page card.
* **SFX on a b-roll entry**: a library «click (camera shutter)» at 0.55 on the stalled-lot clip. Clone the
  segment for other b-roll entries when he has started the pattern; otherwise none.
* **Beds**: he swapped R1/R2 to tracks of his own and set 0.14 / 0.065 / kept 0.16 — the brand library is
  the default, not the decision; default level 0.14.
* **Titles wrap by rendered width, not characters** — he put the 31-char title back on one line at size 25.
* **Captions**: question marks stay on questions (`--keep-punct` for `?`), «אני ממליץ», «אליך», «אז ברגע
  שהצלחת» — the second decode + context pass would have caught two of these.


## The premium layer (0923, 23.09.26) — what "premium" meant once the cadence was already right

Measure the cadence first; if events/min and median shot are inside the reference band, more motion is not
the answer (v2.1 lesson). Premium = the layer every reference has and a podcast cut does not: one huge keyword
in the brand accent where the face isn't, a hook on the face inside 3 s, a name card, the spoken CTA as a
super, the *real product* framed (his own exported reels, never generic b-roll, never a raw screen), a
click/swoosh on every graphic, the bed ducked under inserts, and a compressed voice at −16 LUFS / LRA ≈ 3.
One accent colour (Bunker `#d01020`, read off the logo PNGs), everything else white. Supers ≤ 860 px, one line.
A caption under a super keeps white — one device per moment. Numbered items are bare words (RTL bidi).
Before reporting captions "done": scan for gaps > 1.5 s with a loud mic — 0923 hid seven seconds of speech.


## What Alon corrected on the premium layer (0923 round 2, 23.09.26) — these override the section above

1. **Titles in a reel: the hook only.** «הכותרות זוועה בפורמט רילס … כותרת רק כחלק מההוק, לא יותר מזה». No keyword
   supers, no name cards, no CTA supers. `reel_supers.py` runs with a hooks-only plan (one per reel, ≤ 3.4 s,
   on the intro zoom-out). The keyword colour inside captions stays (it is a caption, not a title).
2. **B-roll: more, and short.** «קאטים קצרים יותר של עד 3 שניות כדי לתפוס את העין» — every piece ≤ 3 s, ≈ 1 per 13 s.
   New material goes to `~/VideoAssets/בירולס לרילס 2026/` (his drop folder; the old «בירולס שלי»
   is dated). Read the folder first on every reel job.
3. **Something comic when the words are comic.** «חייב שיהיה משהו קצת קומי» — an AI clip/still per comic image in
   the script (Higgsfield); with no credits, an emoji pop beside the head (`reel_broll.py` overlay item + `Pop.mp3`).
4. **Logo = the real brand file** (`02 לוגו הבונקר/BUNJER PODCARST_Logo_HEB_2.png`, white wordmark on dark), as a
   LOCAL photo material — never a clone of the online white-card material (CapCut re-links it → white box).
5. **Music: young, rhythmic beats** — trap_hype / gritty_hiphop / funk_groove from the brand library, not
   corporate/inspiring/motivational. «מוזיקה ממש לא מתאימה, יותר ביטים קצביים וצעירים». Outside the brand
   library, take beds only from the safe Pixabay library (folders 8 energy / 13 dark beats for this taste;
   `קטלוג.csv`, see talking-head-promo.md «Safe library»), never commercial songs.
6. **Transcription: infer from the sentence** when he mumbles («רואי חשבון» not «אורי חשבון», «לשרוף זמן שיחה»,
   «איך העסק שלך נראה», «השמין», «מביך», «לסשן»). Second decode + sentence sense, then fix.
7. **Audio QA = render the mix.** `reel_audio_mix.py` per reel: peak, clipping, silences, dead bed ends, files read
   past their end. A click on a loud word can clip the sum — clicks at 0.35, no two hits inside 0.6 s.


## Alon's round-3 notes on 0923 (23.09.26) — now rules

* **No silent card.** The bed starts under the white card (`reel_music.py` spans from the card start).
* **One visual event per cut.** A punch that holds < 2.5 s, a partial ramp at a cut, an angle switch 0.1–0.3 s after
  a jump cut — all read as «קפיצה מוזרה, מעבר מהיר וחזרה». `reel_cut_polish.py` (two sizes, hold ≥ 2.5 s, every
  jump cut changes size, short pieces keep the size) and `reel_polish.py --align-angle-cuts`.
* **Pauses: cut to ≈ 0.25 s and make the cut elegant** (size change / angle / b-roll). `reel_pauses.py --floor -30
  --min 0.45 --keep 0.12` after the compressor (the floor rises with compression; −45 finds nothing).
* **A choke / cough is a cut** — find it by energy between words (0923: 3:18.6–3:18.8).
* **Captions split after `. ? !`** — `reel_caption_punct_split.py`. **No colour change inside a caption** (he called it
  «מציק בעין»); a keyword is either an animated title or nothing.
* **Numbered lists get a badge and numbered titles** («3» icon when he says «שלושה טיפים», then «1 עוגנים» …) —
  PNGs drawn locally (Hebrew in VISUAL order: this PIL has no raqm), overlay items in `reel_broll.py`.
* **Wide b-roll stays wide.** A 16:9 clip goes in at 1920×1080 with `cover` scale and an `x` pan onto the subject, so
  he can drag it in CapCut («שתהיה לי אפשרות לשחק עם המיקומים»). Never crop it in ffmpeg.
* **No near-duplicate b-roll within a minute** (1:20 — a guest-at-desk clip nine seconds after another).
* **«תשאירו פרטים» = his down arrow** (`חץ לבן.png`) under the logo with a pop.
* **Comic script images get Higgsfield.** The claude.ai Higgsfield MCP was out of credits; the API-key MCP
  (`mcp__higgsfield__generate_image_soul` 960×1696 + `generate_video_dop`) worked — Soul stills + DOP animation,
  5.4 s 720×1264 clips, encoded to 1080×1920 pieces.
* **Upload folder:** `~/VideoAssets/בירולס לרילס 2026/` (opened in Finder for him).

## His own footage beats stock, framed reels and generated scenes (0923 round 4)

When Alon says the b-roll is «לא מדויק» the fix is a folder of his current material, catalogued and picked by
eye, one clip per sentence, ≤ 3 s. On 0923 the 2026 Bunker footage (door with the logo, the set, guests at
the mics, the camera monitor, the multicam TV, a reel on a phone) replaced every stock/old clip and every
framed reel insert; only the overlay graphics and the two Higgsfield comic clips stayed. iPhone HDR must be
tone-mapped (`broll_cut.py`) or it renders grey. Extra cuts go on literal sentences only («רואי חשבון» → the
guest in a blazer, «צעירים» → the laughing kid at the mic, «עדויות» → a client watching the two-guest video).


## Voice cleanup — the approved chain (לקוחה D course, 16.11.26: «מושלם! זה הסאונד»)

Three rounds on one 86-minute single-speaker course: (1) highpass 80 + afftdn + presence +2 dB → «חסר בשר»;
(2) body +3 dB @180, −1.5 @3 k, HP 60 → «יותר טוב אבל עדיין יש קצת אקו»; (3) WPE + DeepFilterNet3 before
the chain + a gentle expander → approved. `scripts/voice_clean.py` is round 3, end to end.

* **Dereverb first, on the raw source** — WPE (taps 40, delay 2, 5 it.) then DeepFilterNet3, *before* any
  compression (a compressor lifts the tail that WPE needs to see). Then no `afftdn`.
* **Expander, not gate:** 2:1, range −10 dB, threshold 0.03 — the tail drops, the words keep their ends.
* **Body:** +3 dB @180 Hz Q0.8, −1.5 dB @3 kHz. No presence lift.
* **Two sources, one voice:** takes that only have the broadcast/camera sound get a FIR tone match to the
  same speaker's mic takes (1/3-octave long-term spectra on speech frames, ±6 dB, smoothed) — `--match`.
* **Sync is part of the chain:** afftdn delayed the voice 25 ms, the FIR 10 ms, WPE+DFN 17–28 ms. The script
  cross-correlates with the source and trims; residual must print 0.00 ms. A voice track 25 ms late was
  shipped once before anyone measured.
* Numbers vs round 2 on the same 30 s: tail 80–200 ms after a word −4 dB, pauses −17 dB. Send Alon a 15 s
  before/after file per source type; he decides by ear.

### Long-form lesson cuts (לקוחה D simulator r5, 17.11.2026)
Silence-cutting a lecture: don't cut every 0.3 s pause — Alon: «יותר מדיי חיתוכים… פייד רק כשיש קאט ארוך». Cut pauses > 0.45 s (keep 0.08/0.14 s air), skip any cut that saves < 0.35 s, let fragments < 1 s rejoin their neighbour across gaps < 0.9 s, and put a Mix dissolve only where ≥ 1.5 s of source was removed (plus take/card joins). ≈8 cuts/min. Warmth = clip Adjust › Temperature (`materials.effects` type `temperature`, value + = warmer) on camera shots only.
