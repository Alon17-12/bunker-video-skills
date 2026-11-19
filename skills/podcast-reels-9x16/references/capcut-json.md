# CapCut draft JSON — the encodings you need

Everything here was read off real CapCut-authored projects on this machine and
confirmed against a render. Where a value looked ambiguous, the note says how it
was pinned down. Do not "improve" any of it from memory.

## Contents

- [Geometry: scale and transform](#geometry-scale-and-transform)
- [Split screen](#split-screen)
- [Keyframes](#keyframes)
- [Opacity as a correctable multicam](#opacity-as-a-correctable-multicam)
- [Text: colour, effect, spacing](#text-colour-effect-spacing)
- [LUT and the adjust track](#lut-and-the-adjust-track)
- [Project identity and the registry](#project-identity-and-the-registry)

## Geometry: scale and transform

Canvas for reels is 1080×1920. `clip.scale` **1.0 means fit-inside**, so 16:9
footage rendered on a 9:16 canvas at scale 1.0 is 1080×607.5. Covering the
canvas therefore takes

```
fill = 1920 / 607.5 = 3.1604938…      # reframe.fill_scale(1920, 1080)
```

`clip.transform` is in **half-canvas units**: x is `pixels / (1080/2)`, y is
`pixels / (1920/2)`, and **+y is UP**.

> Pinned down by the caption track: captions sit at `transform.y = -0.2131`,
> which is `-0.2131 × 960 = -204.6px` below centre → centre at 0.607 of the
> frame height. Measured on a screenshot: 0.605. Negative is down.

Two different things get called "position" and they do **not** share units:

* **A number Alon reads off CapCut's panel** → stored = panel ÷ *full* canvas
  dimension. `X=482` on 1080 → `0.4463`. Enter it verbatim, touch nothing else.
* **A pan you compute yourself** from a face at fraction `fx` of the source →
  `-(fx - 0.5) × rendered_width / (canvas_w/2)`. Don't hand-roll it, call
  `reframe.transform_x()`.

## The material's own `crop` — and how to prove the geometry

`clip.scale`/`clip.transform` are only half the story. A `materials.videos[]`
entry can carry its own **`crop`**, four normalised corners plus a `crop_ratio`,
and everything above is then computed on the *cropped* rectangle, not on the
file's 1920×1080:

```
cw = (upper_right_x − upper_left_x) · width      # 0.2402…0.7010 of 1920 → 884.8
ch = (lower_left_y  − upper_left_y) · height     # 0.1807…1.0     of 1080 → 884.8
f  = min(CW/cw, CH/ch)                           # fit-inside, as always
rendered = (cw·f·s, ch·f·s)
centre_px = (540 + x·540, 960 − y·960)           # +x right, +y up
```

When you render a check frame by mapping canvas → source, **clamp the source
rectangle to the crop**, not to the file. Clamping to `0…1920 × 0…1080` shows
material CapCut never displays, and the error is not subtle — it moved a split
seam 130px up the frame and quietly poisoned a whole face scan built on it.

Two pieces of ground truth live in the draft folder, and they cost nothing:

* `attachment_pc_common.json` → `reference_lines_config.horizontal_lines` is the
  guide Alon dragged, in canvas fractions. On a split he snaps it to the seam.
* `draft_cover.jpg` is a frame **CapCut rendered itself**. Find the strongest
  row gradient in it and in your own composite; if they disagree by more than a
  few pixels, your geometry is wrong, not CapCut's.

Do this before you trust any measurement derived from the canvas — a face scan,
a caption band, a logo-clearance number. All of them inherit the error.

## Split screen

Each half of a 9:16 canvas is 1080×960. Covering one half takes exactly half the
full-frame cover scale:

```
split_scale = fill / 2 = 1.5802…      # 607.5 × 1.5802 = 960.0, width 1706.6 ≥ 1080
top    half:  transform.y = +0.5      # centre at y=480  → 480px above centre
bottom half:  transform.y = -0.5      # centre at y=1440
off-screen below (for a slide-in): transform.y = -1.5
x for either half: the full-frame pan ÷ 2 (the rendered width halved with it)
```

Base layer takes the top, the overlay layer takes the bottom.

Those ±0.5 are not constants — they are `±(607.5/1920)·s`, the value that pins a
half's edge to the seam. Write them as a function of the scale, or a keyframed
push-in slides both halves off the seam and opens a black gap.

Equal halves are only the default. When something fixed has to fit — a caption
band, a logo — solve the scale instead of moving the fixed thing: the lower
face's forehead lands at `960 + 607.5·s·fb`, where `fb` is its height as a
fraction of the source. Bigger `s` pushes it down; the cost is a tighter crop
(visible width is `1/s` of the source).

But reach for that only once the full-frame shots have been lifted (see below) —
they set where the caption band can sit, and a band raised there usually leaves
the split with clearance to spare. A split scale chosen to clear a caption
looks like a compromise; one chosen for how the two faces read looks deliberate.

## Full frame: the top pin

At `s = fill` the image is exactly canvas-height — zero vertical freedom, so
`transform.y` must be 0 and a face lands wherever the camera op put it. Scale up
and the slack opens symmetrically; spend all of it upward and you get the
mirror of the seam pin:

```
y = 0.3164·s − 1        # bottom edge flush with the canvas bottom
chin lands at  1920 − 607.5·s·(1 − fc)      fc = chin as a fraction of source height
s ≥ (1920 − chin_target_px) / (607.5·(1 − fc))
```

Two things follow that are easy to get backwards. Pushing in **raises** the
face here (the pinned edge is below it), so the worst frame of a shot is its
first, not its last — solve for the shot's starting scale. And `y` is a
function of `s`: keyframe the scale and leave `y` constant and the frame drifts
off the pin exactly as a split drifts off the seam.

Enter and leave on a **hard cut** — one keyframe a single frame apart (16 667µs at 60fps) is a cut
as far as the render is concerned. A slide-in looks smooth in theory and shows a
black half in practice.

Write the window as exactly four keyframes on the layer that also carries the
full-frame shots, and derive all four from the overlay segment's own `[a, b)`:

```
a-1f   full        the last frame before the other half exists
a      split       first frame of the split
b-1f   split       last frame the other half is on screen
b      full        the overlay segment is over; be full again on this very frame
```

The two boundary frames are the whole game. Put the return-to-full at `b+1f`
instead of `b` and one frame renders half-black; leave it out entirely and the
layer ramps from half to full over however long it takes to reach the next
keyframe — seconds of a shrinking image over black. Half-frame geometry must
last exactly as long as the other half does, not one frame more or less.

For the same reason, a pass that multiplies every keyframe in a window (a
zoom tweak, a scale bump) must **exclude the boundary keyframes**, or it
converts the hard-cut exit into one more split keyframe and the cut disappears.

## Keyframes

`segment.common_keyframes` is a list of `{property_type, keyframe_list}`. Real
CapCut writes `KFTypePositionX`, `KFTypePositionY`, `KFTypeScaleX`,
`KFTypeRotation` together (ScaleY is linked); write all five and nothing
surprises you.

**`time_offset` is in SOURCE time** — `source_timerange.start` plus the offset
into the clip, *not* 0-based per segment. Hand-built 0-based keyframes silently
land in the wrong place, or nowhere.

Values are absolute, in the same units as `clip.scale` / `clip.transform`.
`curveType: "Line"` with zero control points is a clean linear ramp.

**Ease («Easing» in CapCut's keyframe menu)** — the only encoding the menu shows as Easing, read off
Alon's hand-set keys (16.11.26): both keys of an interval `FreeCurveInOut`; the start key's
`right_control.x = 0.42·Δt − 1`, the end key's `left_control.x = −0.42·Δt` (µs, y 0), and the end key
gets a fresh `graphID`. Bare `CurveInOut` with zero controls and handle-less `FreeCurveInOut` both
show as **Linear** — Alon rejected both («אין ease»).

Before the first keyframe and after the last, the value is **held**. So a
property whose first keyframe sits mid-clip is that value from the clip's start
— which is how a split-screen position leaks backwards over a whole shot. Always
anchor a keyframe at the segment's own start.

Keep every `time_offset` inside `[source_timerange.start, +duration]`. Sub-frame
rounding drifts outside it; CapCut clamps, but clamp it yourself.

Every keyframe carries an **`id`**, and so does each `common_keyframes` entry.
Clone a keyframe to make a new one — the obvious way to inherit `curveType` and
the rest — and you clone the id too. CapCut tolerates that until its next save,
then collapses everything sharing an id onto a single timestamp and the curve is
gone. Re-issue `str(uuid.uuid4()).upper()` on every object you create, and
assert `len({k["id"]}) == total` before writing.

Because `time_offset` is source time, a ripple trim leaves it untouched. So a
good version's geometry can be re-mapped onto an edited timeline: evaluate the
old curve at the new `source_timerange` in and out, keep every interior key, and
the shape survives.

## Opacity as a correctable multicam

**This is the delivery format, not one option among several** — Alon asked for it
explicitly after the last build. Do **not** delete the frames of the camera you
are not using. Keep the second angle covering every clip end to end, split at the
cut points, with the unwanted pieces at `clip.alpha = 0.0`. CapCut exposes that
as Opacity, so correcting the edit becomes a slider:

* reveal a hidden shot → Opacity 0 → 100
* drop a cut you dislike → Opacity 100 → 0
* move a cut → ⌘B, then Opacity per piece

No footage is ever lost, and the splits already sit inside silences.

The main video track **cannot hold gaps** — CapCut ripple-closes them on open.
Only the upper track can be sparse, and here it is not even sparse, just
transparent.

Three properties of this layout that are easy to get wrong:

* The **bottom layer never flips**. It carries one camera at `alpha 1` for the
  whole range as the fallback picture. A hole punched in it renders black
  wherever the top is hidden too.
* Alpha is a **cut**: a constant `clip.alpha` of 0 or 1 per piece, which is what
  the Opacity field shows. A `KFTypeAlpha` ramp longer than a frame is a fade,
  and it hides the boundary from the panel he edits in.
* **`attribute: 1` on a video track means the track is muted**, regardless of
  each segment's `volume`. Both routing layers need `attribute: 0` and
  `volume: 1` for the muxed isolated mics to be heard — and since the two files
  carry *different* mics, nothing doubles.

## Text: colour, effect, spacing

A caption is a `materials.texts` entry whose `content` is a JSON **string**:

```json
{"text": "אתה גאון",
 "styles": [{"range": [0, 8],
             "fill": {"content": {"solid": {"color": [0.957, 0.78, 0.059]}, "render_type": "solid"}},
             "useLetterColor": true,
             "effectStyle": {"id": "7336838446625082629", "path": "…/Cache/effect/…"},
             "size": 20,
             "font": {"path": "…/Fonts/bamberger-grunge-bold-fm.ttf", "id": ""}}]}
```

plus material-level `text_color`, `border_color`, `use_effect_default_color`.

### `useLetterColor` — the flag that costs you a day

When a style carries an `effectStyle` (a CapCut *text effect*), **CapCut ignores
`fill` unless the style also sets `useLetterColor: true`.** Without it every
caption renders in the effect's own colour — white — no matter what `fill` and
`text_color` say. Every hand-coloured caption on this machine has the flag;
captions cloned from a white template do not, because white *is* the effect
default and nothing looked wrong.

Nine yellow captions rendered white through two rounds of "verified" because of
this. Whenever you set a colour, set `useLetterColor: true` on every style, and
diff the finished material field-for-field against a caption the user coloured
by hand in one of their own projects.

### Two colours on one card

Split the text into lines with `\n` and give each line its own style whose
`range` covers that line's character span (remember the newline occupies one
index). One line, one colour — never two colours inside a line.

Take the card's text from the caption itself. Rebuilding it from word tokens
restores the punctuation the reel style deliberately strips.

### Vertical position

`segment.clip.transform.y` on the caption segment, in half-canvas units, +y up:

```
centre_fraction = (1 - transform.y) / 2          # of the frame height, top-down
transform.y     = 1 - 2 * centre_fraction
```

The caption band is `centre ± height/2`, and the rendered height is roughly
`(ascent + descent) / 1920` measured with PIL at the calibrated pixel size —
0.046 for `font_size` 20 in this house style.

Do not inherit this value from a donor template. The donor's framing is not
yours, and a value that cleared faces in one project lands on the jaw in the
next. Measure with `scripts/face_scan.py` and derive it.

### Wrapping — CapCut decides, and it decides badly

`line_max_width` (0.82 here) is the fraction of the canvas a line may occupy
before CapCut wraps the text itself. It wraps at whatever column runs out of
room, **including mid-word**, so an overlong caption can render as
«משקיעים היא מאוד פשוט» over a lone «ה».

So the chunker, not CapCut, has to guarantee the fit. Measure the rendered width
with PIL over the real `.ttf` (never a character count — 'w' is nearly three
times an 'i') and split the card in two when it overflows. See
`pipeline.md` → *Chunking*.

A caption that is two lines should be two lines **because you put a `\n` there**
— for the two-speaker colour split — and never because CapCut ran out of width.

### Line spacing

`line_spacing` defaults to `0.02`, which is too airy for stacked reel captions.
`-0.18` is the tightest value that appears in a hand-made project here and is
the house value. Apply it to every text material, captions and title cards
alike.

## LUT and the adjust track

An imported LUT is an `materials.effects` entry of `type: "lut"` referenced from
an **adjust-track segment**'s `extra_material_refs`:

```json
{"type": "lut", "name": "Bunker.cube", "value": 1.0, "visible": true,
 "resource_id": "7501974767453474064",
 "path": "…/User Data/Resources/Lut/Bunker/Bunker.cube;/Applications/CapCut.app/Contents/MacOS/../Resources/DefaultAdjustBundle/merge_all_adjust_color"}
```

The path is two paths joined by `;` — the cube and CapCut's merge bundle. `value`
is intensity, 0–1. Custom LUTs live in `~/Movies/CapCut/User Data/Resources/Lut/<Name>/<Name>.cube`.

A draft built from a donor template inherits **that show's manual grade** on the
same adjust segment (brightness/contrast/saturation/highlight/shadow/temperature/
light_sensation/vignetting). Putting a brand LUT on top of another show's grade
does not produce the brand look. Zero those `value` fields — the sliders stay in
the panel, so it is one drag to bring any of them back — and say that you did.

Parametric keyframe grading (`KFTypeSaturation` and friends) does **not** render.

## Project identity and the registry

* `root_meta_info.json` holds the project list. CapCut reads it **at launch**, so
  a project added while it runs is invisible until it restarts.
* CapCut re-derives `draft_name` from the **folder name** on every save. Writing
  the name into `draft_meta_info.json` and `root_meta_info.json` works until the
  next save, then reverts. The durable fix is to rename the folder and update
  `draft_fold_path`, `draft_json_file` and `draft_cover` in both files.
* CapCut also **rescans the drafts directory**. Removing a registry entry does
  not hide a project; move the folder out of `com.lveditor.draft`.
* CapCut portablises media inside the draft folder to
  `##_draftpath_placeholder_<uuid>_##/file`. Resolve that prefix to the draft
  folder before any `os.path.exists` check, or you will "discover" 62 missing
  files that are all present.
* **Never clear `extra_material_refs` on a video segment.** One ref can point at
  the `drafts` material (a multicam subdraft); without it the clip goes red
  "Media Not Found" and CapCut garbage-collects the material on its next save,
  so the damage compounds.
