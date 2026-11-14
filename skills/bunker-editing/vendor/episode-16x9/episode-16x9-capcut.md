# צומת 20 — the 16:9 episode project

The vertical project is the source of truth. Alon cuts the teaser once, in 9:16,
with captions he has approved. This skill does **not** re-edit it — it copies
that edit into a landscape draft and bolts the episode furniture around it.

## Why this is mechanical (measured, not assumed)

I diffed `אורח S צומת 20 טיזר ורילס` (9:16) against `אורח S צומת 20 פרק`
(16:9). The teaser is the **same edit**: 43 caption cards against 43, identical
texts and times; the same 13 cuts on the same source seconds. The only
differences were frame-grid rounding (30 vs 60 fps) and one shot whose source
he swapped by hand.

So a format conversion is four numbers, not an edit:

| | 9:16 | 16:9 |
|---|---|---|
| canvas / fps | 1080×1920 · 30 | 1920×1080 · 60 |
| video framing | scale 3.18–3.91, pan ±0.9 | **1.0, centred** |
| caption `font_size` and style `size` | 20.0 | **10.2** |
| caption `clip.transform.y` | −0.2131 | **−0.7450** |

The vertical reframe is *thrown away*. It exists only to squeeze 16:9 into 9:16,
so scale, transform and the whole keyframe group get reset — leaving the rotation
key behind while dropping position and scale creates an orphan that still
interpolates and drags the shot off centre.

**But only on camera footage.** My first run reset every video segment and blew
two logos up from scale 0.411 and 0.259 in a corner to full-frame centre. The
reframe only ever applied to *landscape* material crammed into a vertical canvas,
so the test is the material's own aspect: reset when `width > height` and the
material has a real path. A logo PNG, a sticker, a portrait Compound — never.

Two kinds of element have no landscape equivalent at all and should be dropped
or flagged rather than squeezed:

- **portrait Compound clips** — nested 9:16 elements. אורח S's landscape project
  contains none; in a 1920×1080 canvas they render as a narrow strip. **Open the
  nested draft before you drop one** — it lives inline at
  `materials.drafts[0].draft` with its own tracks. פורמן's was a four-layer
  stack (a punched-in middle plus bands at `y ±0.75`), and only the *stack* is
  vertical-only. Its middle layer is an ordinary shot of a real second of the
  episode, and dropping the whole compound silently deleted the teaser's opening
  line. Re-lay the middle layer at scale 1.0 and say what composition was lost.
  **A compound also hides its footage from transcription** — its source times do
  not map through the wrapper, so the audio-plan skips it and the words inside it
  never get captions in *either* format. Transcribe the nested draft's own
  segments, or caption that range by hand.
- **full-frame portrait graphics** (a generated 9:16 PNG closing the teaser).
  Say so; he needs a landscape version, and no arithmetic produces one.

Overlays that *do* survive keep their vertical scale and position **verbatim**.
There is no measured 16:9 reference for them, and a plausible-looking guess at a
logo's corner is worse than a value he can see is wrong and fix in ten seconds.

30 fps times are already on the 60 fps grid (1/30 = 2/60), so nothing needs
retiming. Do not "round" them again; that only introduces error.

## The episode skeleton (all values measured off אורח S's project)

Bottom track, locked (`attribute: 4`):

- **opener 0 → 44.00** — `פתיח צומת 20 (מאסטר 4K).mp4` at **volume 0.10**. It runs
  *under* the teaser as a music bed; the teaser covers it until ~42, and the tail
  is the logo animation. This is why the teaser has no logo of its own.
- **the episode from 44.00** — the רז file, one segment.
- **closing card 3.28s at scale 1.05** — `מסך סגירה - צומת 20 (1080p).png`.

Above it: the teaser cameras, then the CTA banner track.

- **`באנר יוטיוב - הירשמו (HEVC שקוף ל-CapCut).mov` — 5.00s per instance, first at
  episode_start + 7.62s, then every 600s.** On a 72-minute episode that is 8.
  Full-frame overlay: scale 1.0, no transform. The `.webm` next to it is for the
  web, not for CapCut.

## The grade is his, not yours

Both formats use the same adjust preset (`7501974767453474064`), but אורח S's
16:9 values differ from his 9:16 on exactly three sliders — brightness
+0.06, saturation −0.10, temperature −0.14. **One sample pair is not a rule.**
Carry his vertical grade across unchanged, stretch it to the new length, and
*tell him the delta* so he can apply it himself if that is what he wants. Never
regrade silently — he has said before, about a different project,
"שיניתי את הLUT — תשאיר אותו איך שהוא".

## Running it

```bash
~/bunker-video-engine/.venv/bin/python \
  ~/.claude/skills/bunker-editing/vendor/episode-16x9/build_16x9_episode.py \
  --source "<9:16 draft folder>" \
  --episode "/path/to/… רז.mp4" \
  --name "<new draft name>"
```

`--teaser-end` is detected as the end of the first contiguous block on the main
video track (a gap over 5s ends it), because in a teaser+reels project the reels
sit far to the right. Pass it explicitly if the detection looks wrong; the script
prints what it chose before it writes anything.

