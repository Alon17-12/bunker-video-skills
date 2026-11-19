---
name: podcast-reels-9x16
description: >-
  Use when the ask is to edit, finish or correct a video INSIDE CapCut by writing the
  draft JSON — 9:16 reels from a two-camera podcast, a single-talking-head promo, a 16:9
  landing/thank-you/VSL video, edit-prep from a client's SRTs, or any round of corrections on
  one of those ("תכין רילס מהפרק", "רילס 1 הוק 11:00 … סיום 12:52", "תערוך לו רילס",
  "לדייק את הזמנים לפי הזוויות", "תוסיף מסך מפוצל", "כתוביות בצבע לפי דובר", "תוסיף LUT",
  "משחקי מצלמה", "כותרות", "בירולס", "מוזיקה", "תריץ סבב תיקונים", "שכפל את הפרויקט",
  "שהחומרים יישארו בתיקיית המדיה", "ברמה של הורמוזי", "מאחורי הדמות", "רקע מטושטש",
  "תביא את הלוגו האמיתי / הכתבה"). Also use when a CapCut project must be
  duplicated, its media panel populated, or its titles/captions checked for overlap and
  frame overflow. Reach for podcast-multicam-edit when only the camera routing of one
  MULTICAM clip changes; for hakapitan-captions when only transcription/captions are wanted.
---

> **Windows:** לפני העבודה הראשונה במחשב Windows, קרא `~/.claude/skills/bunker-editing/references/windows.md`: מה שונה (נתיבים, CapCut סגור לגמרי, כוננים, מקודדים) ובדיקת המוכנות `doctor.py`.

# CapCut post-production by draft surgery

CapCut has no plugin API. Every deliverable here — reels, promos, landing videos — is produced
by reading and writing `draft_info.json` (and, for what shows in the Media panel,
`draft_meta_info.json`) with the **הקפטן** codebase at `~/bunker-video-engine`
(`.venv`, `app/capcut.py`, `bin/ffmpeg`; there is no ffprobe — parse `ffmpeg -i`).

**Core principle: measure, don't remember.** Every number that matters — a scale, a caption
height, a text width, a cut cadence, a loudness — is read off a project Alon approved, a
rendered frame, or the reference video, and then verified on pixels. A rule that no script
enforces is a rule that will be missed on the day it matters; a JSON that passes every check
can still render wrong. This file is the map; the bodies are in `references/`.

## Which deliverable — read this first

