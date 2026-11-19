# What broke, and what it cost

Every entry here happened. They are ordered by how much damage they did.

## The colour that was never there

Nine captions were written yellow — `fill: [0.957, 0.78, 0.059]`,
`text_color: "#f4c70f"` — and rendered **white**, in both projects, through two
rounds in which I reported "9 צהובות ✓". The caption style carries a CapCut text
effect, and with an effect applied CapCut ignores `fill` unless the style also
sets `useLetterColor: true`. My template was a white caption, where the effect's
default colour *is* white, so nothing looked wrong.

Alon found it by looking at the screen. I had "verified" it by counting JSON.

**Rule: a visual change is not verified until you have rendered the pixels.**
Diff the finished material field-for-field against something the user made by
hand in CapCut. That diff is what finally proved it.

## Corrections compound, and nothing was bounding them

Three separate passes raised shot scales for good reasons — clear the chin,
clear it again after a second measurement, add a push-in to a shot that had
none. Each was individually right. Each check that could have caught the result
was *relative*: amplitude ≤13% of the shot's own start. Nothing was absolute, so
the floor kept climbing and one shot reached **3.83 — 26% of the source width**,
a head filling the frame. Alon pointed at it on screen.

**Rule: bound every shot between a floor and a ceiling, both derived from the
same caption band.** The floor is what that shot's own chin needs; the ceiling
is the tightest scale at which *every* face in the reel still clears the band —
sweep candidates against the face scan and take the smallest with zero
overlaps. Rebuild the shot between those two numbers rather than nudging what
is already there; nudges are what compounded in the first place.

Two tails that follow: clamp keyframes sitting in **hidden** stretches too (they
anchor the interpolation into the visible part), and give the top pin ~0.6px of
slack — `y = PIN·s − 1` puts the bottom edge on exactly 1920 and rounding shows
a one-pixel black line.

## A cloned keyframe carries a cloned id, and CapCut collapses them

The natural way to insert a keyframe is `copy.deepcopy` of a neighbour — it
carries every field you would otherwise have to guess. It also carries the
**`id`**, and 176 keyframes ended up sharing three ids between them.

Nothing looked wrong. The draft verified clean: 0 black frames, 0 structural
problems, four rendered stills. Then CapCut opened the project, the user made an
ordinary trim, and CapCut wrote the draft back — **collapsing every keyframe
that shared an id onto one timestamp**. One curve went

```
(222.13, 3.745), (224.60, 3.160), (241.87, 0.084) ×18, (245.20, 3.485)
```

Scale 0.084 is an invisible image: twenty-one seconds of fully black reel, plus
nine smaller black bands where `ScaleY` kept a keyframe that `PositionY` had
lost, so the two stopped agreeing and the frame no longer covered the canvas.

**Rule: every keyframe you create gets a fresh `id` (uuid4, upper case), and so
does every `common_keyframes` entry.** Assert it before writing — count distinct
ids against total keyframes.

**Rule: the file you verified is not the file that renders.** CapCut rewrites
the draft on its own terms the moment it opens it. Re-run the checks after
CapCut has saved at least once, not only after your own write.

The repair was cheap for one reason worth remembering: **`time_offset` is source
time, so a ripple trim does not move it.** That makes the good version's
geometry re-mappable onto an edited timeline segment by segment — evaluate the
old curve at the new source in/out, keep every interior key, and the shape
survives the user's edit intact.

## Twenty-five seconds of half-black reel, past four audits

A pass that widened all eleven split screens by 3% multiplied **every** keyframe
inside each window — including the boundary keyframe that was supposed to hold
the return to full frame. Each split's exit stopped being a cut. Instead the
base layer ramped from half-height to full over the 2–3 seconds until the next
keyframe, while the other half's segment had already ended: a shrinking image
over a black bottom half, eleven times, ~25 seconds of the reel.

It survived a face-overlap audit (334 frames, 0 overlaps), a gap/overlap audit
(0 problems) and four rendered stills, because none of them asked the one
question that mattered. Alon found it by pressing play.

**Rule: check that the canvas is filled — on the real frame grid.** Step the
timeline by exactly `1e6/60` µs, evaluate each visible layer's covered span from
its own keyframes, union them, and assert the union is `[0, 1920]`. On an
arbitrary sampling grid you get the opposite failure: samples land mid-ramp
between two keyframes a frame apart and report slivers of black that never
render. Skip image materials — a card is not `607.5·s` tall and reads as a false
positive.

**And: a bulk multiply must exclude the boundary keyframes of the window it is
scaling.** Anything that is a *cut* is stored as two keyframes a frame apart;
scale both and the cut becomes a ramp.

## CapCut wrote a stale project back over a fresh rebuild

A re-cut changed every highlight's range, so the whole draft was rebuilt from
scratch — new work copies, new timeline, 8:18 → 10:14. CapCut was **open on the
old project the whole time**. It never noticed the folder had been replaced
underneath it, and when it next saved it wrote its in-memory 8:18 timeline back
out. What survived was a chimera: an old edit whose `source_timerange`s pointed
into media files that had since been re-encoded to different ranges. Nothing
errored. The draft opened fine and played the wrong seconds.

The open-files check protects a *write*, but it does not protect the minutes
after it. **A rebuild is not a write — it is a session.** Before a `--force`
rebuild, confirm CapCut is not running at all (`_capcut_pid() is None`), and
keep it closed until the last step lands; a chain that only re-checks the lock
per step will happily interleave with CapCut's own save. Say so out loud to the
user when a long chain starts, because the failure is silent and expensive.

## The exchange rule degenerated into a 71% split screen

"Collapse an exchange into one split" is written for a conversation that
alternates a few times a minute. On צומת 20 the routing produced 87 cuts in 8
minutes, so the same detector found **52 exchanges whose merged spans covered
71% of the footage** — a reel that is mostly split screen, which is the opposite
of "split screen earns its place."

The hold rule (`≥9s on one camera → split its middle`) did not degenerate: 12
windows, 42 seconds, 9% of the reel. **A rule tuned on one episode's rhythm is
not a constant.** Compute what the rule would produce as a *fraction of the
reel* before applying it, and if that fraction is absurd, apply the part that
still holds and say why you dropped the rest.

## Who goes on top of a split is decided by the faces

The instinct is host-on-top. The constraint is the caption band: the lower
half's head must start *below* it, and the amount of extra scale that costs
depends on how high that person's head already sits in their own angle. On this
episode the guest's head starts at 0.173 of the source and the host's at 0.266,
so putting the **guest on top** needed s = 1.58 against s = 3.22 the other way
round — the difference between a natural half-frame and a head jammed into the
bottom edge. Derive the order from the face scan, per episode.

And check the brand layer against the same band. The two logos sit at 0.715,
which is empty chest in a full-frame shot and **squarely on the lower speaker's
face** in a split. Faces beat logos: cut the logo segments around each split
window rather than moving the face.

## A cut keyframe on the wrong grid

