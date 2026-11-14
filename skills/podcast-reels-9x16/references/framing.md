# Framing: which frame you move, and in what order

The house rules in `SKILL.md` say *what* to aim for — eyes on the upper third,
the head 33–38% across, the caption clear of every chin. This is the arithmetic
that gets you there, and the order matters because each step changes what the
next one can measure.

0. **Anchor the eyes, not the edge of the frame.** This supersedes the top pin
   below for full-frame shots, and it came from Alon rejecting a 3.82 crop as
   "too close": *keep the subject's eyes at the start of the upper third.* Pin
   the eye line and let the scale be whatever the widest legal value is —
   `fill = 3.1605` in 9:16 — instead of pinning an edge and discovering where
   the face ended up:
   ```
   eye_frac(f) = f.top + 0.40·(f.chin − f.top)        # eyes ≈ 40% down the head
   material_top = anchor·1920 − eye_frac·607.5·s      # anchor ≈ 0.30
   clamp material_top to [1920 − 607.5·s, 0]
   y = (960 − material_top − 607.5·s/2) / 960
   ```
   Anchoring the eyes also fixes the push-in: the zoom now closes *around* the
   eyes rather than sliding the face down out of the frame as it grows.

   Say so when the footage cannot deliver it. On אורח O the head sits at 0.173 of
   the source height, so bringing his eyes down to a true 1/3 means cropping from
   the top — which *raises* the scale to 3.71 and contradicts the note that
   started it. Landing at 25–37% (median 29%) and explaining the limit beats
   silently honouring one half of the instruction.

1. **Full-frame shots are pinned to the TOP of the canvas.** The rule the eye
   anchor replaced — keep it for the arithmetic, and for projects graded before
   the anchor existed. At the exact cover scale there is no vertical freedom at
   all, so the only way to lift a face is to scale up a little and spend the
   slack upward:
   ```
   y = 0.3164·s − 1          # bottom edge on the canvas bottom; 0 at s = 3.1605
   chin lands at 1920 − 607.5·s·(1−fc)      fc = chin's fraction of the source height
   -> s ≥ (1920 − chin_target_px) / (607.5·(1−fc))
   ```
   Typically 1–11% more scale — invisible as a crop, and it buys the caption
   40–80px of clean chest.
2. **Split halves are pinned to the seam**, the same idea one level down:
   ```
   top half:    transform.y = +0.3164·s      # bottom edge pinned to the seam
   bottom half: transform.y = -0.3164·s      # top edge pinned to the seam
   lower face's brow lands at 960 + 607.5·s·fb
   ```
3. Only *after* the full-frame shots are lifted do you know how high the caption
   can go — and then the split usually needs no extra scale at all, so its
   scale is free to be chosen for how it looks.

At s = 1.5802 the seam pins are exactly ±0.5, which is what an equal split
already uses — so a split whose scale is keyframed but whose y is a constant
±0.5 silently drifts off the seam as it zooms.

On this episode: caption `transform.y = -0.1474` for all 254 (band 0.551–0.597),
full-frame shots at 3.16–3.83 pinned to the top, splits at 1.75 with the lower
brow at 0.634 — the caption sits in the seam band, above the lower speaker's
head, and never on a face.