| The ask | Reference to read | Scripts |
|---|---|---|
| 9:16 reels from a two-camera podcast (client timecodes, mics, split screens, LUT) | `references/house-rules.md`, `references/pipeline.md`, `references/framing.md`, `references/brand-layer.md` | `prep_from_srt.py` · `reels_build.py` · `frame_shots.py` · `apply_multicam.py` · `reel_captions.py` · `reel_punches.py` · `reel_cutaways.py` · `reel_broll.py` · `reel_append.py` · `qa25.py` |
| **voice of a talking head / course recorded in a room** — echo, thin, "חסר בשר", "אקו" | `references/house-rules.md` § Voice cleanup | `voice_clean.py` (run with `~/bunker-video-engine/.venv/bin/python`) |
| a single talking head in 9:16 (promo, ad, the Bunker's own content reels): intro zoom-out, punches, kinetic stacks, b-roll layer | `references/talking-head-promo.md` + the 0923 entry in `references/scripts.md` (one-camera shoots through the reels chain) | `punch_motion.py` · `kinetic_headlines.py` · `track_pan_plan.py` · `broll_layer.py` · `promo_extras_example.py` |
| "premium" / "ברמה של יוצרים" on a finished reel project: keyword supers in the accent, hook + name card + CTA, framed real-product inserts, click/swoosh + ducking, compressed voice, keyword colour in captions | `references/creator-styles.md` + `references/scripts.md` § 0923 premium | `reel_supers.py` · `reel_broll.py` (framed items) · `reel_sound.py` · `reel_caption_highlights.py` · `reel_caption_add.py` · `reel_polish.py` · `copies_audio_compress.py` |
| a 16:9 landing / thank-you / VSL video on a Multi-camera clip he already cut | `references/landing-16x9.md` + `references/creator-styles.md` | `landing_16x9_{transcribe,words_fix,words_from_captions,build,stills}.py` (env `WORK`, `DRAFT`, `BASE_NAME`) |
| "make it look like Hormozi / the references" — titles, b-roll, sound, colour, pacing | `references/creator-styles.md` (measured grammar + what CapCut can/can't do) | — |
| edit-prep from the client's marking SRTs ("הכן לעריכה") | `references/scripts.md` → `prep_from_srt.py` | `prep_from_srt.py` |
| duplicate a project for a rebuild; put generated assets in the Media panel | this file, below | `duplicate_draft.py` · `register_media.py` |
| blur plate under words · "behind the figure" (Remove background sandwich) · real logos / articles / screenshots from the web ("מאחורי הדמות", "רקע מטושטש", "לוגו אמיתי", "כתבה") | `references/devices.md` (his measured compositions) | `scan_drafts_devices.py` · `devices.py` · `matte_clip.py` · `web_capture.py` |
| the exact JSON encodings (geometry, keyframes, text, LUT, registry) | `references/capcut-json.md` | — |
| what broke before, and what it cost | `references/gotchas.md` | — |

## Non-negotiable safety

1. **Never write while CapCut has the draft open.** `capcut.draft_locked()` is a heuristic; the
   authoritative check is `f"{capcut.DRAFTS_DIR/name}/" in capcut._capcut_open_files(pid)`.
   `_atomic_write` refuses whenever CapCut runs at all, so use the house writer:
   `_backup()` → write `.tmp` → `json.loads` it back → `replace()`. If he is mid-session, park
   the write on a watcher (`pgrep -x CapCut`) that fires when he quits — never wait on him.
2. **`draft_meta_info.json` and `root_meta_info.json` need CapCut fully quit**, not just the
   draft closed: CapCut owns them while it runs and reads the registry only at launch.
3. **Back up before every write; restore by shape, never by filename** — the backup rotation
   deletes `ccstudio-backup-*`; freeze anything you must re-read under your own name
   (`draft_info.<project>-base.json`).
4. **Re-read the live draft every run; never touch his hand-work.** His grade, his cuts, his
   `render_index` values stay byte-identical — prove it with a diff against the frozen base
   after every write. Never clear `extra_material_refs` on a video segment.
5. **Never echo API keys, never auto-accept macOS permission prompts, never call it "ready"
   without a rendered frame you looked at.**

## The pipeline (two-camera reels; the other deliverables reuse stages 7–9)

| # | Stage | Verified by |
|---|---|---|
| 1 | Sync the client's file to the ISO angles (three clocks: cameras, mics, רז) | same offset in 3 windows an hour apart |
| 2 | Convert the timecodes, confirm against the quoted words — **the words win** | transcribe ±5 s around each mark |
| 3 | Encode per-range work copies into the draft folder | durations from `ffmpeg -i` |
| 4 | Build the draft: title card + hook + body; both cameras end to end, opacity is the edit | no gaps/overlaps on the main track |
| 5 | Vertical reframe: eyes at the upper third, head 33–38 % across, measured on the render | `face_scan.py` |
| 6 | Multicam from the mics, cuts inside silence, interjections kept | `mic_windows.py` |
| 7 | Captions: per-mic transcription, second decode + diff, chunk by width and breath | word QA in `hakapitan-captions` |
| 8 | Movement: punch on entry then ≈1.5 %/s, or punches between two sizes | `qa25.py` 18/19b |
| 9 | Grade: brand LUT on the adjust track, his grade untouched | `lut3d` before/after frame |

## House numbers that carry across projects

| | value | where it came from |
|---|---|---|
| text width, 9:16 | `PIL@60(txt) × size/10` (6 px per size unit); wrap = `fixed_width` × 1.2 when the material carries a fixed box (auto-caption clones: 377.8 → ≈450 px!) — set `fixed_width -1` and the wrap is `line_max_width` 0.82 × 1080 = 886 | Alon's screenshots, 0910 · 0923 r6 |
| **text width, 16:9** | the same **× 1920/1080 = 1.778**, in both axes — CapCut sizes text off the canvas WIDTH | 0919 round 3; the bug behind three "design" complaints |
| caption band | measured against the lowest chin; one `transform.y` for the whole project | `face_scan.py` |
| caption card | ≤3–4 words, ≥0.42 s, one line, breaks on pauses > 0.25 s and on `. ? !` | reels he approved |
| zoom | punch 15–25 %/s for 0.5 s, then ≈1.5 %/s; shots < 2.5 s stay still; ceiling measured per episode | אורח O · פרויקט-דוגמה N · אורח G |
| split-screen share | 11–20 % of the reel, on exchanges, never in a monologue; copy the composition | his reels |
| cut cadence, talking head (16:9, long form) | 10–25 cuts/min, median shot 1.2–3 s, **no hold over ~7 s** | six reference creators |
| **cut cadence, 9:16 reel** | **14–39 cuts/min, median shot 1.0–2.1 s**; speech 170–205 wpm | four Hebrew reels, 23.09 |
| **the hook** | **one shot, zero cuts in the first 3 s**, with a super/graphic already on screen at frame 1 | 3 of those 4 |
| **SFX in a reel** | a **burst of 4–5 hits inside 1.3–3.3 s**, on the hook *or* the CTA — only 4–30 % of cuts carry any hit | same |
| caption cadence, reel | 2–5 words, one line, white, centred, changing every 1.5–3.5 s; optional second tier = one giant keyword per turning point, ≈ every 9 s | same |
| loudness | export ≈ −15 LUFS integrated, LRA ≤ 8; bed ≈ 18–22 dB under the voice (**a 9:16 reel's bed runs louder: 12–21 dB, median ≈16**), ducks −3 dB under b-roll | reference creators · four Hebrew reels |
| b-roll | literal scene of the persona / the real system / the real room; one brand preamble in every prompt; keyframe → `seedance_2_5` `omni_reference`, 60 credits per 5 s at 1080p | 0910 · 0919 |
| logos | read the slot and the count off the neighbouring project; zero is a delivery | `brand-layer.md` |

## What "done" means

1. Every new track has 0 overlaps; the main track is continuous; 0 dangling material refs.
2. **Layout QA in pixels**: a box per text segment (x0, x1, y0, y1 in canvas px + time span) —
   nothing outside the safe frame, no two boxes intersecting while both are on screen. Timeline
   QA cannot see two blocks on one baseline; this can.
3. His tracks diff clean against the frozen base (grade values, cuts, `render_index`).
4. A composite still at every title and b-roll time, looked at; then a rendered frame from
   CapCut for anything visual — a still is not a render.
5. `register_media.py --write` so every asset you added shows in the Media panel.
6. The report is numbers: shots, longest hold, cadence, captions, titles, b-roll count, credits
   spent and left, what was skipped and why. No adjectives.

## Duplicating a project and populating its Media panel

```bash
python scripts/duplicate_draft.py "0919" "דפי תודה ו-VSL v2" --write     # CapCut quit; new folder = new name
python scripts/register_media.py "דפי תודה ו-VSL v2" --write             # idempotent, by file_Path
```

A file in the draft folder that a segment points at is on the timeline but **not** in the
project's media list; Alon asked for every generated asset to be there by name. The list is
`draft_meta_info.json → draft_materials[type 0].value`. Run the registration at the end of every
build, not as a favour at the end of a project.

## Red flags — stop, you are about to repeat a known failure

| Thought | Reality |
|---|---|
| "I remember the rule, I'll rewrite the script in /tmp" | You get the conclusions without the checks. Use `scripts/`, extend them. |
| "The JSON is right, so the render is right" | Nine yellow captions rendered white for two rounds. Render a frame. |
| "6 px per size unit" on a 1920-wide canvas | 1.778× off in both axes: titles off the frame, lines on each other. |
| "The timeline QA passed, so nothing overlaps" | Two text blocks shared a baseline through a clean timeline QA. Box QA. |
| "A screen-grab with the mascot popped on it is b-roll" | Alon: *"אני לא רוצה צילומי מסך עם אייקון שקופץ"*. Frame it, or stage a scene. |
| "The file is in the draft folder, so it's in the project" | It is not in the Media panel until `register_media.py` runs. |
| "12 s on one framing is fine, he's talking" | None of the six references holds past ~7 s. Cut or punch. |
| "a whoosh on every graphic" | Long-form habit. In a reel the hits come as one burst on the hook or the CTA; 70–96 % of cuts carry nothing. |
| "open the reel on a cut to the second camera" | Three of four Hebrew references cut zero times in the first 3 s. The hook is one shot + a layer. |
| "I'll add a nuance / a metaphor / a graphic he didn't ask for" | Every graphic he didn't ask for on 0910 was removed. Literal, or nothing. |
| "Credits will probably cover it" | Check `balance` first and say how many clips it buys. |
| "The bed's `path` is my mp3, so that is what plays" | A material cloned from a library track keeps its `effect_id`; CapCut re-points it to the library cache on open (0922: four silent beds). Local audio = `extract_music` / `local` / no `effect_id`. |
| "A boundary/hold key can be `Line`" | Alon: every keyframe with ease. `Line` on a moving pair is a defect. Easing = `FreeCurveInOut` + 0.42·Δt handles + `graphID` on the end key (capcut-json.md § Keyframes); bare `CurveInOut` shows as Linear. |
| "Both layers at volume 1, each with its own mic, nothing doubles" | Gain-baked bleed is 1 dB under the direct mic → comb filter (0922 R5). `copies_audio_gate.py` before delivery. |
| "The pauses are his to cut" | He cuts every 0.5–1.2 s pause inside a reel himself; `reel_ripple.py` does it from the mics. |
| "I'll set `matting.flag` in the JSON and CapCut will cut him out" | Unverified. He clicks Remove background on a copy, or `matte_clip.py` makes an alpha .mov. |
| "This site/logo looks right" | `whiteboard.co.il` is not WhiteBoard. Primary source, title + domain checked, provenance written. |
| "A stock image will do for the article he mentions" | He only ever inserts the real thing. Find it, or leave the moment to the words. |
| "He asked for motion, so every layer gets entry + drift + exit" | v2.1: 20 tracks, 112 % b-roll entries, 1.6 s chapter cards — *"העריכה הקודמת הייתה יותר טובה"*. One device per moment, under the threshold you notice; a chapter card sits on the pause before its sentence, never inside the previous one. |
| "The caption track has 300 cards, the transcript is covered" | 0923 shipped with 7 s of speech uncaptioned (3:48–3:56). Scan for caption gaps > 1.5 s where the mic is loud before reporting. |
| "905 px fits in a 1080 canvas" | `line_max_width` 0.82 → CapCut wraps at 886 px; Alon's 0922 titles prove it. Supers ≤ 860 px, or two lines by design. |
| "Both camera copies audible = the full conversation" | Only when each copy carries its own mic. One RODECaster mix on both = +6 dB and a comb filter (0922 R5, 0923 R1). Mute the over layer. |

## References

* `references/house-rules.md` — timing, mics, multicam-by-opacity, zoom, split screens, captions, terms, shadows, 0830 edit-prep. The body of the reels skill.
* `references/creator-styles.md` — the measured grammar of six long-form reference creators **and of four Hebrew 9:16 reels (23.09)**, and what CapCut can/can't do from JSON.
* `references/devices.md` — blur plates, "behind the figure", real material from the web: his compositions, the tools, the verification.
* `references/landing-16x9.md` — the 16:9 landing build, its text calibration, title system and three rounds of corrections.
* `references/talking-head-promo.md` — 0910: intro zoom-out, punches, kinetic stacks v1–v5, b-roll layer, export.
* `references/scripts.md` — every script, what it measures, how to run it, and its traps.
* `references/pipeline.md` · `references/framing.md` · `references/brand-layer.md` · `references/capcut-json.md` · `references/gotchas.md`.
* `references/text_anim_donors.json` · `references/transition_donors.json` — the cached CapCut presets that exist on disk right now.