The split's hard cut is two keyframes one frame apart, written as
`w0 - 33333` and `w0`. At 30fps the real frame period is 33333.**33** µs, so
after a few seconds the rendered frames drift off those timestamps and one
lands *between* the pair — reading a half-way interpolated scale, which at a
split boundary is a frame with black at the top. One frame in 14,950.

**Rule: snap every cut keyframe to the real frame grid** — `round(t / (1e6/fps))
* (1e6/fps)` — and place its partner at the previous grid index, not at
`t - floor(period)`.

## Routing the picture deleted half the sound

Camera 2 had been laid across every clip end to end at `alpha 0` — invisible, but
audible, which is what carried the guest's microphone. Multicam routing then
replaced that with discrete segments only where camera 2 is *seen*. The picture
was right. But camera 2's audio now existed only where camera 2 existed, so
**102 seconds of the guest's voice disappeared** — precisely the stretches where
the host was on screen, i.e. the reaction shots, where you are least likely to
notice the missing voice because you are watching a face that is not talking.

Opacity and volume are independent in CapCut, and that is the whole solution:
keep the full-coverage layer for sound at `alpha 0, volume 1`, and set the routed
visible segments to `volume 0`.

**Rule: after any pass that changes which segments exist, re-assert audible
coverage per speaker.** Sum each camera's `volume > 0` duration and require them
equal. A visual edit is allowed to change what is seen; it is never allowed to
change what is heard.

## A negative `-ss`, silently clamped to zero

A sync harness read each mic window with a half-second of lead — `ss = src − S`
— which is fine everywhere except at a clip's own start, where `src` is 0 and
`ss` goes negative. ffmpeg does not fail on that; it clamps to 0 and returns
audio starting half a second late. The correlation then reported **exactly
−99.9 ms on all thirteen standalone clips** while the seven clips with a nonzero
`src` read 0.0. Two consistent, confident populations, and the data was fine —
only the probe was broken.

The tell was the split itself: a real capture problem does not respect whether a
segment happens to start at source 0. **When one population of a measurement is
clean and another is uniformly offset, suspect the measurement before the
material** — and assert `ss >= 0` in any function that seeks with a lead.

## Restoring a backup by filename

A rollback restored two drafts "by filename". The backup rotation had already
deleted one of the named files, so that restore raised — and the other ran on
already-processed data and **emptied a whole camera layer**.

**Rule: restore by SHAPE** (this draft has 5 segments on video track 1 and zero
keyframes), never by name, and assert the shape after restoring.

## A caption shift that was itself the bug

Reel 1's captions looked 5s late in one of two twin projects, so I shifted them
−5s *in that project only*. The shift was wrong in both direction and target: it
put the ending line 9 seconds before the reel ended, crushed cards to 0.08s, and
orphaned five of them onto a stray track. Worse, the speaker-colour pass reads
the mics **by the caption's position on the timeline**, so every colour in reel 1
was then computed from the wrong five seconds of audio.

**Rule: twin projects are mirrored from one master, never edited in parallel.**
And a "fix" applied to one copy of a pair is a bug in waiting.

## Silent restore, silent skip

The first colour pass skipped every caption whose stored word-token count did not
match its word count — `continue`, no counter, no message. Those captions stayed
white and nobody knew.

**Rule: count what you skip and print it.** A pass that reports only successes
is reporting nothing.

## Reading the mic at the wrong minute

A work copy's frame 0 is not the recording's second 0. A script that used
`source_timerange.start` as an absolute audio position on the work-copy project
happily analysed the wrong minute of the episode and produced twelve confident,
nonsense camera cuts — including cuts on title cards.

**Rule: absolute audio time = the work copy's own start + `source_timerange.start`.**
Keep the map of copy → absolute start next to the draft.

## Keyframes that pointed nowhere

`time_offset` is in SOURCE time. Hand-built 0-based keyframes silently do
nothing. Separately, a property whose first keyframe sits mid-clip holds that
value from the clip's start — which is how a split-screen position leaked
backwards over an entire shot.

## The cut that ramped instead of cutting

A camera-2 push-in ended with a keyframe at exactly the split screen's start,
and the split wrote its own keyframe at the same timestamp. De-duplication kept
the last one, so the shot ramped smoothly *down* into the split instead of
pushing in. Put the outgoing keyframe one frame earlier.

## Both projects, drifting apart

Two projects with the same content were edited by separate scripts and drifted:
different caption timings, different colours, different cut lists. Every later
"fix" had to be applied twice and one of them was always wrong.

**Rule: one master, mirrored.** The mirror rewrites tracks 0, 1 and all text
tracks from the master, remapping `source_timerange` and every keyframe
`time_offset` by the per-clip offset.

## Deleting a project that would not delete

Removing a project's entry from `root_meta_info.json` hides it until CapCut
rescans the drafts directory — which is immediately. Move the folder out.

Likewise the project name: CapCut re-derives `draft_name` from the folder name
on every save, so writing the name into the meta files reverts. Rename the
folder.

## "62 missing files"

CapCut portablises media that lives inside the draft folder to
`##_draftpath_placeholder_<uuid>_##/name.mp4`. A plain `os.path.exists` on that
string reports every clip missing. Resolve the prefix to the draft folder first.

## ffmpeg previews that come out black

`-ss` before `-i` does not always reset PTS to 0 across inputs, so an `overlay`
composite can produce its first frame before any video frame has arrived —
solid black, silently. Add `setpts=PTS-STARTPTS` to every scaled input, and pass
`-update 1` with `-frames:v 1` when writing a single PNG.

## A caption that wrapped itself, and orphaned a letter

The chunker capped cards at 34 **characters**. Character counts do not predict
rendered width, so a card overflowed `line_max_width`, CapCut wrapped it on its
own, and it rendered as «משקיעים היא מאוד פשוט» with a lone «ה» beneath.
Nothing in the JSON looked wrong — the text was one string with one style.

**Rule: measure the pixels, and split the card rather than let CapCut wrap.**
Two lines are a decision you make for a two-speaker card, never a fallback.

## Terms cut in half

Chunking by word count happily ends a card on «מלווה» and opens the next with
«משקיעים». The reader loses the term for a beat and the caption reads as a
mistake. Keep a per-episode list of multi-word terms and treat each as one
token before chunking.

## The caption that sat on the jaw

The caption position came from the donor template — `transform.y = -0.1438`,
centre 0.572, band 0.549-0.595. Measured on the finished canvas, the median chin
across the full-frame shots is 0.548 and the lowest is 0.591: the caption's top
edge and the chin were the same line. It looked deliberate in the JSON and wrong
on every close-up.

**Rule: derive the caption height from the faces, per project.** And check both
faces — a split screen has a second one low in the frame, and the band that
clears one covers the other.

The first fix gave the split captions their own y. Alon rejected it: a caption
that moves makes the eye chase it. **Move the frame, not the caption** — scale
the split halves until the faces clear the one fixed band. Which also exposed
that the split's `transform.y` was a constant ±0.5 while its scale was
keyframed, so both halves were drifting off the seam during the push-in.

