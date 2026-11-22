---
name: bunker-price-proposal
description: Write and send a Bunker price proposal («הצעת מחיר») as a branded Hebrew PDF — studio hour, reels, course filming day, captions, VSL — and send it to the client on WhatsApp from the Bunker number. Use whenever Alon or Dolev says «הצעת מחיר», «תכין הצעה ל…», «תשלח לו הצעת מחיר», «תוסיף להצעה», gives a client phone number together with a price/package, or asks to fix/resend a proposal. Not for tax invoices or receipts (חשבונית / קבלה) — those come from the bookkeeping system.
---

# הצעת מחיר — הבונקר

One proposal = one JSON file → `scripts/build_proposal.py` → a 3–4 page PDF in the house layout → check every page → send on WhatsApp only after the exact text is approved.

Three finished examples (approved by Alon):
- `examples/course-day.json` — course filming day, 2-stage payment, captions per minute, VSL add-on, course gallery (4 pages).
- `examples/studio-reels.json` — studio hour + 10 reels, prompter callout, reels gallery (3 pages).
- `examples/studio-hours-escort.json` — 5 studio hours + 5 hours close escort (one free), prompter + presentation, materials delivery, behind-the-scenes photo + studio people gallery (3 pages, 22.11.2026).

Start from the closer one, copy it, change it. Don't write a proposal from scratch.

## Workflow

1. **Who is the client.** Usually you get a phone number. If this session has the Bunker Supabase connector, look the lead up in `customers`:
   ```sql
   select id, name, email, phone, pipeline_stage, lead_source, utm_source, utm_campaign, created_at
   from customers where regexp_replace(coalesce(phone,''),'\D','','g') like '%<last 9 digits>';
   ```
   Use the name as written there (first name is fine). No row, or no Supabase connector → ask for the name.
2. **What's in it and what it costs.** The prices come from the person asking, in the message. `references/pricing.md` lists the prices Alon set so far — use them only to fill a gap, and **say which numbers you took from there**. Never invent a price. If something they asked for has no price (e.g. «ליווי צמוד»), list it without a number.
3. **Write the JSON** (copy an example to a scratch folder, not into the skill folder). Rules below.
4. **Build:**
   ```bash
   python ~/.claude/skills/bunker-price-proposal/scripts/build_proposal.py <file>.json --out-dir ~/Downloads
   ```
   Output: `הצעת מחיר - <client> - <title>.pdf` + `.html` (+ `-pages/page-N.png` if `pip install pymupdf`).
5. **Check every page** (open the PNGs or the PDF). Look for: a section cut across pages, a half-empty page followed by a spill page, numbers in the wrong order, a wrong name/price/total. Fix the JSON and rebuild. Don't hand over an unchecked PDF.
6. **Hand the PDF over** and list in 2–3 lines any decision you made yourself (a price from the table, a term you added).
7. **Send (only when asked).** Draft a short WhatsApp text, or use the text they gave you **word for word**. Show the exact text and wait for an explicit OK of that text. Then:
   ```bash
   python ~/.claude/skills/bunker-price-proposal/scripts/send_whatsapp.py --phone <phone> --pdf "<pdf>" --text-file msg.txt --dry-run
   python ~/.claude/skills/bunker-price-proposal/scripts/send_whatsapp.py --phone <phone> --pdf "<pdf>" --text-file msg.txt
   ```
   It sends one message (PDF + text as caption) from the Bunker WhatsApp, prints the `idMessage` and status. Later: `--status <idMessage>` → `sent` / `delivered` / `read`. Report the real status, not «נמסר» when it says `sent`.

## House rules (from Alon's corrections, 20.11.2026)

