---
name: hakapitan-captions
description: >-
  Operating guide for producing captions, transcripts, and reels projects for
  CapCut podcast episodes via "הקפטן" (HaKapitan, the local caption studio at
  ~/bunker-video-engine). Use this skill WHENEVER the task involves
  transcribing or captioning a CapCut project, exporting an SRT/transcript of an
  episode, adding captions to a specific draft, completing missing captions,
  building a 9:16 reels project from marked moments, — including terse Hebrew asks like "תמלל את הפרק", "תוציא SRT של הפרק",
  "תוסיף כתוביות לפרויקט X", "רק הדקות הראשונות", "השלם את הכתוביות שחסרות",
  "בנה רילס מהפרק" — and promo/teaser work on a single
  talking head: kinetic word stacks, B-roll, section export with a matching SRT
  per teaser ("תאקספרט לפי החלוקה", "SRT לכל סרטון"). Trigger it even when the
  user names a CapCut project directly and just says what they want done to it. It also
  carries the hard safety rules (never inject into an open draft, never touch
  existing captions unless asked, save deliverables durably) that prevent the
  data-loss and clobber incidents this workflow is prone to.
---

> **Windows:** לפני העבודה הראשונה במחשב Windows, קרא `~/.claude/skills/bunker-editing/references/windows.md`: מה שונה (נתיבים, CapCut סגור לגמרי, כוננים, מקודדים) ובדיקת המוכנות `doctor.py`.

# הקפטן — Captions & Transcripts for CapCut

**הקפטן** is the local caption engine at `~/bunker-video-engine/app` (installed
by this repo's `install.sh`). It transcribes Hebrew speech from a CapCut project's
*edited* timeline and either injects editable captions straight into the draft
JSON or exports them. The venv is `~/bunker-video-engine/.venv`.

Drive it as **direct Python**, importing its modules (`capcut`, `transcribe`,
`reels`, `cuts`, `srt`, `reframe`, `sound`). Always
`sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))` and run with
the engine venv. The first transcription downloads the Hebrew Whisper model
(ivrit-ai, ~1.6GB) once.

The engine (why it works): each CapCut segment carries
`target_timerange`/`source_timerange`/`speed`, which is an exact map from the
*edited* timeline back to the raw source. `capcut.audio_plan(draft, draft_id)`
turns that into a decode plan; `transcribe.build_timeline_audio(plan, dur)`
rebuilds the edited audio; `transcribe.transcribe(audio)` gives word-level
Hebrew via a local `ivrit-ai` Whisper model (~3.2× realtime on an idle M4 Pro).
So captions/transcripts always line up with the cut **as it is now** — no audio
sync guessing. This is why you transcribe the project itself, not a raw file.

## The safety rules (these are here because each one was learned the hard way)

1. **Never inject into a draft that is open in CapCut.** Injection rewrites the
   draft JSON and CapCut owns it while open. Check `capcut.draft_locked(draft_id)`. Either wait for the user to exit
   to the CapCut home screen, or park the captions and inject later. Transcription
   itself only *reads* source files, so it runs fine while CapCut is open.
2. **Never touch existing captions unless the user asked you to.** When adding
   to a draft that already has captions, inject a NEW track with
   `replace_existing=False`, and verify the old caption track is byte-identical
   afterward. Preserve hook/title text tracks (any text segment >25s is a
   headline, not a caption — `TITLE_LIKE_US`). The user's manual edits are
   sacred.
3. **Save deliverables to a DURABLE path, never the session scratchpad.** The
   `/private/tmp/.../scratchpad` is wiped when the session ends — a completed
   transcript was lost this way. Write SRT/JSON deliverables to `~/Desktop`
   (or another real folder), atomically (write `.tmp`, then `.replace()`).
4. **For long jobs, detach from the session.** A background bash task is torn
   down when the Claude session restarts. For a multi-hour transcription, launch
   `nohup .venv/bin/python script.py >log 2>&1 & disown` so it survives, and have
   the script checkpoint its output to Desktop after each window.
5. **Never run a stale surgery script after the user has edited the project.**
   Re-read the live draft each time; a script built against an old backup will
   destroy current work.
6. **CapCut competing for CPU makes transcription ~5–6× slower** (a 110-min
   episode took ~3h with CapCut open vs. ~35 min idle). Tell the user closing
   CapCut speeds it up; run in the background regardless.

## Pick the workflow

| The user wants… | Do this |
|---|---|
| A full transcript / SRT of the episode | **Full transcript → external SRT** |
| Captions only on the opening, fast, for "stage 1" | **First-N-minutes pass** |
| To fill in captions that are missing on part of a draft | **Incremental completion** |
| Captions added to the whole draft, into CapCut | **Full inject** (auto_inject or manual) |
| A 9:16 reels project from marked moments / client SRTs | **Reels** / **Auto-reels** |

Decide, state the choice, act. Don't interrogate — e.g. "שפר את הכתוביות" on a
draft with holes means complete them; "תוציא תמלול" means export, not inject.

Two chunking styles: **reel captions** (short, punchy — `max_words=3`,
`strip_punctuation`, gap-free) for on-screen captions in his brand style, vs.
**transcript lines** (readable — `max_words≈7`, `max_duration≈4.5`) for a
transcript/SRT deliverable. Match the deliverable. When unsure, offer to
re-emit the other style — it's seconds from the same words.

### Full transcript → external SRT (non-intrusive, durable)

The pattern from `references/full_transcript_srt.py`. Build the whole edited
timeline audio, transcribe in ~10-minute windows, and after **each** window
rewrite the complete SRT-so-far to `~/Desktop` atomically. Injects nothing.
Run detached (rule 4) so it survives session teardown, and monitor a small
progress JSON on the Desktop. End with a glossary (brand-name) pass; if it
fails the SRT is already complete without it. Verify at the end: cue count,
0→duration coverage, monotonic + zero overlaps, `utf-8-sig` BOM (Hebrew), and
that the opening line matches the *edited* project's opening (not a raw
recording's — that's how you catch a timeline mismatch).