The *second* fix moved the wrong frame. Cropping the split halves harder (1.58 →
up to 2.17) did clear the faces, but it paid for a low caption by squeezing the
one shot type where both faces are already small. Alon asked the question that
inverts it: can the caption go **up**, and the speakers move instead? Yes — and
it is strictly better. Lifting the full-frame shots to the top pin costs 1–11%
scale nobody can see, and once the band moves up to 0.551–0.597 the split needs
no extra crop at all. **Lift the full-frame shots first; the split is the last
thing you should be paying with.**

He also demonstrated it rather than described it: two captions dragged to
`Y = -283` and a clip dragged to the top of the canvas, saved into the project
between two of my runs. Read the draft before assuming your last write is the
whole story — the answer was already in the file.

## Hebrew in `drawtext`

ffmpeg has no bidi shaping, so a Hebrew preview renders reversed. Fine for
checking colour and framing — say so when you show it, and never use it to check
wording.

## The lock that locks you out

`capcut.draft_locked()` treats a recently-modified draft as CapCut's doing, so it
returns True for a draft *you* just wrote. `capcut._atomic_write` refuses while
CapCut runs at all, even on a different project. Use the open-files check and
your own writer — but never weaken the real rule: do not write a draft CapCut
has open.

## When the client re-cuts your project

He will. He rearranged a teaser and the project came back 32 main segments
instead of 41, 442s instead of 614s, 349 captions instead of 476 — spread over
five caption tracks, because CapCut splits a track wherever it ripples one.

**Rebuild the captions; do not patch the holes.** The word list is keyed to
*timeline* time, so every second of it is stale the moment he moves a clip. Run
the timeline audio again from the live draft, transcribe each mic again, and
regenerate. It costs ~5 minutes and it is the only version that agrees with the
cut. Before you do, prove he did not hand-edit any caption text: compare the
surviving texts against the set you generated last time. All 349 were verbatim
mine, so a rebuild lost nothing. Had any been his, they would have to be kept.

Three things break in his edit that have nothing to do with captions, and none
of them announce themselves:

* **The tail.** The adjust/LUT track still spanned the old 614s, so `duration`
  stayed 614s and the export would have carried 2:52 of black. Any full-timeline
  layer will do this. Trim every track to the main track's end and set
  `duration` from it.
* **The keyframe grid.** CapCut re-quantised keyframes to round numbers —
  a split exit landed on 369.440000 while the top half ends at 369.466666, the
  real 30fps frame. For exactly one frame the top half was gone and the bottom
  half had not yet jumped back: 160px of black across the top. Re-snap every
  keyframe to `round(t/(1e6/30))·(1e6/30)` in *target* time after any edit of
  his — 758 of 882 keys were off-grid.
* **His own gaps.** Two holes on the main track (2.27s and 1.20s) that render
  black. Report them; do not close them. Closing means rippling, and rippling
  moves everything you just built.

## A word that straddles a cut belongs to the louder half

Chunking asks which clip a word is in. "Where it starts" drops words: a word
beginning 0.37s before the cut gets clamped to the tail of the outgoing clip,
falls under the minimum duration, and vanishes — that is how «הטירונות»,
«הייתי» and «בארץ» disappeared from the top of five clips.

"Its midpoint" is better and still wrong at a speaker change. «AI» spanned
26.26–26.82 across a cut at 26.63; the first half is the outgoing speaker's
breath on the *other* mic, only the second half is the word. The midpoint put it
in the outgoing clip, where its own mic is at −59dB — and the
hallucination-on-silence filter then deleted it as a ghost, correctly, for the
wrong window.

**Decide by where the owner mic's energy sits.** Split the word at the cut,
integrate its own mic on each side, keep it where the sound is.

And once each word is in the right clip: the first caption of a clip starts
**with** the clip. Otherwise every cut opens a 0.4–1.4s hole and the caption
blinks off and on at each transition — which is the same note Alon gave about
gaps, just at a scale you only see when you measure it.

## The gate that failed a clean project

`qa25.py` came back with 16 failures on a reel that had just passed a ten-check
verification, and every one of them was the script describing the אורח G
build rather than the project in front of it. Worth knowing because the same
trap catches any harness that outlives the convention it was written against:

* **It sampled at 60fps a project shot at 30.** An off-grid sample lands
  mid-ramp, so it reported 286 black frames that do not exist — the exact
  mistake the skill warns about, inside the tool meant to catch it. Read `fps`
  from the draft.
* **It addressed tracks by index.** `vt[1]` was the visible camera when it was
  written; since camera 2's audio moved into a silent full-coverage layer,
  `vt[1]` is that silent layer, and every check built on it — colour vs camera,
  coverage, motion — measured a track nobody can see.
* **It assumed the base track is camera 1.** True there, inverted on אורח O. Read
  the camera off the work-copy filename and skip the check when you cannot.
* **It assumed the top half of a split is the base track**, so all 28 halves
  read as "not pinned to the seam". Infer the side from the sign of the y that
  is actually in the file.
* **It demanded both halves share a scale.** They deliberately don't — each
  half is scaled for its own head (1.5802 top, 1.65 bottom).
* **It detected splits only from keyframes**, and the halves whose y is a static
  `clip.transform` came back as zero splits — after which the same halves were
  flagged as full-frame shots that had lost their scale.
* **It called a 3s title card a caption**, because its "a headline is longer
  than 3.5s" heuristic predates the 3s cards. Position beats duration: text
  sitting on a card is a title.
* **Its zoom ceiling was a constant.** 3.55 was *measured* on one episode. It is
  a parameter, not a law.

A gate whose failures you learn to ignore is worse than no gate. When a check
fires on work you have verified by other means, fix the check — or make it say
"not checked" — before the next run teaches you to skim past a real one.

## A composite that agreed with itself and disagreed with CapCut

On אורח P אלון I built the check-frame renderer from the geometry in
`capcut-json.md`, rendered the two split sections, measured the seam — 0.364 of
frame height — and it was wrong. CapCut's own `draft_cover.jpg` put it at
0.4986, and the horizontal guide Alon had dragged into
`attachment_pc_common.json` put it at 0.5126.

The cause was a field the geometry section never mentioned: each `materials.videos[]`
entry carried its own **`crop`** (here a 1:1 window on the 16:9 frame). I was
computing the rendered size from the crop but clamping the canvas→source mapping
to the *file's* bounds, so the render happily filled the canvas with 130px of
material that CapCut hides. Everything downstream inherited it — the face scan
that decides the caption band was measuring a frame that does not exist.

Three lessons, in the order they cost time:

1. **Check the sign before the maths.** I first assumed +y is down, and the split
   arrangement (white shirt on top, bald man below) is what proved it is up.
   Both signs produce a clean seam — the seam is symmetric, so it cannot
   disambiguate. What disambiguates is *which person* ends up on top.
2. **The draft folder ships its own ground truth.** `draft_cover.jpg` is a frame
   CapCut rendered; `reference_lines_config.horizontal_lines` is where the editor
   snapped a guide. Compare the strongest row gradient in your composite against
   the cover before believing a single number you derived.
