---
name: podcast-multicam-edit
description: >-
  Automatic multicam CUTTING for CapCut podcast episodes — routes a multi-camera
  clip to whoever is speaking, decided from the per-mic audio waveforms (the cut
  a human editor makes by eye, done from the sound). Use WHENEVER the task is
  about switching/cutting cameras in a podcast, continuing a multicam edit,
  "route the rest of the episode", enforcing "no shot longer than N seconds",
  adding reaction cutaways to keep the eye active, or any terse Hebrew ask like
  "תמשיך את המולטי קאם", "נתב לפי מי שמדבר", "תחתוך לפי גלי הקול",
  "אין רצף מעל X שניות", "המשך את הניתוב עד הסוף", or naming a two-person podcast
  CapCut project and asking to cut between the cameras. This is the CUTTING
  counterpart to hakapitan-captions (which does captions/transcripts) — reach for
  THIS one for camera switching, that one for text.
---

# Podcast Multicam Auto-Editing

A two-person podcast in CapCut is one **multicam clip** (a camera per guest) plus
**one audio track per mic**. Good editing cuts to whoever is talking. That signal
is already in the mics: **whoever's mic is louder is the speaker.** This skill
reads the waveforms and does the cutting — continuing a human's routing to the
end, or enforcing rules like "never hold a shot longer than N seconds."

Everything runs through the same local CapCut project files as `hakapitan-captions`
(`~/bunker-video-engine/app/capcut.py`, its `.venv`, `paths.FFMPEG`).
Read that skill's safety section too — the lock/backup rules are identical.

## The one tool

`scripts/podcast_multicam.py` (run with the project venv). Three subcommands,
all read-only until `--write`, and `--write` refuses while CapCut has the draft
open:

```bash
cd ~/bunker-video-engine
V=.venv/bin/python
S=~/.claude/skills/podcast-multicam-edit/scripts/podcast_multicam.py

$V $S analyze "<project name>"                       # learn mapping + cadence, cache envelopes
$V $S route   "<project>" --from 214.2 --max 15      # dry-run: route 214.2s→end
$V $S route   "<project>" --from 214.2 --max 15 --write
$V $S maxshot "<project>" --max 10                    # dry-run: enforce ≤10s everywhere
$V $S maxshot "<project>" --max 10 --write
```

Always **dry-run first**, show the user the shot count / median / max, then
`--write` once they confirm and CapCut is closed.

## Which subcommand

| The user wants… | Use |
|---|---|
| "continue the multicam I started, to the end" | `route --from <where they stopped>` |
| a fresh routing of a stretch by who's talking | `route --from <start>` |
| "no shot longer than N seconds" / "add reaction cutaways" | `maxshot --max N` |
| "what did I do / is the mapping right" | `analyze` |

**`route` vs `maxshot` is the key choice.** `route` re-derives cuts from audio for
`[from, end]` and REPLACES whatever was there — use it to extend an unrouted block.
`maxshot` keeps **every existing cut and every hand-correction** and only splits
shots longer than `--max` — use it to tighten a draft the user has already edited.
When the user has made manual corrections, NEVER `route` over them; use `maxshot`.

## How the routing works (so you can reason about edits)

1. **Camera↔mic mapping is learned, not assumed.** For each existing cut, whichever
   mic was louder while that camera showed → that camera belongs to that mic.
   `analyze` prints it and an agreement % (louder-mic vs the shown camera). On a
   real hand-edited intro this was ~90% — that IS the ceiling; the missing ~10%
   are editorial reaction shots that aren't in the audio.
2. **Envelopes:** each mic → RMS envelope at 50 ms, smoothed ~1 s. Speaker =
   `argmax(mic1, mic2)` with a **silence floor** (hold current camera through
   pauses), a **margin** and a **hold time** (the other speaker must dominate
   ~0.35 s before a switch) and a **minimum shot** (~1.3 s) — this is what stops
   it flickering on "mm/yeah" interjections and reproduces a human's cadence.
