# Multicam routing — algorithm, tunables, QA

The system of record for the first real episode this was built on
("אלון ובן המנוקליק", 59.7 min, 2 mics `1_COMBO-1.wav`/`2_COMBO-2.wav`, cameras
`511A4EAE9813` = mic1, `247E39D7005B` = mic2).

## Signal → decision

1. Decode each mic (`ffmpeg -ss off -t dur -ac 1 -ar 8000 -f f32le`) using the
   audio segment's `source_timerange.start` as the offset (both mics shared 9.7 s
   in the source). RMS in 50 ms hops = the envelope. Cache to
   `~/Desktop/.multicam-cache/<folder>.eN.npy` (decoding 60 min twice is slow).
2. Smooth ~1 s (`np.convolve` boxcar).
3. **Silence floor** = `0.4 × median(max(s1, s2))`. Below it → not speech → hold
   the current camera (prevents switching on room tone in pauses).
4. Speaker = `argmax`, but a switch only **commits** when the candidate has been
   louder by `MARGIN` (1.05×) for `HOLD` (0.35 s) AND the current shot already ran
   `MIN_SHOT` (1.3 s). This hysteresis is what turns a jittery per-frame argmax
   into human-looking cadence and ignores brief "mm/yeah" interjections.

## Camera↔mic mapping (learned)

For each existing segment, add its duration to `tally[camera][louder_mic]`.
`mic1_cam = argmax_c tally[c][mic1]`, likewise mic2. On the real episode this was
unambiguous (mic1 100 % → 511; mic2 78/94 s → 247). Then measure agreement:
frame-by-frame, does `argmax(mic)` equal the camera the human actually showed?
**~90 % with 1 s smoothing = the ceiling.** The missing 10 % are reaction shots
the human inserted that the audio can't predict — do not chase them.

## Max-shot rule → reaction cutaways

`--max N` breaks any shot > N. Walk the long shot; every ≤N interval, cut ~1.6–2.8 s
to the OTHER camera, placed at `argmax(listener_env − speaker_env)` in the window
(the moment the listener is most present relative to the speaker → a real reaction
or the speaker's pause). Guaranteed ≤N by clamping the speaker run to `[6, N−0.5] s`.
A silent listener under the cutaway (measured: ~77 % of cutaways) is intended — the
user's words were "לשמור על העין פעילה" (keep the eye active), it's not a bug.

## Pause snapping

Every internal cut is moved to `argmin(s1+s2)` within ±0.6 s (clamped so neither
neighbour drops below `SNAP_FLOOR` 1.45 s or exceeds max). This lands cuts on
breaths. Measured impact on the real episode:

| metric | before snap | after snap |
|---|---|---|
| cuts > 0.35 s from a pause | 268/510 | 117/510 |
| median cut-to-pause | 0.35 s | 0.00 s |
| shots < 1.5 s (flicker) | 203 | 44 |
| shots < 1.2 s | 10 | 0 |

The residual ~117 cuts not on a pause are genuinely inside continuous overlapping
speech — no pause exists to snap to. Don't widen `SNAP_WIN` past ~0.6 s or cuts
drift off the actual speaker turn.

## Tunables (top of podcast_multicam.py)

| name | default | effect |
|---|---|---|
| `MIN_SHOT` | 1.3 | shortest normal shot; raise for calmer, lower for snappier |
| `HOLD` | 0.35 | how long the other speaker must dominate before a switch |
| `MARGIN` | 1.05 | loudness ratio needed to switch (deadband) |
| `REACT_MIN` | 1.6 | shortest reaction cutaway |
| `SNAP_WIN` | 0.6 | pause-snap search radius |
| `SNAP_FLOOR` | 1.45 | min shot length preserved while snapping |

## QA checklist (run after every `--write`)

Reload the draft, per video segment build `(start, end, cam)`:

- coverage end == `duration`, **gaps == 0** (adjacent `start == prev_end`).
- **max shot ≤ max** (the rule held), **0 shots** over.
- **0 consecutive same-camera** segments (a redundant invisible cut).
- shot-length: `min ≥ ~1.3`, few sub-1.5 s, no runs of ≥3 consecutive sub-2 s.
- cut-to-pause: median small; count cuts > 0.35 s from `argmin(comb)` — high count
  means many mid-word cuts.
- **hand-corrections survived:** at each timestamp the user hand-fixed, the current
  camera still matches what they set. Diff current cams vs your intended plan; the
  divergences should be exactly (and only) the user's spots.

## Gotchas

- **Track/segment indices are not stable** across `load_draft`/writes. Identify the
  video track by `type=="video"` + content, cameras by `cur_camera_track_id`, never
  by numeric index. (Same lesson as the caption tools.)
- **Camera ids:** `analyze`/`camera_map` key cameras by the last 12 chars of the
  full track id; the writer needs the FULL id and a real material of that camera —
  both are taken from existing segments, so a camera the user never used can't be
  targeted.
- **Folder ≠ display name** (`resolve_folder` matches by duration). A brand-new
  project can have no `draft_info.json` until saved in CapCut.
- **`route` vs `maxshot`:** `route` overwrites `[from, end]` — it will erase manual
  corrections in that range. Once the user has hand-edited, only `maxshot` is safe
  (it splits long shots and keeps everything ≤max untouched).
- **Envelope cache** is keyed by folder name; delete `~/Desktop/.multicam-cache/*`
  if the source audio is re-recorded/replaced.