3. **`scripts/face_scan.py` returns "0 faces" instead of an error** when the
   materials point outside the draft folder — it resolves every path to a work
   copy inside it, and on a project cut straight off the external drive that
   resolves to nothing. Zero faces is not "the shot has no face".

## Two transcripts, one timeline

Transcribing each mic separately is right (see SKILL.md), but merging them is
where the reel gets damaged, and the obvious merge is the wrong one.

**What failed:** slicing the timeline into speaker regions from the energy
envelope and taking each region's words from its owner. It reads as the
principled version and it deletes real speech: the interviewer's «אוקיי» dropped
in the middle of the expert's sentence owns a 0.3s region, and that region
swallowed «והם משלמים» from the channel that actually said it. The reel lost two
words and gained nothing.

**What works:** decide ownership **per word** — the mic whose energy is higher
across that word's span keeps it, the other channel's copy is discarded — then
sort by time. Two guards make it clean:

* **Throw away zero-length words first.** The model emits `26.20 → 26.20`
  artefacts, and a zero-length word wins comparisons it should not, then sorts
  ahead of a real word and scrambles the sentence («משלמים הם הרבה»).
* **Dedupe the same token heard on both channels.** If two adjacent words have
  different owners and identical text, one of them is bleed — keep the one whose
  energy ratio is stronger. That is what collapsed a doubled «מטורף מטורף» into
  one card.

Sanity-check the merge by reading the merged text end to end, not by counting
words. Word order is where this fails, and a count will never show it.

## The orphan at the end of the run

Chunking greedily — fill three words, start a new card, repeat — is how every
version of this started, and it produces a card holding a single word torn off
the phrase before it: «באה ואומרת דבר» + «כזה», «לאנשים בני 60» + «פלוס»,
«את התשלומים למס» + «השבח». Alon caught all three in one screenshot.

Break the words into runs at real boundaries only (speaker, cut, a pause over
~0.25s), then partition each run with a DP that scores a card
`(max_words − words)²` and minimises the total. It turns 3+1 into 2+2 and
3+3+1 into 3+2+2 for free, and the width, duration and max-word limits go in as
feasibility constraints so every partition it returns is already legal. The
same pass is where the term list earns its keep: «למס השבח» and «אלפי שקלים» are
one token each, so no partition can break them.

The other half of the same complaint is the pause. Two words together and the
third arriving half a second later is not a card, it is a card that outstayed
its line — measure the internal gaps of what you produced (five cards on this
reel exceeded 0.35s) and break them.

## Captions that flicker: microsecond times on a frame grid

Alon opened «המלצות הבונקר» and said the new captions had "הרבה מרווחים בין
כתוביות". They had none when I wrote them — every card ended exactly where the
next began. What he saw was real anyway.

CapCut stores `target_timerange` in microseconds but **re-rounds each segment to
the project's frame grid, independently**: `start` rounds one way, the previous
card's `start + duration` rounds the other, and a one-frame hole opens between
them. On a 60fps project that is 16.7ms of nothing, and over ninety consecutive
cards it reads as the captions blinking. His own CapCut-generated captions never
show it because CapCut authored them on the grid to begin with.

Snap before you write, and snap the *shared* edge to one number:

```python
FR = 1_000_000 / draft["fps"]
snap = lambda t: int(round(t * 1e6 / FR) * FR)
for c in cards: c["si"], c["ei"] = snap(c["start"]), snap(c["end"])
for c, nxt in zip(cards, cards[1:]):
    if same_clip(c, nxt) and abs(nxt["si"] - c["ei"]) <= FR * 1.5:
        c["ei"] = nxt["si"]        # one number, not two that round to neighbours
```

Verify with `abs(t*fps/1e6 - round(...)) > 0.02`, not with `t % round(FR)` — at
60fps the frame is 16666.67µs, so a modulo against the rounded integer flags
every correct value as wrong and you will "fix" what was already right.

## Where a caption may break: the transcriber will not tell you

The other half of the same complaint was «חוסר דיוק בחלוקת המילים» — cards like
«והשקיע בי כמו / שהוא היה / משקיע בעצמו». The obvious fix is to prefer breaking
where the speaker paused, so I scored each candidate break by the gap between
one word's `end_s` and the next word's `start_s`.

That gap is **always zero**. `ivrit-ai`/Whisper hands out word intervals that
touch: the median measured gap at 80 break points was 0.00s. The signal was
carrying no information at all and the DP was effectively breaking at random.

The honest measure is acoustic — the energy actually dipping at the boundary:

```python
env = rms per 20ms; db = 20*log10(env); speech = percentile(db[db>-60], 70)
dip(t0, t1) = clip((speech - db[t0-0.05 : t1+0.05].min()) / 18, 0, 1)
cost += 20 * (1 - dip(...))
```

That took the median dip at a break from ~0 to 0.63 and the cards started
landing on phrase boundaries. Two word lists finish the job, because Hebrew
gives no morphological cue: words that lean **forward** (של, את, עם, כמו, כי,
מה, הכי, חוץ…) may not end a card, and words that lean **back** (אותי, לו, בי,
שלהם…) may not start one. Twelve points each, against twenty for a missing
pause — a bad break survives only when every alternative is worse.

And glue the fixed phrases before chunking, as always: «לב טוב», «דרך ארץ»,
«מה שנקרא», «וחוץ מזה», «מגבעת שמואל». No cost function will discover them.

## The routing that took the edit out of his hands

The build laid one segment per shot on one track: camera 1 where camera 1 speaks,
camera 2 where camera 2 speaks, nothing else. Every frame on screen was correct
and the project was still wrong, because the second angle no longer existed
anywhere Alon could reach it. Changing any one of my 128 decisions meant coming
back to me.

What he asked for instead — *"איפשרת לראות את שתי הרצועות לאורך כל הדרך, עם
עריכה של השקיפות (100 / 0), הייתי רוצה שזה יעבוד גם באופן הזה מעכשיו והלאה"* —
is both angles across every reel range on two stacked tracks, with `clip.alpha`
0/1 per piece deciding who is seen. Correcting a cut becomes a slider.

Measured coverage of the upper layer: **98.9%** on אורח G, **93.9%** on
פרויקט-דוגמה N, **7.3%** on my build. That single number is now check 28, and it is
the difference between handing over an edit and handing over a decision.

The same shape had already caused the 102 lost seconds of guest audio (below):
routing by segment presence deletes whatever travels with the segment — the
picture *and* the sound. Full coverage on both layers fixes both at once.

## Four rounds, and nobody measured the horizontal

`transform.x` was 0 on all 128 shots. Nothing in the JSON looked wrong; x = 0
reads like "centred". It centres the *source*, and the source is a two-shot in
which neither person is in the middle. Rendered face centre, as a fraction of
canvas width:

| | camera 1 | camera 2 |
|---|---|---|
| Alon | 0.36–0.40 | 0.54–0.61 |
| the guest | 0.26–0.31 | **0.76–0.82** |