- **Page 1:** header, title, «לכבוד», short personal intro; the two sets side by side (קליניקה, בר) so the client can compare; «מי ילווה אותך» — Alon and Dolev in their bar photos. **No price on page 1** (Alon, 22.11.2026): the price appears only on the last page. The old dark bottom-line box is off by default (`show_bottom_box: true` brings it back). Keep `show_sets` / `show_team` on unless told otherwise.
- **Logo = the Bunker logo** (`brand/logo-bunker.png`, the default since 22.11.2026). Never the Alon Gabay logo on a Bunker proposal.
- **Dolev = «דולב סלע, המארח של הבונקר».** Not «מנהל האולפן». Alon = «מנהל הבונקר» (+ «מפיק קורסים דיגיטליים» on course proposals).
- **«מה כולל השירות» starts on its own page**, so it is never cut. The course gallery gets its own page under it. The price table starts the last page.
- **The total must be obvious:** one «סה״כ» row on the last page (before VAT, and incl. VAT on a second line). Items with a `unit` (per minute etc.) are options, not counted in the total.
- **Payment:** paid in advance — the payment books the date. Methods: «העברה בנקאית · ביט · כרטיס אשראי (עד 3 תשלומים)». When part of the price depends on something unknown yet (e.g. caption minutes known only after editing), split into stages: stage 1 paid now, stage 2 gets its own short proposal later, also paid in advance.
- **Standard terms** (use when relevant): reschedule < 48h before the shoot = ₪250; one correction round included, more priced by scope; validity 30 days.
- **Gallery:** `"courses"` for course/VSL work (4 named course stills + 6 more), `"reels"` for reels work, omit otherwise.
- **Photo sections** (`photo_sections`, under «מה כולל»): the behind-the-scenes photo (`bts/studio-lights-cameras.jpg` — cameras and lights in the studio) and/or a gallery of people who filmed in the Bunker (`people/*.jpg`). Rules from Alon (22.11.2026): no names or details of the person in a BTS photo; people shots wide (zoomed out — the whole chair and set, not a face close-up); don't put two similar shots (same curtain colour / same look) side by side; sharp source only (take frames from the 4K original, never a resized thumbnail). Check the page count after adding them — a gallery that spills alone onto a new page must be shrunk or moved.
- **Photos of people mid-sentence look bad.** If you add a new photo from a video, pick a frame with the mouth closed / a smile and no burned-in captions.
- **Links:** only links that work and show nothing private (a single-file share, never a folder).
- **Stats** in the copy need a source in brackets (e.g. «לפי Unbounce»). Don't make up numbers.
- **Prices before VAT** everywhere («₪X + מע״מ»), VAT 18% (`vat_percent` in the JSON if it changes).
- Hebrew only, no nikud, dates DD.MM.YYYY. No arrows (→ ←) in the text.

## JSON fields

| field | what |
|---|---|
| `client.name` | used in the file name, «לכבוד», footer |
| `date`, `valid_until` | `DD.MM.YYYY` |
| `title` | «הצעת מחיר – <title>» and the file name |
| `bottom_label` | text in the page-1 price box (only with `show_bottom_box: true`) |
| `greeting`, `intro` | opening lines (intro may hold `<strong>`) |
| `team.alon` / `team.dolev` | override the one-line descriptions |
| `includes[]` | `{heading, bullets[], callout?}` — `callout: true` = grey box with red edge (e.g. the prompter) |
| `photo_sections[]` | under «מה כולל»: `{heading?, feature?: {image, title?, bullets[]}, images?: [6 paths, 16:9, shown uncropped], caption?}` |
| `show_bottom_box` | `true` = put the old price box back on page 1 (default off) |
| `terms[]`, `terms_page` | «תיאום ציפיות»; `"includes"` puts it under «מה כולל» (when that page has room), `"price"` on the last page |
| `gallery` | `"courses"`, `"reels"` or omit |
| `items[]` | `{stage}` = section row · `{desc, price}` = counted in total · `{desc, price, unit}` = per-unit option, not counted |
| `total_label` | default «סה״כ» (e.g. «סה״כ לתשלום עכשיו») |
| `price_note` | small note under the table (an example calculation) |
| `payment_steps[]` | one item = a sentence; several = a numbered list |
| `addons[]` | «אפשר להוסיף בנפרד» |
| `closing`, `signature`, `logo`, `brand_title`, `payment_methods`, `vat_percent` | optional |

Numbers in text are wrapped automatically so they stay in order inside Hebrew lines. Text fields may contain simple HTML (`<strong>`, `<br>`, `<a href>`).

## Assets

`assets/` — sets (`sets/clinic.jpg`, `sets/bar.jpg`), team bar photos, course stills, reel stills, behind-the-scenes (`bts/`), people who filmed in the Bunker (`people/guest-1…6.jpg`), logos (`brand/logo-bunker.png` default, `brand/logo-alon.png` for Alon's own course-production proposals only if asked). Any other image: put an absolute path in the JSON where an asset path goes, or add it to `assets/` in a PR.

## Requirements

Python 3 (standard library) and Google Chrome or Edge. macOS and Windows. On Windows, run the scripts with the full path (`python "$env:USERPROFILE\.claude\skills\bunker-price-proposal\scripts\build_proposal.py" …`), since `~` is not expanded for Python arguments in every shell. `pymupdf` optional for page previews. Sending needs the Green API keys (`GREENAPI_INSTANCE_ID`, `GREENAPI_API_TOKEN`, `GREENAPI_API_URL`) in the environment or in a `.env.local` file inside this skill folder — get them from Alon, never commit them (`.env.local` is in `.gitignore`).

## Updating

Installed with `git clone` into `~/.claude/skills/bunker-price-proposal`. To get the latest version: `git -C ~/.claude/skills/bunker-price-proposal pull`.
