# The single-talking-head promo (0910, 9:16) — intro, punches, kinetic stacks, b-roll layer, export

A one-person promo is not a two-camera podcast: the face has to carry the frame alone, so the motion is punches between two sizes, the text is kinetic stacks, and the b-roll is a literal scene of the persona. Everything below was corrected by Alon across ten rounds on 0910.

## Look for CapCut's own Auto-reframe before you add yours

A project Alon converted to 9:16 with **Auto reframe** carries a `smart_crop`
material per camera segment (`materials.smart_crops`, `crop_ratio: "9:16"`, a
cache under `<draft>/smart_crop/`), and every segment sits at `scale 1.0`
because the crop already fills the canvas. Our fill-scale reframe on top of
that is a second crop of a crop: on 0910 the JSON read ×3.16 (correct on paper),
CapCut rendered ×10 — a mouth and a microphone — and all thirty checks passed,
because every one of them measures the JSON and none of them measures what
CapCut draws. `qa25.py` check 8b now fails on a camera segment that has both a
smart_crop ref and `scale > 1.2`. Before reframing, either drop the smart_crop
refs (ours is face-measured and centred; his was 3% off) or scale relative to
1.0 and keep his — never both. And open the project and look at one frame; the
skill has said so for months and this is the round that proved why.

## Three rules from 0910 (a single talking head, 13.09.26)

**The intro is a mini zoom-out.** Alon: *"אפקט של זום אאוט לפי הקיפריימים עם
הקטנה של כ-5% מגודל הפריים, ככה שהפריים אחרי שניה מהרצת הסרטון יגיע לגודל
הרצוי, עם תנועה חלקה"* — and "put it in every video". The first camera piece of
every reel (project start, or the piece right after a title card) starts 5%
larger than its target framing and eases to it over 1.0s (`curveType
CurveInOut` on both keys), then the usual slow push-in resumes. This is the one
reversal allowed inside a shot; `reel_motion.py --intro 0.05 --intro-s 1.0` is
the default and `qa25.py` check 18 drops the intro window (`--intro-s`) before
it looks for wobble.

**A single talking head is centred on the FACE, and the pan follows him.**
The 0.33–0.38 window is for a two-shot; a one-person promo wants the face at
canvas x = 0.5 — *"הפנים צריכות להיות בנקודה 0 על ציר ה-x, ביחס לפנים, לא
למידה של הפריים, עם התאמה בקי-פריימים לתנועה של הדמות, בצורה חלקה"*.
`transform.x = 0` is not that: on 0910 his face sat at 0.53–0.55 of the source
in the opening shots and landed off-centre in every frame. So track it: sample
the SOURCE at 4 fps, YuNet face → `fx`, median (1.25s) then mean (1.75s)
smoothing, `x(t) = −s(t)·(2fx−1)` clamped to ±(s−1), keyframes kept only where
a straight line would miss by > 0.006 (≈ 3px) and re-solved at every scale key.
That gave 149 PositionX keys over 187s — a slow drift that follows a lean, not
a jitter that follows a head turn. `qa25.py` check 9 skips a tracked pan and
check 29 (`--face-x 0.47,0.53`) judges the face itself. Planner:
`scripts/track_pan_plan.py <project>` writes `~/Movies/reel-captions-work/<project>_pan_plan.json`
(`{segment_id: [[source_us, fx], …]}`); `scripts/track_pan_apply_example.py` is the
0910 apply step (intro + pan + caption/logo y) to adapt — it derives x from the
FINAL scale curve, so run it after the zoom is written.

**Captions and logo sit as a pair.** He moved them closer together on sight:
captions `y −0.19` (band ≈ 0.57–0.62) and the logo `y −0.40` (≈ 0.66–0.74),
a 4% gap, with the chin (≤ 0.52) clear of both. The logo goes on footage only,
never over the white cards, at 32% of the canvas width.

## Punches, not drift (0910 round 3)

Alon, after watching the tracked pan and slow push-ins: *"יש הרבה תנועה איטית של
'ריחוף' של הקי-פריים, הייתי רוצה פחות כאלה ויותר תנועות שתופסות את העין — פעם ב…
זום אין/אאוט חד וחלק"*. So for a single talking head the motion layer is:

* every shot **holds still** between moves — no 1.2%/s push;
* on **sentence starts** (the word after a `.`/`?`/`!` in the words cache),
  spaced ≥ 4s apart and ≥ 1.5s after the cut / ≥ 1s before it, the shot
  **snaps** between two levels over 0.45s with `CurveInOut` — even shots on
  1.00/1.08 × fill, odd shots on 1.05/1.113 × fill (ceiling ×1.123), so cuts
  still land with a framing change and the snaps alternate in / out;
* the intro zoom-out (5% → target over 1s) stays on the first shot;
* the tracked pan is re-solved on the union of pan and scale key times.

`scripts/punch_motion.py <project> <words.json> <pan_plan.json>` does it;
`qa25.py` check 18 now classifies each move as punch (≤0.7s, ≥2.5%), hold or
drift — reversals are the style in a punchy shot, a punch under 0.3s is a jump
cut and fails, and 19b measures drift only. A two-camera podcast keeps the
old one-way push-in (`reel_motion.py`); the snap style is for one face that
has to carry the frame alone.

## Sentence-aware cards with the question mark on them

*"למה כאן אין סימן שאלה והפרדה של הכתוביות?"* — a card read «ערכתם השנה הלקוח»,
a question and the next sentence's first word on one line. Rule: a card never
runs across a sentence end (`.`/`?`/`!` on a Whisper word); split there on the
word's end time (≥0.30s per side, else keep the mark and skip the split), and
keep `?`/`!` on the card that asks. Periods and commas stay off-screen.
`scripts/sentence_split_captions.py` re-splits an existing track from the
words cache while keeping the QA-corrected card text (the cache still holds
the raw ASR words, so align tokens with difflib and never copy text from it).
Cards with two style ranges (the mixed-font brand card) are skipped, not split.

## Music bed per section, and a CTA arrow when he says "the link below" (0910 round 4)

Alon's asset library is `~/VideoAssets/` — `סאונד/מוזיקת רקע`
(64 beds, mostly Pixabay-style royalty-free; the karaoke pop songs and film
themes in there are NOT for client work), `סאונד/SFX` (Pop, Woop, Notification,
swooshes…), `גרפיקות ואנימציות/חץ לבן.png` (a white down-arrow, 1080² with the
glyph in the middle 40%). There is no librosa on this machine; tempo and
loudness come from ffmpeg → numpy (onset autocorrelation, 60–200 bpm) and that
is enough to sort beds by energy.

**Safe library for anything that gets published (since 2.11.2026):**
`סאונד/מוזיקת רקע/שירים מהפוסט של עדן בלי/טראקים בטוחים מ-Pixabay/` — 165
Pixabay tracks in 13 mood folders (1 storytelling … 8 energy … 13 dark beats),
each with no Content ID and no AI flag. Pick from `קטלוג.csv` there (folder,
use_for, title, seconds, LUFS, page); the usage guide is `מדריך שימוש.html`
one level up. Nobody has listened to them: audition before committing, and
level each bed under the speech (LUFS spans about −23 to −5). Alon's IG
accounts are business accounts, so commercial songs (the karaoke/pop rips and
film themes in `מוזיקת רקע`) never go into a published reel. No licence log
per track is kept (Alon, 2.11.2026). Which track goes in which video is
Alon's call. The same 165 are also in the Captain app's cloud sound toolbox
(🧰 → מוזיקה), named «<folder> · <title>», so `add_music` can pick them there.

* **One bed per section.** A promo cut into sections by white cards is several
  ads; each gets its own bed picked by the section's mood (corporate/inspiring
  for "make money from your courses", hip-hop for social managers, ambient for
  "vacation without worry", dramatic for the "two kinds of people" closer).
  All beds on ONE audio track, gain per file from measured RMS so every bed
  sits ~16 dB under the speech, `audio_fades` 0.8s in / 1.2s out. Never let a
  bed cross a white card.