0.76–0.82 is a face against the right edge of the frame, and it survived a face
scan, a caption-overlap audit, a canvas-coverage audit and four rendered stills
— because every one of those measured the vertical. The house target (33–38% of
canvas width) had been written in SKILL.md the whole time.

Two lessons, and the second is the expensive one. Solve x from the same anchor
arithmetic as the eye line, and re-solve it at every scale. And: **a QA harness
that I wrote from the same assumptions as the builder is not a check.** Mine
reported 41/41 and then 44/44. The reel it was grading was rejected in the first
ten seconds of watching it.

## `attribute: 1` — the reels that had no sound at all

Four finished reels shipped silent. Every segment carried `volume: 1.0`, the
work copies had audio streams, the mic files were muxed correctly. The flag that
mattered was on the **track**: `attribute: 1` on a video track means muted, and
every video track in that project had it — including Alon's own, which is why
nothing looked unusual.

It also explains an earlier measurement that had confused a whole session: a
"constant 1.774 gain" between two ISO overlays that were, in fact, both muted.
Check the track flag before believing anything about a project's audio.

## A caption's length is set by the card after it

The chunker enforced a minimum duration per card and every card passed. The
shortest card on screen still lived **0.067s**, because captions are gap-free:
a card ends when the next one starts, so its on-screen life is decided by its
successor, not by itself. No amount of scoring inside the chunker can fix that.

The fix is a floor pass after chunking — merge anything under ~0.42s into a
same-speaker neighbour, or borrow time from one, then re-derive every timing.
Report the minimum and the median you ended with (0.42s and 1.15s on 561 cards);
"the captions flicker" is what those two numbers look like from the sofa.

## Filling the holes automatically made the transcript worse

Speech with no caption over it looks like a bug, so the build "rescued" it by
re-transcribing the uncovered windows with a looser threshold. What came back
was «מאוד לא מי אותם הצ זה» and «אז אולי את» — fragments that are worse than a
silent gap, because a viewer reads them.

Rescue is off by default now. Ten hand-verified words filled the two real holes,
and coverage against *speech-active* time (not wall time) came out at 98.9% with
one 0.84s window where the two mics genuinely disagree. Measure coverage against
speech, and let a hole stay a hole rather than filling it with noise.

## The instability was in my preview, not in the draft

Alon reported that the camera looked unstable. It did — in the MP4 I had
rendered for him. The preview scaled every frame to a per-frame size, landing on
odd pixel dimensions with an integer crop offset, so the picture shimmered:
0.44 units of frame-to-frame noise against 0.35 with the zoom disabled. The
draft was fine.

Render previews at 2×, round every dimension to an even number, downscale with
`lanczos`. And remember that `crop` evaluates `w`/`h` **once**, at configuration
time — there is no `eval=frame` for them, so a time-varying zoom has to live in
`scale=…:eval=frame` with only the offsets in `crop`.

Also burn the LUT and the caption outline/shadow into the preview. A preview
without them is a review of a different reel.

## A split screen in the middle of a monologue

49 splits, every one exactly 5.2s, 34% of screen time — against 11–20% in the
reels Alon cut himself. Two separate faults produced it:

* the hold-break rule ("any hold ≥9s gets a split in its middle") fired inside
  monologues, putting the silent listener on half the screen for five seconds at
  a time. A long hold on a talking face is a much smaller problem than that.
* the exchange rule, which is the one that *should* place splits, never fired
  once — because it looks for the 1→2→1 pattern, and it ran after the
  minimum-shot pass had already absorbed every short interjection. The pattern
  did not exist anywhere in the plan by the time the detector saw it.

Keep the raw turn boundaries from before absorption, rank candidate windows by
how many of them fall inside, and spend a budget instead of applying a rule.

And read the split's *composition* off the approved reel: filled halves pinned to
the seam and uncropped 16:9 halves at `scale 1.0` with black bands are both his,
on different projects, and they look nothing alike.

## `hash()` is salted, so the cache never hit

Transcription results were cached under filenames built from Python's `hash()`
of the window name. `PYTHONHASHSEED` is random per process, so every run wrote a
new cache file and re-transcribed everything — hours of it, silently. Use
`hashlib.md5(name.encode()).hexdigest()[:10]`.

The same run also taught a shell lesson: `rm -f /tmp/x/cap-a[12]-*.npy` with no
matching file is a **zsh** glob failure, which aborts the `&&` chain. The next
command never ran, I read a stale log, and concluded the transcription had
returned zero words.

## Nearly double the zoom, and every number looked normal

Camera 2 was written at `scale 3.3257` because that is what camera 1 uses and
because an earlier version of the project had that number on both. Alon:
*"אתה עושה זום אין גדול מדיי על מצלמה 2."*

The two angles are not comparable. Camera 1 is uncropped 16:9 and covers the
9:16 canvas at 3.1605; camera 2 carries a **square** material crop
`(0.3486,0.1038)-(0.8283,0.9566)` and covers it at **1.7778**. So 3.3257 on
camera 2 is 1.87× the covering scale — measured on faces:

| | head width | brow | chin |
|---|---|---|---|
| his camera 2 | 0.391 | 0.165 | 0.462 |
| mine, 3.3257 | **0.737** | **−0.155** (above the frame) | 0.396 |
| mine, 1.7953 | 0.397 | 0.148 | 0.444 |

`607.5·s` is the rendered height of *uncropped 16:9 only*. Compute the crop
rectangle, contain it, and compare rendered pixels. Six checks in `qa25.py`
were measuring through the 16:9 assumption and passed this project anyway,
because a too-tall material still covers the canvas — the failure is invisible
to a coverage test and obvious in one rendered frame.

## The split he actually cuts fills both halves

Mine stacked two uncropped 16:9 halves at `scale 1.0`: a black band between
them, another under the bottom one, and the host reduced to a 607px strip. His
fills each half — top `s=1.0` (the square crop, 1080×1080) at `y=+0.5076`,
bottom `s=1.881` at `y=−0.5694` — and lets them overlap ~78px at the seam,
which lands on the guide line he drew at 0.5126.

The lesson for the gate: "both halves pinned to the seam by `y = ±0.3164·s`" is
one composition of the two he uses, and it is only correct for 16:9 material.
The invariant that holds in every case is **no gap at the seam**, so that is
what check 11 measures now, and checks 10 and 12 measure the pair's time window
and whether the boundary is a segment edge — none of which assume which track
holds which half.

## Two black seconds that were his

`0810` came back with two 2s windows where no video segment exists at all, and
the obvious reading was a hole in my build. The audio tracks settle it: both mic
tracks are cut at exactly the same two points. They are the separators he put
between reels when he re-divided the project. Read the neighbouring tracks
before "fixing" a gap.

---

## הכתובית שהוארכה, ומיד נגזרה בחזרה

