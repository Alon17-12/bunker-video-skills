# The 16:9 landing video (0919 «דף תודה»)

Everything the vertical pipeline does NOT cover: a landscape talking-head page video built from a
Multi-camera clip Alon already cut. Scripts: `scripts/landing_16x9_{transcribe,words_fix,build,stills}.py`
and `scripts/register_media.py`. Read this when the deliverable is 16:9 and page-bound rather than a reel.

## A 16:9 talking-head landing video, end to end (0919 «דף תודה», 19.09.26)

Two thank-you-page monologues (WhiteBoard + הבונקר) already cut by Alon as **Multi-camera clips**
(compound with a nested draft per camera, `cur_camera_track_id` per piece). Everything in
`scripts/landing_16x9_*.py` (transcribe → words_fix → build → stills); the build is idempotent
because it freezes Alon's main track to `draft_info.0919-base.json` on first run and rebuilds from it.

* **Routing without mics** (one speaker): every jump cut flips the camera (it hides the cut);
  inside a hold > 11 s an internal cut at a sentence start (else the longest pause) opens a 2.5–5.5 s
  camera-2 beat and returns; camera 1 keeps the floor until it has run 5 s. Result ≈ 65–70 % camera 1,
  median shot 4.5–6 s, max ≈ 15 s. Alon's own camera-2 pieces are forced.
* **Zoom on 16:9** is a slow drift, not a punch: 0.75 %/s, cap ×1.075, alternating push-in / pull-out
  per shot, CurveInOut, with PositionX/Y solved so the composited face stays put
  (`x = −(s−1)(2fx−1)`, `y = −(s−1)(1−2fy)`, face centres measured with YuNet through the nested crop).
  Keyframe `time_offset` is source time = `source_timerange.start + rel` (compound offsets included).
* **Captions**: donor is 16:9 project `0902` (bamberger size 10, y −0.6667, house effect); ≤ 4 words,
  single line ≤ 700 px (PIL@60 × size/10), ≥ 0.5 s where the width allows, never across a sentence
  mark or into a title window. Brand keyword ranges in the brand colour; Latin runs (WhiteBoard, AI,
  VSL) in `Heebo-ExtraBold` at 0.8× size — the house font has no Latin glyphs.
* **Title stacks**: phrase-anchored (not index-anchored — indices move with every word fix), 1–3
  lines centred at y +0.62, sizes 7.5/9.5/13 (half the 9:16 stack), pop-in keyframes + cached Fade
  Out, swoosh @0.35; the phrase's words leave the caption track (word contract) and the caption
  before the window ends 0.02 s before it opens.
* **B-roll** (Seedance 2.5 omni_reference, 1080p 5 s = 60 credits each): one persona card per video
  (nano_banana_pro), literal scenes of the persona per key sentence, muted, 1.06→1.0 settle, whoosh,
  never over the name card. Music: library bed for WhiteBoard, brand bed for הבונקר
  (`לו-פיי מתחת לדיבור`, looped with a 3 s acrossfade), ≈ 15–20 dB under the measured speech level.

### Round 2 on the same project — what Alon's five notes actually meant (20.09.26)

