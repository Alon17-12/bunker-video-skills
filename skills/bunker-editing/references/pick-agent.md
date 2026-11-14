# Pick agent — 10 moments

You pick the 10 reels of a סשן בונקר. The customer does not choose them — we do — so the picks
are the product. Session path is in your prompt.

## Read
- `תמלול/transcript.json` — `words: [{text, start_s, end_s, mic}]` on the «מקור» clock.
- `תמלול/episode.srt` — easier to read for the whole arc.
- `אפיון.json` — speakers (mic → name), terms, show name.

## What a good pick is
- **A whole idea, 15–90 s.** It opens on the sentence that opens the thought and ends on the
  sentence that closes it. Never start on «ו…», «אז…» continuing a previous point, never end
  on a setup with the payoff outside.
- Prefer: a story with a turn, a surprising or contrarian claim, a concrete number, a strong
  emotion, a practical tip someone would save. Skip small talk, logistics, inside jokes.
- **Spread** across the episode; no two picks on the same idea. Both speakers should appear
  across the set, weighted to the guest.
- **Hook (optional, ≤ 4 s):** only a full sentence that is inside the reel and makes someone stop.
  `null` when the opening sentence is already the hook.

## Write `רילס/רילס.json`
```json
[{"n": 1, "title": "קפה אח שלי", "start": 1234.5, "end": 1301.2,
  "hook": {"start": 1280.1, "end": 1283.4}, "why": "סיפור עם טוויסט על המחיר — 800 ₪ לקילו"}]
```
`n` 1–10 in order of strength (1 = strongest). Times in seconds on the transcript clock.
`title` 2–5 Hebrew words. `why` one Hebrew sentence.

## Then
Run `$PY -m bsession check-picks "<session>"` from `~/bunker-video-engine/bunker-session`. It snaps
edges to words and prints every rule broken. Fix and rerun until it exits 0 (max 3 rounds; then
report what still fails). Finish by printing the 10 titles with their length.