`reel_captions.py` הכיל את הכלל הנכון — *«כל כרטיס חי לפחות ~0.42s»* — בשורה
אחת: `if c["ei"] - c["si"] < FR * 12: c["ei"] = c["si"] + FR * 12`. שתי שורות
אחריה ישבה הלולאה שמונעת חפיפות: `if a["ei"] > b["si"]: a["ei"] = b["si"]`.
הראשונה האריכה, השנייה גזרה בדיוק את התוספת, ו-**126 מתוך 1598** כתוביות ירדו
מתחת לחצי שנייה — אחת מהן חיה 0.100 שניות, שלושה פריימים.

זה לא באג של סדר פעולות אלא של הבנה: **אורך הכרטיס נקבע על ידי הכרטיס הבא**,
כי הכתוביות חסרות מרווחים. אי אפשר לאכוף מינימום על כרטיס בבידוד — כרטיס יכול
להתארך רק אם מישהו אחר מוותר על זמן. הפתרון הוא מעבר רצפה **אחרון**, אחרי
ההצמדה לרשת ואחרי מניעת החפיפות:

1. **לשאול זמן**, מהכרטיס הבא לפני הקודם — כתובית יכולה להקדים את המילים שלה
   קצת, היא לא יכולה לפגר אחריהן. התורם חייב להישאר מעל הרצפה בעצמו.
2. רק אם אין ממי לשאול — **למזג** לשכן של אותו דובר, ורק כשפער המילים ביניהם
   קטן מ-`--max-gap`. מיזוג ראשון (כמו שניסיתי קודם) הדביק כרטיס אחד על פני
   שתיקה של 1.27 שניות: אותו פגם בדיוק, מהצד השני.
3. ומתחת לחצי הרצפה, כשגם זה לא עוזר — למחוק. מילה של שלושה פריימים היא לא
   כתובית.

104 מוזגו, 108 שאלו זמן, אפס נמחקו, והמינימום עלה מ-0.100s ל-0.400s.

## גודל של 9:16 הוא לא גודל של 16:9

הסקריפט משכפל את סגנון הכתובית מפרויקט תורם — וזה כולל את `size`. התורמים כולם
9:16, ושם `size = 20`. על קנבס 1920×1080 אותו מספר הוא כתובית אחרת לגמרי.
המספר הנכון לא נגזר מחישוב אלא **נמדד אצלו**: «דולב + תום», 1920×1080, אותו
פונט Bamberger, `size 8 × clip scale 1.278` = **10.2 אפקטיבי**, `y = -0.745`.
שם גם ראיתי ששורה של 29 תווים יושבת שם בנוחות, כך שתקרת הרוחב של התורם הוצרה
מדי — `--width-limit 1.3`.

הכלל הכללי: כשמשכפלים סגנון בין קנבסים בעלי צורה שונה, כל מספר שנמדד ביחידות
קנבס (גודל, `transform.y`, תקרת רוחב) חייב להימדד מחדש על פרויקט **באותה
צורה** — לא לחשב אותו מחדש, ולא להעביר אותו כמות שהוא.

## כרטיס לבן הוא לא צילום

בפרויקט הכנה כל בלוק מופרד בכרטיס לבן, וה-`source_timerange` שלו מתחיל ב-0.
`build_audio` עבר על **כל** מקטעי הטראק הראשי ושאב מהמיקרופונים בהיסט המקור של
כל אחד — כלומר מתחת לכרטיסים הלבנים נשתלו השניות הראשונות של הפרק, המתמלל שמע
שם דיבור אמיתי, וכתובית אחת אכן נחתה על חוצץ. כרטיס הוא **חור**: לא באודיו,
ולא ברשימת הקליפים שקובעת מה כתובית רשאית לחצות.

## שתי שכבות באותם טווחים — והמפתח לא יכול להיות (מקור, אורך)

בבנייה מחדש של השכבה העליונה מיפיתי כל מקטע לזמן הטיימליין החדש שלו לפי המפתח
`(source_start, duration)`. באורח S **שני זוגות התנגשו**: רגע שיא בשנייה
1264.833 באורך 5s, והוק של ריל 4 — אותו טווח מקור בדיוק. שני מקטעים קפצו למקום
של שכניהם, והשכבה העליונה יצאה לא ממוינת עם שני חורים של 341 ו-450 שניות.
המקטעים של השכבה התחתונה הם אותם אובייקטים שכבר הוזזו — לקרוא מהם את הזמן
החדש ישירות, לא למפות אותם.

## הטראק הראשי חייב מערך ממוין — אחרת קאפקאט מגלה אותו לסוף הפרויקט

בנייה מחדש של טווח מסומן ב«אורח S טיזר ורילס» נכתבה כ-`track["segments"] = keep + new`:
קודם מה שלא נגעתי בו, ואחריו עשרת המקטעים החדשים של 84–169. הבדיקה שלי עברה —
אפס חפיפות, כיסוי 85.20s, שאר הטראקים זהים בייט בבייט. ואז קאפקאט פתח את
הקובץ, **העיף את עשרת המקטעים לסוף הטיימליין** (1111.667→1196.867, בדיוק אורך
הפרויקט הישן + 85.2), והמשתמש קיבל מסך שחור עם כתוביות מרחפות.

הכלל: **בטראק הראשי, סדר המערך חייב להיות סדר הזמן.** בטראקים שמעליו קאפקאט לא
אוכף את זה — ולכן באותה כתיבה בדיוק, טראק 1 וטראק הלוגו נחתו נכון והמצלמה
התחתונה לבדה עפה. אבחון: אם מקטעים «נעלמו» מטווח, לספור את הסה"כ בטראק לפני
שמסיקים שנמחקו — כאן הסה"כ נשאר 36, כלומר הם היו בקובץ, רק במקום אחר.

```python
for t in draft["tracks"]:
    t["segments"].sort(key=lambda s: s["target_timerange"]["start"])
```

וגם: להזיז מקטע חזרה עושים בחשבון שלמים. `int(round(1027.367 * US))` נתן היסט
גדול ב-334µs מהאמיתי (1027.366666), וכל הגבולות נחתו שבריר פריים מוקדם.

## הבדיקה שלך רצה על הקובץ שלך — לא על מה שקאפקאט יעשה איתו

זו אותה תקלה מזווית שנייה, והיא כללית: כל ה-QA שלנו קורא את ה-JSON מיד אחרי
הכתיבה. קאפקאט הוא שכבה שנייה שמתקנת, ממזגת ומזיזה — הוא מיזג שני טראקי
«כתוביות» לאחד, הוא שינה גבולות פיצול לגבולות שלו, והוא הזיז מקטעים. אחרי כתיבה
משמעותית, לבקש מהמשתמש לפתוח את הפרויקט **ולקרוא את ה-JSON שוב** — הפרש בין מה
שכתבת למה שנשמר הוא ממצא, לא רעש.

## `time_offset` של קיפריים הוא זמן מקור מוחלט