* **The arrow.** Every "…כאן למטה" gets the white arrow under the logo
  (`scale 0.20, y −0.68`) for up to 3s, cut before the section ends: pop-in by
  scale keyframes 0 → 1.18× → 1× over 0.4s (`CurveInOut`), a 0.03 bob every
  second, scale-out in the last 0.25s — no `KFTypeAlpha` (never seen in his
  drafts) and no cached CapCut animation dependency. `Pop.mp3` at 0.7 on its own
  SFX track, 50 ms before the phrase. Find the phrases in the words cache
  (`כאן` followed by `למטה`), not by guessing timestamps.

`scripts/…` — the 0910 apply is `0910_extras.py` in the session scratchpad;
copy it into the skill the next time a promo needs beds (parametrise PICKS/CTA).

## Kinetic headline stacks (the yuval.perez / guyedri7 look, 0910 round 6)

Alon's reference reels (IG `DND9uPusHx2`, `DYUzBlbsSao`, `DYhficVMe3g`): the
opening sentence builds **line by line in the middle of the frame** — each line
pops in (scale-in with a soft blur), the earlier lines slide up to make room,
the key line is bigger and heavier with one word in colour, and the whole stack
leaves together. Secondary lines are small and light; numbers and dates get
the big treatment. That is text layers with keyframes, not an effect, so it is
buildable from the JSON — `scripts/kinetic_headlines.py` does it:

* one text material + segment per line on its own text track (`kinetic 1..3`,
  because lines overlap in time); sizes s/m/b = 14/18/25, one highlighted word
  in the **house yellow** (0.96, 0.78, 0.06 — check 24 allows only the palette);
* entrance = scale keyframes 0.4 → 1.10 (0.22s) → 1.0 (0.36s) `CurveInOut`
  plus the cached **Fade In** preset (200ms); exit = cached **Fade Out** (300ms)
  on every line at the window end. The blur-in of the originals needs the
  `Blur` preset, which is not in the local cache — one manual use in CapCut
  caches it (`references/text_anim_donors.json` holds the cached ones);
* stack geometry: line box = 86·size/20·1.25 px, 12px gaps, group centred at
  y ≈ 1150px (60%); when line *k* appears every earlier line animates to its
  new slot over 0.30s. Window = first word −0.05s → last word +0.35s;
* the regular caption cards inside the window are removed (a straddler is
  trimmed to start at the window end) and the logo piece starts 0.15s after
  it — the stack sits where the captions and logo were;
* `qa25.py`: checks 21–23 measure only the largest text track; 4b ignores
  CapCut animation entries (they carry the resource id as `id` and differ only
  in `start`).