3. **Max-shot rule → reaction cutaways.** A long monologue would sit on one camera
   too long. `--max N` breaks any shot > N by cutting briefly (~1.6–2.8 s) to the
   OTHER camera, placed where the listener's mic is most present relative to the
   speaker (a reaction / the speaker's pause) — "keep the eye active." A silent
   listener under the cutaway is fine and expected; it's for eye-activity.
4. **Cuts snap to pauses.** Every cut is nudged (±0.6 s) to the quietest nearby
   moment (min of mic1+mic2) so it lands on a breath, not mid-word. Clamped so no
   shot drops below ~1.45 s.

Tunables live at the top of the script (`MIN_SHOT`, `HOLD`, `MARGIN`, `REACT_MIN`,
`SNAP_WIN`, `SNAP_FLOOR`). To make cuts snappier/calmer, adjust and re-dry-run.

## The multicam data model (what a "cut" actually is)

Each timeline video segment references a video material whose
`multi_camera_info.cur_camera_track_id` names the **active camera**. Switching
cameras = a new segment whose material carries a different `cur_camera_track_id`.
The camera source videos aren't in the material `path` (it's ""); cameras are
identified only by these track ids. The script clones a **real material of the
target camera** (taken from an existing segment) so every internal field CapCut
expects comes along. Source maps 1:1 to target (`source_start = target_start +
offset`, offset usually 0).

## Non-negotiable safety (each learned the hard way)

- **Never write while CapCut is open.** The script checks `draft_locked` and
  aborts; still, ask the user to Cmd+Q and confirm before `--write`.
- **`_backup()` before every write, atomic write after.** Backups sit in the
  draft folder; `capcut.restore_backup(folder)` reverts.
- **Preserve the user's hand-work.** `maxshot` keeps every ≤N shot byte-identical
  (including their corrections). After any write, VERIFY: full coverage, 0 gaps,
  `max shot ≤ N`, and that known hand-corrected timestamps still show the camera
  the user set (diff current cams vs your last plan — see the QA pattern below).
- **The draft FOLDER name ≠ the display name.** CapCut stores duplicates as
  `name (1)` or even `0730`; a freshly-created project may have NO `draft_info.json`
  on disk until saved. `resolve_folder()` matches by duration — trust it over the
  display name, and if a brand-new project won't resolve, have the user save/close
  it in CapCut first so the JSON is flushed.

## QA the result (always, after a write)

Reload the draft and check: total coverage == duration, **0 gaps**, **max shot ≤
max**, **0 redundant same-camera adjacencies**, shot-length distribution (few
sub-1.3 s = no flicker), and **cut-to-pause distance** (median should be small —
cuts land on breaths). To confirm hand-corrections survived, compare the current
per-time camera against your intended plan at the corrected timestamps. See
`references/algorithm.md` for the exact metrics and thresholds that flagged real
problems (mid-word cuts, flicker) and how snapping/min-shot fixed them.

## References

- `references/algorithm.md` — the envelope math, every tunable, the QA metrics
  with the before/after numbers from the first real episode, and the gotchas
  (track-index instability, camera-id resolution, envelope cache).

## Routing CapCut Multi-camera *clips* inside a bigger project (0830 (1), 15.09.26)

Alon's newer habit: he selects the two camera layers of a reel and converts them to a
**Multi-camera clip** (a compound with `multi_camera_info` on the outer material). Several
such clips sit at the head of a project that also holds older finished reels — so
`route --from` (whole-timeline, one 1:1 source map, mic audio tracks in the project) does
not fit. `scripts/route_multicam_clips.py` is the per-clip variant, same algorithm
(`route`/`split_long`/`snap` imported from `podcast_multicam.py`):

* **One span per nested draft.** Consecutive pieces on the same `drafts` ref are collapsed
  back to one span first (idempotent), the camera ids come from the nested draft's tracks
  by the *last digit of the file name*, and the camera-file time is `nested source start +
  the piece's own source offset`; the mics get `MIC_OFF` on top (−0.146s here).
* **A cut is CapCut's own shape:** a new material per piece (deep copy, only
  `cur_camera_track_id` changes, `audio_open_track_id_list` stays on the mic-2 camera so
  the sound is continuous), the same `drafts` ref shared, the other extras cloned, source
  offset inside the compound. That is byte-for-byte what CapCut wrote for his old reels.
* **A plain Compound clip with the same two cameras is one field away from a Multi-camera
  clip.** Diffed material, segment, drafts entry and nested draft: only `multi_camera_info`
  (and the names) differ. Reel 3 was converted in place and routes like the others.
* `_atomic_write` refuses while CapCut runs at all; the draft may be closed while the app
  is open, so the script writes tmp → parse back → replace after `_backup()`.
* Numbers to read: pure speaker-follow gave 18 shots and a 128s hold; with the default
  `MAX=15` (reaction cutaways) 80 shots, min 1.40s, median 8.4s, camera 1 (host) 30%,
  mic↔camera agreement 85–88% per span. Render frames 0.6s either side of three cuts.