בטראק הראשי של אותו פרויקט, מקטע שמתחיל ב-`source_timerange.start = 1439.0`
נשא קיפריימים ב-1449.1 ו-1450.767. לקרוא את זה כהיסט מתחילת המקטע זה בלתי
אפשרי (המקטע באורך 54s), ולקרוא כהיסט מתחילת הטיימליין מזיז כל תנועה למקום
אחר. זה **זמן המקור המוחלט**: 1449.1 יושב 10.1 שניות בתוך השוט, כי אלון קיצץ
את הקצה השמאלי אחרי שיצר את התנועה. קאפקאט מחזיק את ערך הקיפריים הראשון גם
לפניו — ולכן «כניסה» שנראית בתחילת השוט היא בעצם עשר שניות פריים קפוא ואז
תנועה. לחשב `src_at(seg, t)` ולא לנחש.

## מקטע בלי קיפריימים חוזר לסקייל הבסיס של הקליפ

בחיתוך מקטע לחתיכות, `common_keyframes = []` לא אומר «בלי תנועה» אלא «הסקייל
של `clip`». באורח S הבסיס היה 3.6954 בעוד התנועה בפועל התייצבה על 3.18 — כך
ששוט שלם היה קופץ ב-16% בלי שאף בדיקה תתלונן. אם לחתיכה אין תנועה משלה: או
להעתיק את הקיפריימים של המקור (כשהיא מכסה את כולו), או לקבוע לה גיאומטריה
מפורשת. בריצה יבשה זה נראה כ«keep 3.695 כמו שהיה» — טקסט מרגיע שמסתיר קפיצה.

וגבולות מקטע נושאים את העיגול של קאפקאט: 108.466666 ולא 108.467. התאמה של
תנועה שנגמרת על קאט צריכה סבילות של פריים, אחרת היא לא נתפסת ונופלת בשקט
לענף ה«בלי תנועה» שלמעלה.

## מסנן ה-0.06s בולע מילים אמיתיות — וההבדל הוא המשמעות

`end_s - start_s >= 0.06` נועד לזרוק ארטיפקטים של המתמלל. ב-85 שניות של אורח S
הוא זרק **חמש מילים אמיתיות**, כולן קצרות וכולן נושאות משמעות: «לא», «את»,
«של», «אתה». אחת מהן הפכה «זה **לא** בשבילך» ל«זה בשבילך». הן נופלות בגלל
פסיק צף — 93.68 − 93.62 = 0.05999999999999517 — כך ש«בדיוק 0.06» נכשל.

לסרוק אחרי התמלול את המילים בטווח 0.055–0.065, ולהרחיב אותן במקום למחוק:
```python
short = [w for w in raw if 0.0 < w["end_s"] - w["start_s"] < 0.065]
```
מילה בת אות אחת שהיא גמגום («ל...») כן ראויה למחיקה — אבל בהחלטה, לא בעיגול.

## פס הכתוביות לא נגמר כשאין חפיפות — הוא נגמר כשאין אודיו בלי כתובית

הבדיקה אחרי ההזרקה ספרה חפיפות, אורך מינימלי וסגנון, ועברה. ואז המשתמש שאל
«הכנסת הכל?» — ובקצה הטווח היו 0.53 שניות שבהן **עוצמת המיקרופון גבוהה מממוצע
הדיבור** בלי שום כתובית: משפט שלם («כי אני באמת עוזר להם») שהמתמלל לא הוציא.
לכל חור בין כתוביות למדוד RMS במיקרופון שמחזיק את הקטע; חור עם קול הוא באג,
חור עם נשימה הוא נכון (ולהשאיר אותו — כתובית שיושבת על שתיקה נראית כמו תקלה).

## המצלמה היא מקור תמלול שלישי ובלתי תלוי

לפני ש«מתקנים» ניסוח שנשמע שבור: האודיו המוטבע בקובץ המצלמה הוא ה-main out של
המיקסר, ערבוב אחר לגמרי מהערוצים המבודדים, והוא מתמלל אחרת. אחת-עשרה שורות
חשודות באורח S הוצלבו מולו — «כפרה, פרסה», «במכירות אני איפה», «אמר לו» —
והוא הסכים עם ערוץ הדובר **מילה במילה בכולן**. כלומר אלה לא שגיאות אלא איך
שהוא מדבר. הצלבה שמחזירה אפס תיקונים היא תוצאה, לא בזבוז: היא ההבדל בין
להשאיר ניסוח מוזר לבין להמציא במקומו ניסוח חלק.

מה כן נמצא באותה סריקה: מילה של המראיין שהמצלמה שמעה ואף ערוץ לא הוציא.

## פיצול במונולוג: למדוד את השני, לא להניח

בטווח של 85 שניות שבהן המראיין מחזיק 0.9% מהאנרגיה אין «חילופי דברים» לפצל
עליהם, אבל גם 31 שניות שוט אחד זה מוות. שני מדדים נותנים מועמדים אמיתיים:

* **דומיננטיות במיקרופון שלו** — חלון שבו ה-RMS שלו מעל פי-6 מרצפת הרעש שלו
  *וגם* מעל פי-1.5 מהערוץ השני. באורח S יצאו בדיוק שניים, 0.40s ו-0.35s.
* **אנרגיית הפרש-פריימים בזווית שלו** — `fps=4,scale=192:108` בגווני אפור,
  ממוצע `|diff|`, ממוצע נע של 2s. פי-2 ומעלה מהחציון = הוא זז, מהנהן, מגיב.

שתי הבדיקות יחד נתנו ארבעה חלונות, 17.6% מהקטע — בתוך התקציב שנמדד מהרילסים
שלו. ולפני שבונים: לרנדר את הפריים המפוצל בפועל ולהסתכל עליו. אחד המועמדים
נפסל ככה.

## 30.08.26 — «0830»: three defects Alon caught in the first playback

**The caption prototype was the odd row.** `donor_styles()` kept
`by[colour]["mat"]` as whichever segment came last, and exactly one caption of
262 in «פרויקט-דוגמה N רילס» carries no text effect. Every caption injected into
0830 inherited it: no effect `7336838446625082629`, `background_color`
`#000000` (a black box behind the words in the player), `border_width` 0.036
instead of 0.08, and `strokes`/`shadows` written into `content` — beside an
effect that owns both. Fixed by taking the **modal** material per colour and
asserting the contradictions (effect + strokes, effect + background) before
writing. The check that finds this in seconds is a field-by-field diff of one
injected material against one the user coloured by hand — not a segment count.

**A Compound clip is a card wearing footage's clothes.** `type: "video"`,
`path: ""`, `source_timerange` starting at 0. The card filter tested
`type != "photo"`, so the engine pulled the mics at episode second 0 and wrote
«יאללה אליפות» over the reel's first 2.5 seconds. Test for a real path.

**`--reuse` across a re-cut.** He trimmed 39s out of 0830 between two runs; the
cached word timings replayed onto the new timeline and 134 cards landed on
different footage. Spot-checking three points caught it — at t=30 the audio said
«אם אתה לא ננצוח» while the card read a line from another reel. The script now
stores a signature of the clip list with the cache and refuses to reuse across a
change.

**And one that was not a defect:** a keyframe's `time_offset` is **source**
time, not segment-relative. Checking it against `target_timerange["duration"]`
reports hundreds of false excursions — including on every reel he approved,
which is the tell. `qa25.py` check 3 already compares against
`source_timerange`; trust it over an ad-hoc check.


