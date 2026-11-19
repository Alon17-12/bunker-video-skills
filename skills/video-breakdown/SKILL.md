---
name: video-breakdown
description: Use when the user hands over one or more video links (YouTube, Instagram) or local files and wants to learn how they are MADE, not what they say — "תנתח לי את הסרטונים", "מה הסגנון של הקריאטור הזה", "תפרק את הריל", "איך הם עורכים את זה", "תעשה breakdown", "ספר סגנון", "תשווה בין הסרטונים", "analyze these reels", "reverse engineer this ad", or a client/competitor reference that must be reproduced in CapCut.
---

> **Windows:** לפני העבודה הראשונה במחשב Windows, קרא `~/.claude/skills/bunker-editing/references/windows.md`: מה שונה (נתיבים, CapCut סגור לגמרי, כוננים, מקודדים) ובדיקת המוכנות `doctor.py`.

# Video Breakdown

Reference videos → a style book you can execute from. **Every number is
measured, never estimated**; interpretation is labelled as interpretation.

Built for reels, shorts and ads up to ~3 min. Longer runs still measure, but
`shots.json.warning` says the premise is off.

## Run

```bash
S=~/.claude/skills/video-breakdown/scripts
python3 $S/run.py <batch_dir> <url> [<url> ...]     # or <batch_dir>/sources.txt
```

Default batch dir: `~/video-breakdown/<YYYY-MM-DD>-<topic>/`.
`run.py` fetches, measures, and transcribes every link, skips stages already
on disk (re-running after a failure or two new links costs only the missing
work), and prints the numbers table that `comparison.md` starts from.

Per video it leaves: `source.mp4`, `evidence/{meta,shots,captions,audio,transcript}.json`,
`transcript.md`, `shots/`, `captions/`, and **`sheets/`** — labelled contact
sheets. Read those, not the individual stills; open a still only for a card
that needs a closer look.

**Instagram** public reels download logged-out (verified on a 53 s reel).
Some reels are genuinely 5 s and silent — text cards; `meta.json` says
`audio_present: false` and the table shows `SILENT`. That is the content, not
a failed download. A cookies file is recommended, not required: it switches
yt-dlp to the proper API path so duration and metadata come through. Reading
Chrome's cookies directly fails here (the Keychain denies a non-interactive
shell), so export one with "Get cookies.txt LOCALLY" on instagram.com and save
it as `~/.config/video-breakdown/instagram-cookies.txt` (`chmod 600`) — picked
up automatically. Never print or commit it.

**YouTube** breaks when yt-dlp's client tricks go stale (`"The page needs to
be reloaded"`). `bin/yt-dlp` is the standalone binary — `bin/yt-dlp -U` first,
then `BREAKDOWN_COOKIES_BROWSER`.

## Listen — submit first, collect last

Music character and SFX identity cannot be measured. **Before** reading any
sheet, submit every video to Higgsfield and save the ids:

- YouTube → `mcp__claude_ai_higsfield__video_analysis_create` with `youtube_url`
- Instagram/local → `media_upload` → `media_confirm` → `video_input_id`

Observed 23.09.26: a 70 s job sat `queued` for 35+ minutes against a stated
3-5 (all four completed within ~6 hours). Do the looking and writing while it
runs; poll `video_analysis_status` at the end. If it has not completed by
then, deliver with every `[נשמע]` field as `—` and say so — never fill them
from the frames.

### Verify every analysis before you believe one word of it

**24.09.26: two of four analyses described a video we never sent** — our 73 s
Hebrew reel came back as a 30 s English milk-frother ad, our 57 s one as an
18 s toothbrush ad. Both were detailed, confident and internally consistent.
Nothing in the response marks them as wrong.

Before using any field, check the analysis against our own evidence:

1. **Duration** — the last `timestamp_end` must land within a few seconds of
   `meta.json.duration_s`. 30 s against 73 s is the whole tell.
2. **First spoken line** — its scene 1 `audio` must be our `transcript.md`
   first line (it translates Hebrew to English; the content still matches
   word for word).

Fails either → the analysis is discarded, `[נשמע]` stays `—`, and the report
says the job returned someone else's video. Never re-submit and assume the
second try is real: verify that one too.

Also know what it does *not* give: the `audio` field is speech only. It names
**no music genre and no sound effect** — the two things we send it for. Its
`visual` field is real value (props, lighting, layer devices), but it is a
second pair of eyes, so tag it `[נצפה]`, not `[נמדד]`.

## Write

Fill the fixed rubric (`references/rubric.md`) for every video, in the same
order, using the templates:

- `references/timeline.md` → `<video>/timeline.md` — shot by shot
- `references/style-rules.md` → `<video>/style-rules.md` — CapCut-executable rules
- `references/comparison.md` → `<batch>/comparison.md` — paste `run.py`'s table

Hebrew throughout. Every field carries `[נמדד]` / `[נצפה]` / `[נשמע]` / `[הסקה]`;
a field without evidence is `—`.

## Who may say what

| Claim | Only source |
|---|---|
| any number — cut rhythm, BPM, dB, wpm, hit counts, face size | `evidence/*.json` |
| shot content, caption look, camera move, on-screen text | sheets you looked at |
| genre, what a sound *is*, tone | `higgsfield.json` |
| why it works, who it targets | you, tagged `[הסקה]` |

Scripts beat the analyser on any number. "Fast cutting" vs a measured 2.4 s → 2.4 s.

## Limits the scripts state about themselves

- Tempo ±3 BPM, reported only on a genuine periodic peak; `null` = speech-led.
- SFX are located and counted, never named, by `audio.py`.
- **Caption change count is a ±40 % estimate**, calibrated on three videos
  (26 / 9 / 23 measured vs ~40 / ~4 / ~22 true). `captions_present: false`
  is reliable (captionless footage reads 0 text px). The count never becomes
  a rule until you have looked at `sheets/captions-*.jpg` — count the cards
  there and write the number you saw, tagged `[נצפה]`. Band is the lower
  45-98 % of frame; captions parked high are missed.
- Framing comes from the largest detected face; B-roll, screens and profile
  faces read `no_face`.
- `transcript.py` needs platform captions (YouTube). Instagram has none — the
  transcript then comes from the listening pass or Whisper, and is tagged so.