### First-N-minutes pass (fast partial + inject)

When the user only needs the opening captioned now: filter `audio_plan` to
segments before `N*60s` (clip the straddling one), build audio for `[0, N*60s]`,
transcribe, `chunk_captions(max_words=3)`, glossary-fix, then inject with the
default style. Injection needs the draft unlocked (rule 1) — tell the user to
step out to the CapCut home screen. See `references/first_minutes.py`.

### Incremental completion (preserve everything)

Find the existing caption coverage (`capcut.extract_captions`), transcribe only
the uncovered holes (≥3s), and merge — existing captions and manual edits
survive verbatim. Transcribe the hole window yourself and inject a new track with a donor
style cloned from the existing captions via `capcut.extract_style(draft_id,
track_index)`; then assert the old track is byte-identical (rule 2).

### Full inject (captions into CapCut)

Build the timeline audio, transcribe, `transcribe.chunk_captions(...)`, then
`capcut.inject_captions(draft_id, captions, style)` with a style from
`capcut.extract_style` (a donor track) — only while the draft is closed in
CapCut (rule 1).

### Reels & Auto-reels

- **From marked moments:** `reels.create_reels_draft(...)` builds a fresh 9:16
  draft (white title card per moment, auto-reframe, color) without touching the
  source.

## QA the words before you report — context and spelling, not just coverage

A caption job is not done when the count and the overlaps check out. Alon's
standard (set on 0830 (1), 8.9.26, and he called the result "מעולה") is that
every transcription gets a **second opinion and a reading for meaning**. The
first pass on that project was 96.7% right and still shipped «לקוכב» for
«לקוחה» (Sivan is a divorce mediator — the context named the word), «משווים
מטורפים» for «מצבים מטורפים», «העולם שאימא» for «שזה מה שאימא», and dropped
«חד», «יום» and «הבנת». None of those is visible in a card count.

Three layers, all of them, every time:

1. **A second decode and a diff.** `references/caption_qa_tiebreak.py --cache
   <reel_captions work key>` (or `--audio/--words`) re-transcribes the same
   timeline audio with a bigger beam, no VAD and no conditioning on the
   previous window, and prints one line per disagreement. 96–98% agreement is
   normal. Words both passes agree on are what was said, even when they look
   odd («בגלל שלזה גדלת», «אישית ושלנו אישית») — leave them. The disagreements
   are the candidate list.
2. **Read the whole text in order, as a listener would.** Dump the cards in
   time order and read them against the subject of the recording: a word that
   exists but does not fit («של עד זה» → «של ילד זה»; «הוא התגרש» where the
   sentence is conditional → «הוא יתגרש»), a fragment that is a stutter on
   screen («ש זהו», «א היא»), a card that lost a word the sentence needs.
   Spelling too: «גודל» as a verb is «גדל»; a final letter mid-word is never
   right. This is the layer the diff cannot do.
3. **An independent agent for anything that matters.** For a delivery, spawn a
   QA subagent with the caption dump, the source audio and the mapping, told
   to re-transcribe from the raw file and report — not fix. Its 6-setting
   decode of each suspect spot is what separated "high confidence, fix" from
   "no two decodes agree, leave it for a human ear" («זה יוצר דרגן»).

Then apply only what two of the three agree on, **text and the style
`range` together** (a card with one style gets `range = [0, len(text)]`; a
multi-style card needs its per-word ranges rebuilt), keep every card inside
the width ceiling (moving a word to the neighbouring card beats a too-wide
line — «חד משמעית» went to the next card), back up, write atomically, and
re-check that the untouched tracks are still byte-identical. Report the
agreement %, the list of fixes, and the suspects you deliberately left.

## References

- `references/caption_qa_tiebreak.py` — second-opinion decode + word diff;
  the first layer of the QA above.
- `references/full_transcript_srt.py` — durable windowed full-episode → SRT.
- `references/first_minutes.py` — fast first-N-minutes transcribe + inject.
- `references/snippets.md` — the load/verify/monitor snippets (audio_plan
  filtering, atomic SRT writer, `srt.parse_srt` verification, clean progress
  monitor) reused across all of the above.

## Compound clips break `audio_plan`

A CapCut **compound clip** ("Compound clip1") is a material with `duration`,
`width`/`height` and **no `path`** — `audio_plan` cannot decode it, so a project
whose cold open is compounded looks silent. The media is one level down:
`materials.drafts[].draft` points at `subdraft/<id>/draft_content.json`, and the
nested draft carries the real segments and file paths.

In the episode `צומת 20 - אורח O פרק` the compound was a straight 1:1 pass-through —
one 72.2s video segment (`1_CAMERA 1.mp4`) and one audio segment
(`1_COMBO-1.wav`), both from source 0 — so a segment's `source_timerange.start`
in the outer draft *is* the time in the WAV, and the timeline audio can be
rebuilt by decoding those spans directly. Verify that before relying on it: if
the nested draft's segments do not start at 0, or carry a speed, the mapping is
not the identity and you have to compose the two timelines.

Two things worth checking on an episode's cold open before transcribing: which
microphone actually carries it (this one was 99.3% mic 1 — a monologue to
camera, so the captions are a single colour), and where the intro starts, which
is the caption boundary. It is the first main-track segment that is *not* the
compound; in `צומת 20 לקוח I פרק` the captions end at 99.98s on exactly that
frame, and that project is the style donor for the rest: white, `size 10`,
`scale 1.5`, `transform.y = -0.6019`, `bamberger-grunge-bold-fm`, black stroke +
shadow, 2-4 words, no punctuation, no gaps.

## The house font has no Latin glyphs — transliterate brand names