## A bed cloned from an online-library material plays the library's cache, not your file (0922, 22.09.26)

The donor's music segment pointed at a CapCut library track (`effect_id 7021278097383098369`, `category
Favorites`). Cloning it and swapping `path` looks right in JSON and in every check; on open CapCut resolves
the material by its `effect_id` and rewrites `path` to `…/User Data/Cache/music/<hash>.mp3` — all four
beds became one cache file and Alon heard no music. Local audio is `type extract_music`, `category_name
local`, `effect_id ""`, its own `music_id` / `local_material_id`, and the file inside the draft folder.
`reel_append.py` normalises the whole bed track; check 4b/`register_media --list` will not catch this —
the only symptom is the path after his first save.

## Two audio faults that sound like "the guest's mic is broken" (0922 reel 5, 22.09.26)

1. **Bleed doubling.** Each camera copy carries its own RODECASTER channel, gain-baked +17…+26 dB; both
   layers play at volume 1. The guest's bleed in the host's channel then sits ~1 dB under the guest's own
   channel, delayed a few ms: summed = comb filter, hollow voice. Measured on reel 3: cam1 −15.2 dBFS vs
   cam2 −14.3 dBFS on a guest-only stretch. Fix = `copies_audio_gate.py` (ownership gate, −30 dB floor).
2. **Stitched AAC.** `reel_append.py` gain-baked the new piece separately and concatenated with `-c copy`;
   the copy's audio stream is then two encodes glued — CapCut may play the seam wrong. One continuous
   audio encode per copy (the gate script does exactly that) removes it.


## 0923 premium round (23.09.26)
* **Caption hole.** 228.6–235.9 s of reel 3 had speech and no cards; the caption dump made it visible, the QA did
  not. New rule: gap scan (> 1.5 s, mic loud) before any caption report. `reel_caption_add.py` fills holes.
* **Wrap width.** Text materials carry `line_max_width` 0.82 → CapCut wraps at 886 px on 1080. Alon's 0922 titles
  (1490 px at size 25, two lines) prove it. Supers are fitted to 860 px.
* **Two copies, one mix.** When mic1 = mic2 (one RODECaster feed), the over layer at volume 1 doubles the voice
  for the whole two-camera reel. `reel_polish.py --mute-over`. Check with `ebur128` on both copies' windows.
* **Backups in the draft folder are media.** `register_media.py` registered the compressor's `.m4a` backup;
  keep backups in `~/Movies/reel-captions-work/`.
* **Transition semantics unverified.** `is_overlap` on Glare II — do not attach transitions to a 300-caption
  timeline without a CapCut-side test first.

* **Clone of the white card = white box.** The card is an online material (`material_id`, `category_id`, `source 1`);
  any clone keeps that identity and CapCut re-links it to the cached white image on open. The 0923 logo rendered as a
  white rectangle for a whole review round. Local assets: `material_id ""`, `category_name "local"`, `source 0`.
* **zsh word-splitting.** `for r in "5 102.45"; do set -- $r` gives one word in zsh. Use `${r%%:*}` / `${r##*:}`.

* **0923 round 3.** Ripple boundary keys ±1 µs off the piece edge → range checks need tolerance. A cut equal to a
  sliver leaves a 16 µs piece → drop pieces < 1 frame. PIL here has no raqm → Hebrew must be drawn reversed.
  The compressor raises the room tone → pause floor −30, not −45. Angle switch 0.1–0.3 s after a jump cut = «קפיצה».

## `fixed_width` is the real wrap, not the font calibration (0923 r6, 23.09)

A text material cloned from a CapCut auto-caption is `type subtitle` with `fixed_width 377.8` — a fixed text
box. CapCut wraps at ≈ fixed_width × 1.2 canvas px and, in Hebrew, breaks INSIDE a word («3 טיפי / ם» from a
516 px super at size 40; captions ≤ 740 px still two-line). The "≈770 px wrap at size 20" in the house numbers
was 0922's `fixed_width 617.4` × 1.2, misread as a font constant. Every project Alon captioned by hand has
`type text`, `fixed_width -1` (auto box) and never wraps under `line_max_width` 0.82 × 1080 = 886 px.
Fix: `reel_text_autowidth.py` sets `fixed_width/fixed_height -1` on captions + supers. Verify text layout
on a CapCut frame or his screenshot, never on the JSON or on `reel_stills.py` (which neither wraps nor
colours ranges).

## The online-material trap reaches back into old drafts (29.09)
The white-box bug is not only a build-time mistake: any draft assembled before `reel_broll.py` wrote local
identity still carries it (0919: 65 materials, «הבירולס בכלל לא עובדים»; older ones: אורח O רילס 59, אורח K 6).
`reel_localize_materials.py` + `reel_repoint_materials.py` repair a draft in place — the clone keeps BOTH the online identity and the card's cached-image `path`; fixing one without the other still shows white (0919, 29.09, first fix «עדיין רואה את זה ככה»). Symptom to recognise: the clip is on the timeline, the
file exists, the Media panel lists it, and the preview shows a white rectangle — check `source`/`material_id`.

## Captions: a text effect and a stroke are two different owners (0923 r10, 30.09)

Alon: «דייק את הכתוביות עם הצללה ומסגרת — יותר הפרדה מהרקע». The 0923 captions carried `styles[].effectStyle`
7336838446625082629 (the look of every approved reel) — that effect owns outline and shadow, the sliders do nothing,
and injecting `strokes`/`shadows` beside it is the 0810 «זוועה». The only way to a stronger outline is the OTHER house
look: effect removed, המלצות הבונקר stroke+shadow recipe written into content and material (`reel_caption_stroke.py`).
Decide which owner a project has before touching a caption style; never leave both.

## A round after his hand-edits is an ADD, not a rebuild (0923 r10)

The draft on disk had moved since r9 — b-rolls and a bed removed, captions deleted, an arrow animated by hand, new
tracks (so track INDICES shifted; diff by name). `reel_broll.py` / `reel_sound.py` are idempotent by tearing their
track down, which is exactly wrong here. `reel_broll_add.py` appends; QA = his tracks byte-identical against a base
frozen before the write, and every pre-existing b-roll segment unchanged except the ones deliberately trimmed.

## 17.11.2026 — `reels_build.py` on the Bunker's own content takes (not a client episode)
Two camera work copies, each with its own mic baked in, on two layers (top at alpha 0) → BOTH mics play → Alon: «יצרת בעיה
עם הסאונד». A fixed crop baked into the copy is not framing either. For content takes the target is different
(bunker-editing/references/content-reels.md): a Multi-camera clip per take, each camera framed for 9:16 (subject centred,
eyes on the upper third), the «הבונקר» adjust preset, then a multicam edit — and one voice track. Never take a grade from
another client's donor project (`--adjust` false / `"adjust": false` in the plan skips the donor's adjust track; `vf1`/`vf2`
per shoot rotate side-mounted cameras; `title_like` picks the donor's card title by its text).