### Two guards that are not optional

1. **CapCut must be fully closed.** Putting the new project on the home screen
   means rewriting `root_meta_info.json`, which CapCut owns while it runs. The
   script refuses otherwise. This is stricter than the caption-injection rule,
   which only needs the one draft to be closed.
2. **Read the live draft, never a backup.** Alon keeps editing between runs — the
   פורמן project grew a sticker track and two video tracks in the hour after
   captions went in. The script reads what is on disk at the moment it runs.

The source project is opened read-only and never written. If anything fails the
new folder is removed, so a half-built draft never reaches the home screen.

## Verify before reporting

The script prints these; do not report success without reading them:

- canvas 1920×1080, fps 60
- teaser segment count per camera matches the source's teaser region
- **every teaser video segment at scale 1.0 / transform 0,0 with 0 position or
  scale keyframes** — this is the check that catches a half-converted reframe
- caption count matches, `font_size` 10.2, `y` −0.7450 on all of them
- spine: opener 0→44.00 · episode 44.00→44+D · closing card 3.28s
- banner count and spacing, first at +7.62s then every 600s
- total duration = 44 + D + 3.28

Then open it and look at one teaser frame and one episode frame. A number that
says "centred" and a frame that shows a head against the right edge have both
happened before on this codebase.

## What stays vertical

The reels do **not** get a landscape version. A reel is a 9:16 format; only the
teaser crosses over. Leave the reels in the vertical project untouched.

## The faster route (15.10.2026): clone an approved episode project

When the 16:9 teaser is a finished **render** (Remotion, not a CapCut edit), there is nothing to convert — the episode is
the previous approved episode project with three files swapped. `scripts/build_episode_from_template.py` copies
«אורח U אורח J צומת 20 פרק» and replaces: the teaser (0 → T), the רז (T → T+D, its volume stays as in the template, 2.24),
the closing card at T+D (scale 1.05, 3.28 s); re-lays the subscribe banner (5 s, first at T+7.65 s, then every 600 s)
and stretches the two top logos (צומת 20 + הבונקר) over the episode. `--dry-run` prints the layout without writing.
Needs: the רז on RCV_Disk, CapCut fully closed.


**אורח T אורח N (15.10.2026):** נבנה ב-`build_episode_from_template.py` מתוך פרויקט אורח J — טיזר מהעותק בכונן (`טיזר/… - טיזר 16x9.mp4`), רז, 7 באנרים, 2 לוגואים, 0 הפניות לאורח J. לפני הבנייה: למדוד LUFS של הרז מול הרז של התבנית (‎-23.3 מול ‎-23.1) — אם דומה, volume 2.24 נשאר.

## מוזיקת סיום (אורח T אורח N, 15.10.2026: "מושלם תכניס את זה ותזכור את זה בסקיל")
אלון: "לשלב בסיום מוזיקה עדינה — אולי מהסוף של המוזיקה של הטריילר".
- **המקור:** אותו טראק של הטיזר (`public/music.wav`), מקו תיבה ~18 שנ' לפני המכה האחרונה (HIT/BAR/PH מ-Teaser.tsx; אורח T: 110.16→131.78).
- **הצבה:** המכה האחרונה נוחתת על תחילת מסך הסגירה; הצלצול (3.7 שנ') מתנגן עליו; פייד 0.8 שנ' עד סוף הפרויקט.
- **מתחת לדיבור:** 2× lowpass 1.4 kHz, ×0.08 (‎≈-34 dBFS מול דיבור ‎≈-23 אחרי ×2.24) עם פייד-אין 3 שנ'. 2.2 שנ' לפני המכה — מעבר לטראק המלא ×0.42.
- **קובץ:** "<פרק> - מוזיקת סיום.wav" בתיקיית הפרק, ערוץ אודיו משלו ב-volume 1.0 (`capcut.add_audio`). שאר הערוצים לא נוגעים.
- **לפני שמכניסים:** תצוגה של 25 השניות האחרונות + מסך הסגירה (ffmpeg xfade fadeblack) לאלון.

## "File not accessible" אחרי בנייה בסקריפט (אורח T אורח N, 15.10.2026)
CapCut ל-Mac רץ ב-sandbox (`com.apple.security.app-sandbox` + `files.user-selected` + bookmarks): הוא פותח רק קבצים שהמשתמש בחר בממשק (או שנמצאים בתיקיית ה-draft). נתיב שהסקריפט כתב לקובץ בכונן (טיזר, רז) מופיע אדום — "File not accessible" / "Unsupported Media" — גם כשהכונן מחובר. באורח J זה עבד כי אלון ייבא את הקבצים בעצמו.
- **תיקון חד-פעמי:** ב-CapCut, קליק ימני על הקליפ האדום → Relink / קישור מדיה → לבחור את הקובץ (או Import לתיקיית הפרק). ההרשאה נשמרת.
- **מראש:** קבצים קטנים (טיזר, מוזיקה, גרפיקה) — להעתיק לתוך תיקיית ה-draft (כמו `add_audio`), שם אין בעיה. הרז (10GB+) — להגיד לאלון מראש שצריך Relink פעם אחת.