`bamberger-grunge-bold-fm.ttf` (the caption font on every brand-style track)
carries Hebrew only. A Latin word in a caption renders as a row of notdef boxes,
and nothing in the JSON looks wrong. Whisper writes brand names in Latin
(`מ-whiteboard`, `Meta`, `AI`) whenever it can, so after chunking grep the cards
for `[A-Za-z]` and rewrite them in Hebrew letters (`מווייטבורד`), keeping the
style `range` in step with the new text. Verify a font the same way it was
caught on 0910: with PIL, `getlength("W") == getlength("口")` means the glyph is
missing (both fall back to notdef). A Hebrew transliteration is the deliverable
until Alon swaps in a font with Latin coverage — say so in the report.

## Font catalog — what CapCut can draw (updated 09.10.2026)

Every caption font lives as a file in CapCut's sandbox folder
`~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/` (mirrored in
`~/Library/Fonts`). A style points at a font by **absolute path** in two
places that must agree: `material.font_path` and every `styles[].font.path`
inside `material.content` (leave `font_id`/`font_resource_id` empty — those
are CapCut's store fonts). A path that doesn't exist renders in the system
face with no warning, so `ls` the file before injecting.

Latin = has A–Z (brand names can stay in English); otherwise transliterate as
above. Verified with fontTools cmap on 09.10.

| Font | File for captions (heaviest) | Latin | Digits | License |
|---|---|---|---|---|
| Bamberger Grunge (house) | `bamberger-grunge-bold-fm.ttf` | no | yes | own |
| Open Sans Hebrew | `opensanshebrew-extrabold-webfont.ttf` (also bold/regular/light, italics) | yes | yes | Apache 2.0 |
| Arimo | `Arimo-Bold.ttf` (Regular→SemiBold, italics) | yes | yes | OFL |
| Fredoka (rounded) | `Fredoka-Bold.ttf` | yes | yes | OFL |
| Rubik Scribble (scribbled display) | `RubikScribble-Regular.ttf` | yes | yes | OFL |
| Karantina (narrow) | `Karantina-Bold.ttf` | yes | yes | OFL |
| Nachlieli CLM | `nachlieliclm-bold-webfont.ttf` (+ oblique, light) | yes | yes | GPL+font exc. |
| Pfennig | `pfennigbold-webfont.ttf` (+ italic, regular) | yes | yes | OFL |
| Noot (handwritten-ish) | `noot-aj.ttf` | yes | yes | OFL |
| OS Aran | `OS Aran_400FFC.otf` (Latin); `OS Aran_R_600FFC.otf`, `OS Aran_W_500FFC.otf` are Hebrew-only | 400 only | yes | free commercial (Ofir Shavit) |
| Ellinia CLM | `elliniaclm-bold-webfont.ttf` | no (a lone «S» only) | yes | GPL+font exc. |
| Gladia CLM | `gladiaclm-bold-webfont.ttf` | no | yes | GPL+font exc. |
| Yehuda CLM | `yehudaclm-bold-webfont.ttf` | no | yes | GPL+font exc. |
| Journal CLM (handwriting) | `journalclm-light-webfont.ttf` | no — its «A» is a **box glyph** («AI» → «□I») | yes | GPL+font exc. |
| Abraham | `Abraham-Regular.ttf` | no | yes | GPL+font exc. |
| Ptil Narrow / Wide | `ptilnarrow-medium-webfont.ttf`, `ptilwide-medium-webfont.ttf` | no | yes | OFL |
| Migdal HaEmeq | `migdalfontwin-webfont.ttf` | no | **no digits** | OFL |

Also present from earlier: Heebo, Rubik, Assistant, Alef, Miriam Libre, IBM
Plex Sans Hebrew, Noto Sans Hebrew, Varela Round, Suez One, Frank Ruhl Libre,
Amatic SC (Google Fonts, all with Latin). Migdal has no digit glyphs — a card
with a number must be spelled out or set in another face. A new font for a
show needs a new style in the studio (copy an existing style, swap both
paths) — never edit the font of a style other projects already use.

## Question marks stay on, sentences never share a card

Reel captions drop punctuation — except the marks that carry meaning. Alon on
0910: *"למה כאן אין סימן שאלה והפרדה של הכתוביות?"* when a card read «ערכתם השנה
הלקוח». Keep `?` and `!` on the card that asks, drop `.` and `,`, and never let a
card cross a sentence end: split on the sentence-ending word's end time. Whisper's
Hebrew punctuation is usable (4 `?` / 40 `.` on a 380-word promo, all correct on
review) but read the transcript once yourself for rhetorical questions it missed.
The re-split tool lives in `podcast-reels-9x16/scripts/sentence_split_captions.py`.

## Promo / teaser projects — one talking head, eight deliverables (0910, 13.09.26)

The promo for the WhiteBoard webinar (`0910`, 9:16, one speaker, 3:42) was cut
into eight teasers by white 5s cards on the main track, and went through eleven
rounds before Alon said "הגענו לרמה גבוהה מאוד". Everything that is *editing*
(reframe, punches, music bed, CTA arrow, kinetic word stacks, B-roll) lives in
`podcast-reels-9x16/SKILL.md` from "Three rules from 0910" onward, with the
scripts in that skill (`kinetic_headlines.py`, `broll_layer.py`, `qa25.py`).
This section is the caption/transcript side of the same project — the part
that is הקפטן's.

**The caption contract.** Once kinetic text stacks share the screen with
regular captions, "every spoken word is captioned exactly once" is the only
rule that survives contact: a word is either inside a stack's word range or
on exactly one regular card. Alon caught both failure modes on the same day —
*"יש כתוביות שמחקת"* (cards that merely touched a stack window were removed)
and *"הטקסט היה כתוב פעמיים"* (a straddling card kept its full text under the
stack). The fix is a word-level rebuild from a **frozen** full-coverage caption
track plus a per-word token map, and a run is finished only when it prints
`words without caption: []` and `shown twice: []`. Freeze that base under a
custom name (`draft_info.caption-base-v4.json`): `_backup()` rotates and
**deletes** `ccstudio-backup-*` files, and it deleted the one I was reading.

**A date is one card, one colour.** «ב-27 בספטמבר» never splits across cards
or across a highlight range. Do the date-join before the flicker glue (< 0.5s
cards glued to the next, never *into* a date card) and the width re-split,
and iterate until nothing changes.

**Text size in CapCut is not what PIL says.** Measured off Alon's screenshots:
rendered width = PIL width at 60pt × `size`/10 (≈ 6 px per size unit), line
pitch 6.6×size, a row wraps at ≈770 px on a 1080 canvas. The old composite
renderer drew text 30% too small and passed every width check while cards
wrapped on screen. Render a still with them before calling any width "OK".

**Never share a material between tracks.** A pop lane reused the CTA arrow's
audio material; when that lane was torn down and rebuilt, the shared material
went with it and CapCut silently dropped *both* tracks on load. Alon heard the
missing click before I saw it. Every track owns its materials; a rebuild
script restores what it may have removed and repoints paths into the draft
folder.

**Delivery: sections + SRT per section.** CapCut has no export API and the GUI
route raises macOS permission prompts that are Alon's to grant. The recipe that
works: he exports the whole timeline once (4K 2160×3840, 60fps) **with SRT**
into a prepared Desktop folder, and a watcher splits both:

```bash
R=~/.claude/skills/hakapitan-captions/references
python3 $R/section_export.py plan  "<draft folder>" plan.json     # ranges = camera runs between white cards; then name them by content
python3 $R/section_export.py split full.mp4 full.srt plan.json "<Desktop folder>"
python3 $R/section_export.py srt   "<draft folder>" full.srt      # when CapCut exported no SRT (it only exports what it marks as subtitles)
```

Each section lands in its own sub-folder, `<name>/<name>.mp4` + `<name>/<name>.srt`,
cues clipped to the range and shifted to 0, utf-8-sig. `section_export_watcher.sh`
is the polling wrapper (size-stable check, 4-minute grace for the SRT, fallback
to the draft's captions, `setopt null_glob` — an empty folder aborted the first
version). Section names carry content («06 חופש בלי דאגות»), not only numbers.
Verify the plan against the draft (eight ranges, 5.0s gaps) before it runs, and
open one section's SRT against its mp4 before reporting.

