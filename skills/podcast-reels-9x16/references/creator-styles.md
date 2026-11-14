# The creator grammar — measured off six reference videos (22.09.26)

Alon asked for the edit to reach the level of the top business-content creators and sent six
references. Everything below was **measured** (scene-change detection over the first 4 minutes,
24-frame contact sheets, EBU R128 loudness), not remembered. Cadence numbers are per-video, so
read them as a range, not a target.

| Creator | Format | Cuts / min | Median shot | Loudness (I / LRA) | Signature |
|---|---|---|---|---|---|
| יובל צרפתי (Personal Business) | 2-person interview, white cyc | 13.5 | 2.3 s | −15.2 / 8.0 | one huge word per super, red on white, glow; chapter progress bar |
| מתן ניסטור | solo talking head, living room | **25.2** | 1.2 s (p25 0.16 s!) | −15.1 / **1.6** | framed personal photos, flash/whip, 3-D word, yellow keyword captions |
| Dan Martell | solo, wood studio | 23.5 | 2.2 s | −16.3 / 4.2 | lower-third name + cyan underline, top-down whiteboard b-roll, framed video calls |
| Kallaway | solo, dark studio | 5.0 (graphic-dense) | 13 s | −14.0 / 1.5 | purple orb + node diagrams, small definition cards on a scrim, grid-fill data viz |
| Philipp Humm | loft + whiteboard | 7.5 | 4.4 s | −20.9 / 7.0 | teal pills sliding in, PIP of a reference clip in a brand frame, kinetic words, letter badges |
| Vinh Giang | solo, neon studio | 10.5 | 3.1 s | −15.9 / 5.9 | keyword pairs beside the head, sticky-note cards, full-frame "paper" misconception cards, PIP under marker circles |

For comparison, 0919 after round 3: WhiteBoard 10.8 cuts/min (median 4.5 s, longest 12.3 s),
Bunker 8.7/min (median 5.9 s, longest 15.3 s) — camera cuts only, before b-roll. The references
sit at 10–25 for a talking head with a median of 1.2–3 s; the slow ones (Kallaway, Humm) buy
their pace with graphics instead of cuts. **Nobody holds 12–15 s on one framing.**

## What they all do (the grammar)

1. **Text lives where the face isn't.** Supers sit in the top band or in the free column beside
   the head; captions, when burned, sit bottom-centre and nowhere else. Nothing overlaps a face.
2. **One huge keyword, one small line.** A super is 1–3 words in the accent colour at 2–3× the
   caption size, with an optional small white kicker. יובל puts a single spoken word («אבל»,
   «רגע», «כי») on screen at moments — that is a rhythm device, not a subtitle.
3. **One accent colour per brand**, used only for the keyword: red (יובל), yellow (ניסטור),
   cyan (Martell), purple (Kallaway), teal (Humm), yellow (Giang). Everything else is white.
