# The brand layer: grade, music and logos

The finish is fixed across צומת 20 reels, and the reference build is the
`צומת 20 אורח G רילס` project — read the numbers off it rather than
inventing them.

| Element | Where |
|---|---|
| captions | `transform.y = −0.2131` (band centre 0.607) |
| intro music | `intro_50-94.wav`, `volume 0.10`, from 0, 44s, 2s fade-out |
| grade | `Bunker.cube` as a `type: "lut"` effect on an `adjust` track spanning the timeline |

The **adjust track grades everything beneath it**, so it belongs directly above
the camera tracks and below the titles, logos and captions; leave it at the top
of the stack and the LUT eats your captions.

### How many logos this reel gets

Not a constant — it follows where the reel is going, and every one of these
already exists on disk, so read the answer off the neighbouring project instead
of deciding it:

| Delivery | Logos | Reference project |
|---|---|---|
| The show's own channels | **two** — the show's mark and הבונקר | `צומת 20 אורח G רילס`, `צומת 20 - אורח O` |
| The show, on an episode that carries a guest's brand | **two** — the guest's mark takes the left slot, הבונקר keeps the right | `אורח E רילס` |
| A single-brand cut | **one**, in its own slot | `צומת 20 לקוח I רילס` |
| A reel delivered to a הבונקר *customer* | **none** | `פרויקט-דוגמה N רילס` (five tracks, zero stills) |

**Zero logos is a delivery, not an omission.** The customer's reel goes onto the
customer's channel; stamping הבונקר on it is a mistake, not branding. Say out
loud which of these four you are building before you place anything.

There are two slots, and they are the same two in every project — measured as
the centre of the rendered box, in percent of the canvas:

| Slot | Centre | Rendered width |
|---|---|---|
| left — the show / the guest | **38–40% W, 71–72% H** | 25–30% of canvas width |
| right — הבונקר | **61–62% W, 72% H** | 20% of canvas width |

Read those as a pair of anchors, not as `transform` numbers: the artwork is
square with transparent padding (2363×2363 in every reel project), so a `scale`
copied between two differently-padded files lands the mark somewhere else
entirely. The number that carries across episodes is the rendered box, exactly
as with head width.

Three consequences worth stating because each one has been got wrong:

* **A lone logo keeps its slot.** `צומת 20 לקוח I רילס` carries only the
  show's mark and it sits at 38%/72% at 30% width — identical to its position in
  the pair. Centring a single logo makes the reel look like a different show.
* **The slots sit *below* the caption band** (captions centre at 61% height,
  logos at 71–72%), so a logo never fights a caption — but it lands squarely on
  the lower speaker in a split screen. Cut the logo segments around every split
  window: faces beat logos.
* **Logos go over footage only.** Across a white title card they vanish into it,
  so build their segments from the complement of the card spans, not one long
  segment — and rebuild them if the client later moves a card, or they will be
  sitting on white where they used to sit on picture.

A 16:9 episode project uses the same two marks in a completely different place
(stacked bottom-right, x ≈ 83%). Don't carry reel coordinates into one.

`scripts/qa25.py` check 27 measures all of this: it prints the slots it found,
fails on a logo over a card, over a split, or moving mid-project, and reports
"no logos" as a fact to confirm rather than an error.

The intro music is an *opener*, not a bed: in the reference project it runs
0→44s of a 988s cut. Match that rather than looping it under a whole teaser.