* **"הכותרות מעוצבות לא טוב בכלל … טקסט שנדרס"** was a *placement* problem, not a wrap problem: a
  centred stack on a 16:9 talking head lands on the speaker's face, and a pitch of `6.6 × size`
  between lines of *different* sizes lets the big line's box touch its neighbours. The fix is a
  **right-aligned block in the free column beside the speaker** (right edge 1830 px, box 760 px wide,
  top 205 px, under the logo), line boxes of `1.34 × em`, and **every line measured and shrunk** so it
  can never wrap — CapCut breaks a line at `line_max_width` (0.82 of canvas width = 1574 px here,
  read it off the material, don't guess). Replace pop-in *scale keyframes* with the cached
  Grow / Showing Up entrances: scaling a text segment enlarges its box and is itself a collision.
* **A title line containing Latin silently inherited the caption size** because `styled_ranges` had
  `CAP_SIZE` baked in. Any helper that builds style ranges must take the size *and* the font.
* **Installing a Google font for CapCut:** download the variable TTF from the `google/fonts` repo and
  cut static instances (`fontTools.varLib.instancer`, `wght` 600/700, `updateFontNames=True`) into
  `~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/`. Fredoka carries **Hebrew and Latin**,
  so a Fredoka video needs no Heebo fallback — but it renders ~1.5× wider than bamberger, so its sizes
  and width budgets are its own.
* **"בירולס לא מתאימים … רפרנסים של המערכת"**: when the script says "the system", show the system.
  Real screen recordings beat anything generated (`whiteboard-launch-video/screen-recordings/*.mp4`),
  and for a scene where a laptop merely *appears*, pass the real screenshot as an `image_references`
  to `nano_banana_pro` and ask for the interface to be reproduced faithfully. Brand colour comes from
  the brand LUT over the generated people shots (`lut3d=/tmp/wb.cube`, keep a `*.orig.mp4`).
* **"אתה מראה סרטון מהאולפן — באולפן אחר"**: never let a model invent a room you own photos of.
  Build the keyframe with the real room photo as a reference ("THE EXACT SAME studio … keep every
  detail identical"), then animate that keyframe as `start_image`. `cinematic_studio_3_0` at 1080p is
  50 credits per 5 s and holds the room; it also trips the "IN THE DARK" preset, so carry
  `declined_preset_id`.

## Round 3 on 0919 — one wrong constant, three "design" complaints (20.09.26)

Alon came back with what read as three separate design failures: a title colliding with a
caption, a title cut off outside the frame, and "the titles aren't luxurious or consistent".
They were one bug. **The 6 px-per-size-unit text calibration was measured on a 1080-wide 9:16
canvas, and CapCut scales text off the canvas width** — so on a 1920-wide landscape canvas every
glyph is 1.778× bigger in both axes. Widths came out 1.78× under, so lines ran off the right
edge; the line pitch came out 1.78× tight, so stacked lines sat on each other; and the name card
landed on the caption's own baseline and read as one run-on sentence.

```python
CANVAS_K = canvas_width / 1080
def width_px(txt, size, font): return _F60[font].getlength(txt) * size / 10 * CANVAS_K
def line_h(size):              return 6 * size * CANVAS_K
```

Two things generalise past this project:

* **QA the layout in pixels, not the timeline.** Every previous check passed — no overlaps, no
  gaps, nothing dangling — while two text blocks shared a baseline. Build a box per text segment
  (`x0,x1,y0,y1` in canvas px plus its time span) and assert: nothing outside the safe frame, and
  no two boxes that are on screen together intersect. That check is what turns "it looks messy"
  into a number you can fix.
* **The free column is a property of the framing, not a preference.** His head sits at x 700–1160
  in both cameras, so the only column free at every moment is x 1176–1786 — 610 px. Titles must be
  written to fit 610 px, which means short copy, not clever shrinking: measure every line and
  print the ones that don't fit rather than squeezing them to 70% and shipping them.
* **A title needs its own background.** The cut-off title at 0:18 was white text on a white
  screen-grab of the product. Generate a gradient scrim PNG (dark at the right edge, gone by
  mid-frame) and run it under every title, plus a fixed accent rule in the video's colour — that
  is also what makes eleven titles read as one designed family instead of eleven decisions.

**B-roll: a mascot pasted on a screen-grab is not a scene.** Round 2 shipped real screen
recordings with the BOARDi icon popping in over them; Alon's note was "I don't want screenshots of
the system with a BOARDi icon jumping in — I want BOARDi creating things inside the screens, a
student watching him work, a lecturer building a course easily". The fix was a **storyboard with
one world**: a written brand preamble (palette, lens, light, the real UI on every screen, BOARDi as
a flat 2D character that lives *inside* the screen and never in the room) pasted verbatim into
every prompt, then `nano_banana_pro` keyframes with the mascot PNG and a real UI screenshot as
`image_references`, reviewed as a contact sheet, then `seedance_2_5` in `omni_reference` mode with
the keyframe as `start_image`. 60 credits per 5 s 1080p clip — check `balance` and say how many
clips the budget buys before promising a count.

## The media panel is part of the delivery (22.09.26)

Round 3 landed well — *"הסרטון נערך ברמה גבוהה מאוד"* — and the one thing he asked for on top was
that the generated material stay reachable inside the project. See **Anything you generate belongs
in the project's Media panel** in SKILL.md; for 0919 that is 32 assets (5 BOARDi story clips, 7
bunker clips, 4 real system recordings, 7 earlier WhiteBoard clips, 2 music beds, 2 logos, the
mascot, and the scrim + two accent rules). Register them at the end of every build, not as a
favour at the end of a project.

## What the round-3 title system actually is

Numbers worth carrying to the next 16:9 project on this framing (speaker's head at x 700–1160):

| | value |
|---|---|
| title column | right edge 1786, left wall 1176 → **610 px of copy** |
| block anchor | always centred on y = 372, whatever the line count |
| line pitch | `6 × size × (canvas_width/1080) × 1.30` |
| sizes, matched cap heights | Fredoka (cap 0.70 em) 6.0 / 7.6 / 10.0 · bamberger (cap 0.60 em) 7.0 / 8.9 / 11.7 |
| entrance | `in:Showing Up` 0.45, staggered 0.09 s per line, `out:Fade Out` 0.3 |
| name card | left edge 150, lines at y 600 and 700 — the caption band is up to 1244 px wide (x 338–1582), so the escape from it is vertical, never horizontal |
| furniture | a 1920×1080 gradient scrim PNG (dark at the right edge, gone by mid-frame) + a 10 px accent rule at x 1814, both faded with `KFTypeAlpha` keyframes |

The scrim exists because a white kicker over a white screen-grab of the product is invisible; the
fixed rule and fixed anchor are what make eleven separate titles read as one designed family.

## Two clarifications a fresh reader asked for (22.09.26)

* **The caption width ceiling.** `CAP_MAX_W` is 700 *model* px, i.e. `700 × 1.778 = 1244` real px on
  this canvas — the build multiplies it out, and the round-3 QA boxes use the real number. A caption
  therefore spans up to x 338–1582, which is why the name card escapes it vertically, not sideways.
* **The brand LUT never touches the adjust track.** His grade lives on the adjust segment and stays
  byte-identical (the diff after every write proves it). The WhiteBoard LUT is baked into the
  generated people clips with `ffmpeg -vf lut3d=<cube>:interp=tetrahedral` (keep a `*.orig.mp4`);
  the real system recordings and the BOARDi story clips are already on-palette and get no LUT.

## v2 — the rebuild under the creator grammar (22.09.26)

Alon duplicated nothing himself; `scripts/duplicate_draft.py "0919" "דפי תודה ו-VSL v2" --write`
made the copy (folder = display name, new ids, registry entry, media paths rewritten to the copy) and
the build ran on it with `WORK=~/Movies/reel-captions-work/landing-16x9 DRAFT="דפי תודה ו-VSL v2"
BASE_NAME=0919`. `BASE_NAME` matters: the frozen original cut is `draft_info.0919-base.json` and it
travels with the copy — freezing the *copy's* current draft as a base would route on top of routing.

**The word cache is not durable unless you make it.** The session scratchpad that held
`0919_words_fixed.json` was wiped between rounds, so v2 had to re-transcribe. A re-transcription
drifts by a word here and there and every drift is a caption Alon already corrected once —
`scripts/landing_16x9_words_from_captions.py` aligns the fresh words to the **approved caption
track of the source project** and takes the approved token wherever they disagree one-for-one (15
substitutions on 0919), then prints the spots that are not one-for-one for a human look (11 more
fixes by hand). Anchors (`find_phrase`) now fall back to a fuzzy window match (≥ 0.66) and print
what they matched, so a title does not die on «או אולי» → «אולי».

What changed on the timeline, each traceable to `creator-styles.md`:

| Grammar | v2 implementation | Measured |
|---|---|---|
| no hold past ~7 s; punches between two sizes | `MAX_HOLD 7`, walk never merges past it; punches on sentence starts (or the longest pause in a long hold) between 1.00↔1.06 / 1.03↔1.09, 0.45 s, ≥ 3 s apart; intro zoom-out kept | 96 shots, median 4.0 s, max 7.1 s, 13.4 cuts/min (+14 b-roll, 8 cards ≈ 17 events/min); 208 scale keys |
| one huge keyword | headline 12 (Fredoka) / 14 (bamberger), kicker unchanged, shrink floor 0.70, copy shortened where it still failed («לראשונה» / «בישראל» as two lines) | 0 outside the frame, 0 overlapping boxes |
| reference material is framed | the real system recordings run inside a rounded card with a shadow on a blurred, darkened plate of themselves (`framed_asset()`: ffmpeg `alphamerge` against a PIL mask) | 3 framed inserts, 5 BOARDi story clips full-frame |
| chapters are announced | 4 + 4 full-frame cards drawn with PIL (`rtl()` reverses tokens — no raqm here), 1.5 s, in the first free slot before the section's title (else right after it), never over the name card, a title or b-roll; whoosh on `sfx chapter` | 7 cards placed, 0 clashes; wb-02 («איך עושים מזה כסף?») had no free slot between its title and the b-roll and was skipped — reported, not forced |
| lower-third with a rule | a horizontal accent underline between name and role (`ccstudio-hrule-*.png`, `scale.y` = 4 px) replaces the vertical bar beside the name | — |
| bed under the voice, ducked under overlays | `KFTypeVolume` keys on the bed: ×0.71 under every b-roll clip and chapter card, 0.3 s ramps | 88 keys over 21 covers |

Two mechanics worth keeping: the b-roll list is placed **sorted by time**, because the "≥ 1 s after
the previous clip" rule reads the previous clip and list order silently dropped a slot; and a
`busy` list (name card, b-roll, title windows) decides where a chapter card may land — the first
version put a card on top of a title and a clip at 212 s and the stills showed it.

Not done in v2, and why: no new generated b-roll (47.5 credits, a clip is 60); no transitions
(only Glare II / Black Fade / Delay Zoom / Old Film II are cached on disk and none fits a hard-cut
house style); loudness is his export's to measure (`ebur128`, target ≈ −15 LUFS, LRA ≤ 8).

**A card is a plate — every pixel opaque.** The first chapter cards drew their grid with
`(255,255,255,10)` on an RGBA image; PIL's `line` replaces pixels instead of blending, so each grid
line became an alpha-10 slit and CapCut showed the speaker through it ("הרקע הכחול מחורר"). Cards
are now RGB (`scripts/landing_16x9_cards.py`), any translucent line is a colour mixed by hand, and the
file is written to a temp name and `os.replace`d so a regeneration is safe while CapCut holds the old
one. Check `"A" in Image.open(card).getbands()` is False before shipping a plate.

## v2.1 — "מעבר למשחקי קיפריימים בקושי ראיתי הבדל" (22.09.26)

Alon's four notes on v2, and what each one changed:

1. **"פרק 1 בלי פרק 2."** A skipped chapter is a defect, not a report line. Chapter cards are now
   placed *first* (busy = name card + title windows only, four candidate slots) and the b-roll
   yields to them — a clip that would overlap a card is trimmed to end before it (if ≥ 2 s remain)
   or pushed to start after it. All eight cards land.
2. **"בקושי ראיתי הבדל."** 6 % snaps over 0.45 s read as nothing on a 1920 canvas. Now 8 %
   (1.00↔1.08 / 1.04↔1.12), 0.35 s, ≥ 2.5 s apart — and every overlay moves, see 4.
3. **"חלק מהבירולס לא מדויקים למלל."** The map was re-read sentence by sentence: «בשיעורי זום
   מוקלטים» gets a recorded lesson on a laptop (not the course builder); «למרצה לבנות את הקורס»
   gets the lecturer clip; the feature list «כל זה אפשרי בתוך WhiteBoard» gets the real builder,
   framed; «ואתם תקבלו אחוז» gets the dashboard shown to a client. Before assigning a clip, grab a
   frame of it (`ffmpeg -ss 2 -frames:v 1`) and put it next to the sentence — that is how wb2/wb42
   were confirmed literal and wb5/wb6 judged acceptable.
4. **"לא השתמשת באלמנטים של תנועה בשכבות."** One helper, `motion(seg, dur, base, entry, drift,
   exit_)`, writes Position/Scale/Rotation keyframes (CurveInOut) on any overlay, on the segment's
   own clock (+ source offset for b-roll):
   * captions: cached `Fade In` / `Fade Out` 0.12 s on every card;
   * titles: `Fade In` + slide from the right (Δx 0.07, scale 0.94→1) over 0.38 s, a slow drift
     while held, slide-out + `Fade Out`; lines still staggered 0.09 s;
   * name card: slide from the left + fade, drift, slide-out;
   * b-roll: slide from the right + 1.12→1.0 settle, slow push to 1.05, punch to 1.08 in the last
     0.25 s; framed inserts rise from below (Δy −0.22) instead;
   * chapter cards: zoom-through 1.30→1.0 with −3°→0 rotation, drift +4 %, exit to 1.14/+1.2°;
     a transparent **HUD layer** (`hud_overlay()`: accent corner brackets, faint diagonals, dots)
     rides on top with *counter*-motion (1.12→1.0, +4°→0) so the pair reads as depth — the
     "3-D / futuristic" feel without any effect CapCut cannot express from JSON;
   * logo drops in (Δy +0.06, scale 0.85→1) over 0.6 s.
   `KFTypeRotation` is proven (786 uses in his drafts); non-uniform *animated* scale is not, so the
   accent rule still slides rather than grows.

Verify motion on **two** stills per element — entry frame and settled frame — not one; a single
still cannot show that anything moved.

## v2.2 — one device at a time (22.09, after the first render Alon looked at)

Alon exported v2.1 and sent four notes: *"בלאגן בטיימליין, יותר מדי שכבות ובלאגן בעין"*, *"קי פריימים
אגרסיביים מאוד בבי רולס שלא לצורך"*, *"הכניסה של הפרקים מהירה ולא נעימה, אי אפשר באמת לקרוא וגם
הכיתוב של שם הפרק לא רלוונטי"*, *"בגדול העריכה הקודמת הייתה יותר טובה"*. Measured on the render
(`ffmpeg` frames every 0.2 s around each event, scene cuts, ebur128):

| note | what the render showed | v2.2 |
|---|---|---|
| too many layers | 20 tracks: an empty `boardi`, scrim + rule as two tracks, a HUD track, 3 SFX tracks, a 4th title track for one segment; on screen 15.6–18.4 s = card → head for 0.25 s → title → b-roll | 14 tracks: scrim+rule baked into one **plate PNG per block height** (`ccstudio-title-plate-<key>-<h>.png`, ~15 files), brackets baked into the card, one `sfx` track with `add_sfx()` trimming the previous tail, 3-line title copy, empty tracks never assembled |
| aggressive b-roll keys | every clip entered from 112 % with a 0.16 slide in 0.45 s and left on an 8 % punch in 0.25 s; framed inserts dropped in from y −0.22 | footage: 104 % → 100 % over 0.6 s, +3 % across the hold, **plain cut out**; framed inserts: alpha fade only (`motion(..., fade=(0.35, 0.3))`) |
| chapters fast / irrelevant | 1.6 s on screen, 0.5 s zoom-through + 3° rotation + counter-moving HUD → < 1 s to read; and every card was slid 1.85 s ahead of its title to dodge the title window, so all 8 landed **inside the previous sentence** | 2.8 s, fade 0.4 s each way, 4 % drift, no rotation; **the card sits on the last pause ≥ 0.35 s before its opening sentence** (word gaps, not caption gaps — title words are not captioned); if none within 7 s it ends 0.2 s before the sentence. Never after it. The **title yields to the card** (starts 0.4 s after it leaves and holds ≥ 2.6 s, clipped to the next title); b-roll yields with 1 s before / 2 s after, waits only while its own sentence is still running, else is dropped and reported |
| "the previous edit was better" | v2's grammar was fine; v2.1 stacked every motion device on every layer at full amplitude after the note "no motion at all" | keep v2's structure; titles and name card move half the distance with no drift; captions keep their fade |

Two things worth keeping from the measurement itself: the exported file came out at **−23.7 LUFS**
(CapCut export, his voice level — say it, do not "fix" it in the edit), and a caption-gap search
is not a pause search, because words under a title carry no caption. Pauses come from the word list.

**Media panel, second lesson (22.09).** CapCut rewrites the `file_Path` of every file inside the draft
folder to `./name` the first time it saves the project. A registrar that compares absolute paths then
adds every asset again (v2.2: 160 entries, 45 duplicates). `register_media.py` now compares resolved
paths and folds duplicates; run it after every write regardless.