4. **Reference material is framed, never raw.** A photo, a video call, a clip from another show,
   a document: rounded card or phone mockup, drop shadow, on a dark scrim or blurred plate, often
   with a name card on the frame (Humm's Anne Hathaway panel, Martell's Tony Robbins lower-third,
   ניסטור's 9:16 photo grid). A full-frame raw screen-grab is the one thing none of them do.
5. **People get a lower-third with a rule.** Name on line 1, role on line 2, a thin accent
   underline (Martell) or a framed panel (Humm). Ours: name card + accent rule, same idea.
6. **Chapters are announced.** A full-frame card (dark grid + italic serif for Martell; cream
   paper + serif for Giang; navy "#2 מה היו הפחדים" for ניסטור) or a persistent progress bar
   (יובל). 1–2 s, over the speech, with a whoosh.
7. **B-roll is literal.** Whiteboard being written (Martell, Humm), the actual book, the actual
   photo of the actual person, the actual building. No metaphors — the same rule Alon wrote for
   0910 (`feedback_alon_broll_literal_scenes`).
8. **Two or three framings, alternated.** Wide / medium / close, cut on sentence starts; punch-ins
   between two fixed sizes, not drifts. ניסטור adds a flash or blur whip on the punch.
9. **Audio is loud and flat.** −14 to −16 LUFS integrated, LRA 1.5–8 — voice compressed, a bed
   ~18–22 dB under it, a whoosh/click on every graphic. Humm at −20.9 is the outlier and sounds
   quiet next to the others.
10. **The grade is a signature.** Cool monochrome (יובל), warm (ניסטור, Martell), dark + neon
    (Kallaway, Giang), teal (Humm). Consistent from first frame to last; the background is
    always darker or softer than the face.

## Four Hebrew 9:16 reels — measured 23.09.26 (`video-breakdown`, batch 2026-09-23-batch-1)

The six above are long-form 16:9. These four are the format we actually ship: Hebrew vertical
reels, 45-73 s, one talking head. Measured by `~/.claude/skills/video-breakdown` (OpenCV cut
detection, numpy STFT, Whisper), not remembered. Full evidence and per-video rules live in
`~/video-breakdown/2026-09-23-batch-1/`.

| Creator | Length | Cuts / min | Median shot | BPM | Bed under speech | wpm |
|---|---|---|---|---|---|---|
| עדן בלי | 45.7 s | 14.4 | 4.4 s | 69 | −21 dB | 204 |
| עומר אורח S | 73.1 s | 20.5 | 2.1 s | 117 | −12 dB | 170 |
| ניתאי נקל | 57.0 s | 22.1 (+~6 missed slide transitions) | 1.0 s | 144 | −16 dB | 195 |
| רוני גרין | 53.2 s | 39.4 | 1.0 s | 134 | −16 dB | 186 |

Cut cadence for a **reel** runs 14-39/min against 10-25 for long form, and the median shot drops
to 1.0-2.1 s for three of the four. Speech is 170-205 wpm — faster than a podcast, which is why
caption cards of 2-5 words change every 1.5-3.5 s.

**The five that all four share — apply these by default to every Bunker/client reel:**

1. **The hook is one shot with a layer on it.** Three of the four cut ZERO times in the first
   3 s; the energy comes from a giant super or a graphic that is already on screen at frame 1
   (עדן's thumbnail grid is up before he speaks). Never open on a camera cut.
2. **SFX arrive as a burst in one place, not on every cut.** 4-5 transient hits inside 1.3-3.3 s,
   parked on either the hook (רוני, ניתאי) or the CTA (עדן — 5 hits in 2.3 s under the profile
   card). Only 4-30 % of cuts carry a hit at all. A whoosh on every graphic is a long-form habit;
   in a reel it reads as noise.
3. **The talking head is still; the layers move.** Three of the four hold a static camera on a
   static speaker for the whole reel — רוני has no zoom and no punch across 53 s. Pace comes from
   the b-roll/graphic layer above the head. Only ניתאי moves the camera itself (handheld).
   ⚠️ This is in tension with our house punch-in rule (SKILL.md § house numbers, 15-25 %/s then
   1.5 %/s). Unresolved — Alon likes the push-in. Do not drop punches on his projects without
   asking; the reference point is that four creators earn their pace without one.
4. **B-roll is one-to-one with the script**, 1-1.5 s per noun/verb — literal (ניתאי's real
   lifestyle footage, עומר's screen recordings) or *staged-prop metaphor* (רוני: a glass desk
   standing in the sea, a colander holding four miniature houses, a sharpener ringed by six
   pencils). The staged prop is a third road between `feedback_alon_broll_literal_scenes` and the
   metaphors he rejected on 0910: the object is real and photographed, the metaphor is in the
   staging. רוני's cutaways sit on the *feeling* of the moment, not on a noun.
5. **Two tiers of text.** Regular caption at 2-5 words on one line, white, centred; plus one
   giant keyword on each turning point, roughly every 9 s. Only רוני does the second tier — and
   it is the single most distinctive thing in the batch.

**Bed level:** these reels sit 12-21 dB under the voice (median ≈16), against the 18-22 dB the
long-form references use. A reel's bed is allowed to be louder.

## What CapCut can and cannot do from the draft JSON

Measured against Alon's own cache on this machine (22.09.26): the things that exist in his
drafts are usable as donors; the things that don't need one manual use in CapCut to cache.

| Device | CapCut, via JSON | How |
|---|---|---|
| keyword super, kicker + headline | ✅ | text materials, per-range `styles`, `useLetterColor`, `line_max_width` |
| text entrances | ✅ proven on text: Fade In, Grow, Showing Up; exit Fade Out | `references/text_anim_donors.json` — clone the wrapper, set `duration` |
| overlay entrances (b-roll, PNG cards) | ✅ cache on disk: Dissolve, Zoom In, Zoom Out, Zoom 1/2, Mini Zoom, Swoosh | same donor file; `material_type` sticker/video — use them on b-roll and cards, not text |
| entrances that appear in his old drafts but whose cache is gone | ⚠️ Bounce In, Slide Right, Blur out, Typewriter, Tremble… | one manual use in CapCut re-caches them; a donor whose `path` is missing renders nothing — check `os.path.exists` before cloning |
| translucent / italic light line | ✅ | `global_alpha`, `italic_degree`, `border_width 0`, no `effectStyle` |
| lower-third + underline rule | ✅ | two text lines + a rule PNG scaled non-uniformly (`scale.x ≠ scale.y`) |
| scrim behind text | ✅ | a full-canvas gradient PNG on a video track under the text, alpha-keyed |
| framed insert / PIP / phone mockup | ✅ | composite the clip into a rounded-corner card with ffmpeg (`geq`/PIL mask), place at scale ≈ 0.34–0.5 beside the head |
| chapter card | ✅ | a PIL PNG (Hebrew drawn locally — never generated) 1.4–2 s on a video track, whoosh |
| progress bar / dots | ✅ but fiddly | one PNG per state, or one PNG + keyframed position |
| cut transitions | ✅ cache on disk: **Glare II, Black Fade, Delay Zoom, Old Film II**; ⚠️ Mix, White Flash, Zoom Snap, Pull in appear in his drafts but their cache is gone | `references/transition_donors.json`, referenced from the outgoing segment; re-cache by one manual use |
| flash / blur whip on a punch | ✅ Glare II (a light-leak flash) on the punch; ⚠️ a hand-made flash needs a white PNG + `KFTypeAlpha`, unverified in his drafts | prefer the cached transition |
| punch-in / hold / drift | ✅ | `KFTypeScaleX/Y` + Position keyframes, source-time offsets |
| speed ramp | ✅ | `materials.speeds` on the segment (unexplored here) |
| blur / vignette on a plate | ✅ cached video effects Blur, Vignette | `materials.video_effects` on an effect track |
| stickers (arrows, circles, censor) | ✅ cached: circle & arrow, three white arrows, blur censored | `materials.stickers` |
| 3-D extruded text (ניסטור «ברחוב») | ❌ | render it as a PNG/MP4 elsewhere and overlay |
| node diagrams, orb, grid fills (Kallaway) | ❌ native | draw with PIL frame-by-frame → MP4, or Higgsfield; overlay |
| sidechain ducking | ❌ | `KFTypeVolume` keyframes on the bed pieces (×0.71 = −3 dB under b-roll) |
| loudness normalisation | ❌ in the draft | voice is his; measure the export with `ebur128` and report LUFS/LRA against −15 / ≤8 |
| masks (rounded corners on video) | ⚠️ `materials.masks` exist, not mapped | bake the rounded frame into the asset instead |
| render / export | ❌ no API | he exports; verify on a rendered frame, never on the JSON |

## What this changed in the 16:9 landing build (v2 of 0919)

* holds capped at 7 s and punch-ins on sentence starts between two fixed sizes (the 0910
  "punches, not drift" motion) — the cadence moves from 9–11 to ~15 events/min without more cuts;
* headline supers one size larger, kicker one size smaller, so the keyword reads at 2.5× the
  caption; single spoken words allowed as supers on beats;
* the real system recordings go into a **framed insert** beside the head (rounded card, shadow,
  scrim) instead of full-frame, and the BOARDi story clips stay full-frame;
* a lower-third underline rule under the name, the same accent as the title rule;
* a chapter card at each section turn, drawn locally in the brand font;
* hard cuts on b-roll (the house rule); `Glare II` is the only cached flash on disk and is reserved for a section's first punch — `Mix` / `White Flash` need re-caching before they can be used;
* the bed ducks −3 dB under every full-frame clip; loudness of the export reported, not assumed.

**What v2.1 got wrong with this grammar (22.09).** The references use one device per moment: a punch
*or* a b-roll *or* a card, each below the threshold where you notice the mechanism. Applying entry +
drift + exit to every layer at once, at 8–30 % amplitudes, read as clutter and Alon preferred the
plainer v2. The measured numbers stand; the lesson is restraint in applying them — see
`landing-16x9.md` § v2.2.
