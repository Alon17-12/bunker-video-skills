# Devices: blur plates, "behind the figure", and real material from the web

Three looks Alon asked for on 22.09.26, measured off his own drafts with
`scripts/scan_drafts_devices.py` (197 drafts: matting in 26, Blur in 9, external assets in 130).
**Copy his composition; do not invent one.** Every number below was read off a project he cut.

## 1. Blur plate under words

What he does: a b-roll or screen-recording *copy* on its own track with the `Blur` effect, and the words
on top — never the blur on the main talking-head track.

| project | plate | Blur | words on top |
|---|---|---|---|
| דולב + תום (16:9) | `MVI_1477.MP4`, scale 1.0, 3.7 s | **0.75** | «מילים» / «=» / «7%» — size 8 × scale 3.1–4.4 (≈ 150–210 px), `DeepGlow` text effect, `Fade In`, entering 0.3 s apart at x −0.42 / 0 / +0.45 |
| 100 ל-100 (9:16) | `IMG_0511.MOV`, 2.1 s | **0.5** | a caption line, size 11 × 1.44, house effect |
| vsl עריכת וידאו (16:9) | the shot itself (copy at 1.0) + a *matted* copy above it, 8.4 s | **0.1** | «לקחת את הצעד הראשון שלך» size 15 × 0.62 |
| משיגנע לvsl (9:16) | screen recording 1.27, 1.6 s, `Fade Out` | 0.5 | a photo of the ad + two lines + green-screen money |

Rules of thumb from that table: **0.5** behind a headline, **0.75** for a full plate under glowing words,
**0.1** when the speaker stays readable under a plain caption. The words are one idea in one to three
tokens, each on its own track, arriving one after the other. In JSON: `devices.blur_effect(mats, amount)`
appended to the plate segment's `extra_material_refs`. Text effects he used there (`DeepGlow`,
`glowing neon`) are **not cached** — he applies one once, then it is cloneable.

## 2. "Behind the figure" (Remove background sandwich)

What he does, every time: **three layers of the same shot.**

```
top     video   the SAME clip, matting.flag 3 (or 1), scale/position IDENTICAL to the bottom copy
middle  text    2–4 words on 2–4 tracks, huge (9:16: size 15–20 × scale 2–5; 16:9: size 15 × 0.8–1.4),
                staggered 0.2–0.4 s, anims Bounce In / Blur:out; sometimes a PNG (arrow, laptop) with Click Open
bottom  video   the original clip (matting 0), his keyframes untouched — or a real photo (0111: «חדשות 1.jpg»
                at 3.21 with Blur 0.16) when the story is the picture
```

Measured: סרטון ליד פרימיום («50» «%» at scale 5.0/5.35, `Blur:out`), vsl עריכת וידאו («עד» «שהמסך» «הזה»
`Bounce In`, + `חץ.png`), VSL אייל (matted copy at scale 1.20 with the *same* keyframes as the copy below),
0111 (matted speaker over a blurred news photo for 36 s). The top copy carries the same `scale`, `transform`
and `common_keyframes` as the bottom copy — one pixel of drift shows as a halo.

**Getting the cut-out.** CapCut computes the matte in the UI; setting `matting.flag` from JSON without its
cache is unverified — do not rely on it. Two proven routes:
* **Alon clicks** Remove background on a *copy* of the segment (works on Multi-camera copies — «Multi-camera
  clip 1-copy» in VSL הפקת קורס), and the build does the layering.
* **Local:** `scripts/matte_clip.py "<camera file>" <start> <dur> "<draft>/ccstudio-cutout-<slug>.mov"` — rembg
  (`isnet-general-use`: keeps chair and mic as foreground; `u2net_human_seg`: person only) → HEVC-with-alpha
  via VideoToolbox, the format CapCut already accepted for the tsomet-20 banner. ≈ 1–2 s per frame at 1080p:
  run at 30 fps, `--preview` first and look at hair and the mic arm. Place it as a normal video material
  (`has_audio` false) at the exact scale/position/keyframes of the shot it was cut from, on a track above the
  text. It is a file in the draft folder → `register_media.py`.

**Where the layers go relative to his adjust track.** A CapCut adjust layer grades every track *below*
it. The bottom copy is graded by it, so the cut-out (raw camera pixels) and the words must sit **between
the main track and the adjust track** — `d["tracks"][:1] + [words…, cutout] + d["tracks"][1:]` — or the
figure comes out a different colour from its own background. The b-roll layer stays above the adjust as
before (its LUT is baked in).

**Multi-camera shots.** The active camera lives in a *nested* segment with its own `clip.scale` /
`clip.transform` (0919 cam 1: 1.0607, x +0.0607) under the outer segment's keyframes. Matte from the same
pixels (`matte_clip.py --vf "scale=iw*1.0607:-2,crop=…"`) and matte the **whole outer shot**, so the
cut-out segment can copy the outer `scale`, `transform` and `common_keyframes` verbatim. And read what
is already on screen: 0919 carries the real WhiteBoard logo in the corner for the whole video (md5 equal
to the file on whiteboard.education) — a second logo pop would be a duplicate, so the real-material
insert there is the framed homepage or product, not another logo.

Never move his adjust track, never delete his title stack to make room: the words go where the free
column is (right of the head in 0919), or the title window shifts.

## 3. Real material: logos, articles, screenshots

What he does: the real logos of the tools he names (`chat gpt.png`, `cap cut.png`, `canva 1.png`,
`eleven labs.png`, `hedra.png` in vsl עריכת וידאו — one per mention, popping in with `Fade In` at scale
0.3–0.6 beside the speaker), screenshots of the ad or article being discussed («יש לך אומץ להרוויח 50,000
שקל», `צילום מסך …png`), news photos as the plate (0111, «כתבה על דולב»). Never a stock photo standing in for
the real thing.

Procedure, per named thing in the transcript (company, product, person, article, statistic):
1. **Find the primary source** with WebSearch/WebFetch: the company's own site for a logo (press/brand page
   first), the publisher's page for an article, the product itself for a UI. **Verify it is the real one
   before capturing** — `whiteboard.co.il` is a design-thinking studio in Bnei Brak; Alon's platform is
   `whiteboard.education`. The capture prints title + domain for exactly this check.
2. `scripts/web_capture.py "<draft>" page <url> --slug <ascii-slug> [--selector article]` or
   `… image <url> --slug …` → `ccstudio-web-<slug>.png` + a line in `ccstudio-web-sources.json`
   (url, title, time). SVG logos are rasterised at 2×. Slugs are lowercase ASCII.
3. Frame it the house way: `framed_asset()` in the landing build (rounded card on a blurred, darkened plate)
   for pages and screenshots; a logo goes bare, RGBA, scale 0.11–0.16, in the free column, `Fade In` /
   `Showing Up`, out with the sentence. One asset per mention; it enters on the word.
4. `register_media.py --write`, then the stills, then his render.

Say in the report where each asset came from (the sources file is the record). Screenshots of articles
and ads are quoted for commentary — keep the publisher's masthead visible; do not crop it into a fake.

## Verify before "done"

* a still at entry and at hold for each device, looked at: text between figure and background, no halo,
  no drift between the two copies, the logo the real logo;
* structural QA as always (0 overlaps, 0 dangling refs, his tracks byte-identical);
* `register_media.py --list` shows every `ccstudio-web-*` and `ccstudio-cutout-*`;
* his CapCut render of the window — a still is not a render.