Also in this round: «27 בספטמבר» in the house yellow on every regular card
(style ranges), `scripts/split_wide_cards.py` (cards wider than CapCut's wrap
point are split on the last word's start; `fixed_width = -1`), and
`scripts/promo_extras_example.py` (music beds + CTA arrow + SFX from 0910).

### Kinetic stacks v2 — what Alon corrected on the first pass

1. **Not only the opener.** Stacks also mid-section on the strongest claims —
   numbers («אלפי שקלים», «ב-997 שקלים»), the triads («לא משרה / לא השקעה /
   משהו שלישי»), the closer («תהיו מהסוג הראשון»). ~2 per 25s section.
2. **A big line must fit on ONE row.** CapCut wraps at ≈385 PIL-px@60 for
   size 20 (scale linearly: size 25 → 308). `fit()` shrinks the size down to 14
   and then splits at the middle word; the wrapped «הפעם אתם שומעי / ם לפני» was
   the failure. Prefer one big WORD («לפני», «מוזר») to a big phrase.
3. **Real line spacing.** Box = 86·size/20·1.5 px + 10px gap; the stack is
   clamped between 52.6% and 70% of the canvas. v1 used ×1.25 and lines overlapped.
4. **Vary the entrance.** Cycle per stack: pop (scale 0.4→1.1→1) · slide-up
   (+0.06 → target) · zoom-out (1.7→1) · `Grow` preset · `Showing Up` preset;
   exits alternate Fade Out / scale-to-0.6 + Fade Out. The big line always pops
   unless the stack is a zoom-out stack.
5. **The translucent light style** («לבנות עסק אונליין» in the reference) =
   `bamberger-grunge-light-fm.otf` (has Hebrew) + material `global_alpha` 0.72
   (the field CapCut writes for text opacity; `text_alpha` stays 1). Use it for
   the lead-in line of a stack.
6. **A soft swoosh** (`swoosh quick 1.mp3` @0.35) on each stack start, skipped
   within 1.2s of a CTA pop, on its own `sfx text` track.
7. **The logo is cut out under every stack window** (±0.15s), not only delayed
   at section starts.

`scripts/kinetic_headlines.py` is the v2 build; it tears down its own tracks
first, so it is safe to re-run after editing the STACKS table.

### Kinetic stacks v3 — Alon's second round of corrections (13.09.26)

`scripts/kinetic_headlines.py` is now the v3 build (modes `roll` / `replace` /
`words`); v2 is gone. What changed and why:

1. **The logo never leaves.** One logo piece per contiguous camera run (never on
   the white cards) and the stacks sit **above** it: zone 950–1245 px, the logo's
   top edge is at 1265 (y −0.40, 158 px tall at scale 0.32). Cutting the logo
   under every stack (v2) was rejected — "הלוגו צריך להופיע לאורך כל הסרטון".
2. **Lines don't all stay.** `roll` keeps only the newest lines that fit the
   zone (older ones fade out 0.25s as the next enters), `replace` shows one line
   at a time, `words` builds rows word by word. Two visible lines is the norm
   (b+m = 165+119 px); three only for small sizes.
3. **A date is one card in one colour.** «ב-27» | «בספטמבר נראה לכם» was split
   across two cards with the first in white — the script merges such pairs into
   «ב-27 בספטמבר» (yellow, ends at the word's end) and leaves the rest white.
   Never put a date into a `words` row: every word there is its own clip.
4. **Entrances/exits** cycle per stack: pop · slide-up · zoom-out · `Grow` ·
   slide-right (x +0.30→0) · `Showing Up` · drop (+0.06 → −0.008 → 0) · tilt
   (rotation −8°→0 with scale 0.8→1); exits: `Fade Out` · shrink · rise-out
   (up, away from the logo). Everything else CapCut offers (Blur, Bounce In,
   Typewriter, Enlarge Letters, Tremble, Wafting In …) exists in his older
   drafts but **is not in the local cache** — one manual use in CapCut caches it.
5. **The translucent style is NOT the thin brand font.** The reference
   («לבנות עסק אונליין») is a clean sans in italic with no outline and the
   background showing through: `Assistant-Regular.ttf` + `italic_degree 10` +
   `global_alpha 0.62` + `border_width 0` + **no `effectStyle`** in the content
   styles (the house text effect owns the black outline — remove it or the line
   reads as "thin", which is what v2 shipped and Alon rejected).
6. **Word-by-word rows with a click.** Each word is its own text clip placed
   RTL: right edge = 540 + row_width/2, word centre = right − Σ(previous widths
   + 0.32 em gaps) − width/2, entrance scale 0.5→1.08→1.0 over 0.24s, and a
   click (`references/click.wav`, 0.36s cut from «Text appear SOUND EFFECT»
   @0.8) at every word on `sfx click` — a second lane when two clicks are
   closer than the sample length, because CapCut refuses overlaps on a track.

**Calibration that made 6 possible** (measured on Alon's screenshots of v1,
isolated words «אנשים» 278 px / «שלישית» 349 px / «לפני» 172 px at size 25):
`canvas px = PIL@60 width × size / 10`, i.e. **em ≈ 6 px per size unit**, line
pitch 6.6 × size (6.2 for rows that never shift), one-row wrap ≈ 770 px. The
compositor's old 86·size/20 was 30% small — every stack looked roomier in my
stills than in CapCut. `scripts/composite_stills_example.py` carries the
corrected numbers and honours `transform.x` and `border_width`.

Kinetic text tracks are allocated per segment (first track with no overlap,
new one if none) — a `words` stack of nine words needs nine tracks.

### Kinetic stacks v4 + the caption contract (0910 round 9, 13.09.26)

Alon's three corrections after v3, now enforced by `scripts/kinetic_headlines.py`:

1. **Pages, not a rolling window.** When a stack has more lines than fit the
   zone, show them as *groups* — «צמד 1+2 ואז צמד 3+4» — and the group leaves
   together when the next one starts. The split point is the longest pause
   between lines if any pause is ≥ 0.35s; otherwise the fullest page. Dropping
   only the oldest line each time ("keep the 2 most relevant") looked unnatural.
2. **Every spoken word is captioned exactly once.** Either it is inside a stack's
   word range (the kinetic text shows it) or it sits on exactly one regular
   card. v1–v3 removed whole cards that merely *touched* a window (words before
   the stack lost their caption) and trimmed straddlers by time while keeping
   their full text (the stack's words appeared twice). The rebuild is word-level:
   a frozen copy of the full-coverage caption track (`draft_info.caption-base-v4.json`
   — a custom name, because `_backup()`'s rotation deletes `ccstudio-backup-*`
   files and did delete the one I was reading) plus a per-word token map
   (`ccstudio-0910-wordmap.json`, QA-corrected text per word index). Cards keep
   their bytes when their word set is untouched (109 of 115 reused verbatim);
   partial cards are re-cut on word boundaries; a card ends at the stack's
   first word −0.05s and the next starts at the stack's last word end. The
   script prints `words without caption: []` and `shown twice: []` — a run that
   prints anything else is not done.
3. **A stack's tail never covers the next caption**: the window ends at the
   next spoken word −0.02s (min last word +0.08s), not last word +0.35s.

Alignment rule that bit twice: align a card's tokens only to the raw words
spoken **while it is on screen** (start ∈ [card start −0.08, card end −0.08));
a ±0.3s slack or a global sequence alignment lets a repeated phrase or an
unequal `replace` opcode claim the neighbour's words, which then get dropped
as "stack words" — that is how «ב-27» vanished from two date cards.

### B-roll layer (Seedance 2.5 via the Higgsfield MCP) — `scripts/broll_layer.py`

Alon's process, verified and extended (the additions are marked ➕):

1. Understand the message and the audience (0910: freelancers who serve
   businesses that teach — editors, social managers, photographers, marketers —
   sold a webinar on 27.09 about recurring income from existing clients).
2. Pick one key sentence per section that can be shown, not said.
3. Decide per moment: generate b-roll from scratch, or plant a graphic you can
   draw yourself (the «27» calendar badge is a PIL PNG; anything with Hebrew
   text is drawn locally, never generated — AI garbles Hebrew).
   ➕ **Fix one visual style first** (here: cinematic, warm light, shallow DOF,
   clean, no text/logos/faces) and put it in every prompt so eight clips from
   eight prompts read as one film.
4. Generate and insert at the right time. ➕ Review a contact sheet of every
   clip (`fps=1,tile=5x1`) before touching the draft — a wasted image costs 2
   credits, a wasted Seedance clip 45. ➕ Strip/ignore audio (`generate_audio:false`),
   mute the segment (`volume 0`), source-offset 0.3–0.6s to skip the settle
   frames, hard cut in with a 1.08→1.0 settle over 0.5s, hard cut out.
5. Don't hide the captions. ➕ Track order is the mechanism: the b-roll track is
   inserted right **above the adjust layer and below every text, logo and
   arrow track**; text tracks always render on top. A stack popping over a
   b-roll (coins under «אלפי שקלים») is a feature, not a clash.
6. Don't break the SFX. ➕ Speech and music beds untouched; a whoosh
   (`Woosh #2.WAV` @0.45, 0.12s before the cut) on its own `sfx broll` track;
   the badge reuses the CTA pop sample on its own lane.
7. ➕ QA + composite stills at every b-roll time (`composite_stills_example.py`
   draws the overlay frame), and record the credits spent.

Higgsfield specifics: model `seedance_2_5`, `mode t2v`, `9:16`, 5s (min 4),
`1080p`, `generate_audio false` → **45 credits per clip**, HEVC 1080×1920 24fps,
5.04s. Three of eight prompts were hijacked by the "IN THE DARK" preset
recommendation (any dusk/dim wording); resubmit with
`declined_preset_id 24bae836-2c4a-48e0-89b6-49fcc0b21612` and brighter wording.
Use `generate_video_batch` + `jobs_wait` (≈2–3 min for eight clips); download
the `result_url` files with curl into `<scratch>/broll/sN.mp4`.

`qa25.py`: a video track named `broll` (or all pieces < 8s with < 30%
coverage) is an overlay, not a second camera — without that, checks 20 and 28
wake up and fail on a single-camera promo.

### Round 10 on 0910 — the nine polish items, and what "export" means here

`kinetic_headlines.py` (v5) and `broll_layer.py` (v2) now carry:

* **SFX density.** Clicks only on a row's first word and on highlighted words,
  never on a bare function word (`STOP`): 31 → 14 clicks; 3+-hits-within-0.8s
  pile-ups 24 → 1. Count events per second before shipping any SFX layer.
* **No quiet stretches > 6s.** A section with nothing but face + captions for
  more than ~6s gets a b-roll or a small stack. 0910 went 8 → 12 clips.
* **No caption under 0.5s.** After the date is made whole, flickers are glued
  to the next card (never into a date card) and wide rows are re-cut at the
  best word (both halves ≥ 0.5s when possible). Order matters: date-split
  first, then glue, then re-split, until stable.
* **B-roll variety.** One inset (`pip`: the clip's middle square at scale 0.34,
  x +0.66 / y +0.60 beside the head, pop in/out) among full-frame cuts; full
  frames settle 1.08→1.0 and punch 1.0→1.12 in the last 0.25s before the cut
  back; one section opens on b-roll under its stack instead of on the face.
* **Music ducks 3 dB** (×0.71) under every full-frame clip via `KFTypeVolume`
  keyframes on the bed pieces (values are gain multipliers, source clock).
* **The badge on every date card**, ≥ 2.2s, cut at the next full-frame clip;
  dark header, the number in brand yellow.
* **Opener breathes**: the first logo piece starts at 1.5s with the cached
  video `Fade In` (id 6798320778182922760, wrapper type `sticker_animation`).
* Word rows ≥ 16 (pitch 6.0×size), roll `s` = 15.
* `qa25.py`: `_broll_layer()` tracks are skipped by checks 7/8/9 too.

**Export.** CapCut has no export API. GUI automation (Quartz mouse events +
`screencapture`, `scripts/../ui.py` pattern) reached the home screen but the
first click raised macOS permission prompts (screen-recording picker bypass +
accessibility for the host app) — those are the user's to grant, never
auto-accepted. The working recipe is: the user exports the whole timeline once
(4K 2160×3840, 60fps) into the prepared Desktop folder, and a watcher splits it
into the sections at the white-card boundaries (`0910_sections.json` from the
main track's camera runs; libx264 CRF 15, aac 256k). Section files are named
by content, not by number only.

### B-roll, second pass — what Alon rejected and the rule that came out of it

"רוב הבירולס לא מדויקים למה שנאמר ולא מתלבשים טוב … הגרפיקות שהוספת לא
טובות, תסיר אותן." The first pass was stock metaphors (coins, hourglass,
door, chart, skyscraper) plus a drawn calendar badge. All of it went.

**The rule: a b-roll clip shows the persona doing exactly what the sentence
says.** «ואתם קיבלתם תשלום פעם אחת» → the editor holding bills, rubbing his
forehead. «יצאתם לחופש בלי דאגות» → the same man on a beach lounger typing
client replies while his family plays behind him. Write who / where / what
happens / what he feels; no metaphors, no graphics, no badges (the CTA arrow
is the one overlay Alon asked for by name).

**Keep one face across the film.** Generate the persona once with
`nano_banana_pro` (3:4 portrait, described precisely: age, hair, stubble,
shirt colour, setting), then pass its job id as `image_references` with
`seedance_2_5` in `mode: omni_reference` — same 45 credits as t2v, and the
man in the balcony, café, beach and home-office clips is recognisably the
same person. Scenes with other people (the social manager, the welcome at
the startup, the three viewers) stay t2v. Blurred screens, notifications as
"abstract banners with no readable text".

**Never share a material between tracks when one of them is rebuilt.** The
badge's pop lane reused the CTA arrow's Pop material; the lane's tear-down
deleted the material and CapCut silently dropped BOTH tracks on load — the
arrow lost its click and Alon noticed before I did. Every track gets its own
material; `broll_layer.py` restores `sfx arrow` from the frozen caption base
if it is missing, and repoints the path when the file lives in the draft folder.
