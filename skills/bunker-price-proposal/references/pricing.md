# Prices used in proposals (before VAT)

These are the prices Alon gave for proposals so far. The person asking for a proposal sets its prices; use this table only to fill a gap, and say so when you do. When Alon sets a new price, add a row with the date.

| item | price | source |
|---|---|---|
| Studio hour (שעת צילום באולפן) | ₪400 | Alon, 20.11.2026 («התמחור הרגיל») |
| 10 reels from a shoot | ₪1,500 (₪150/reel) | Alon, 20.11.2026 |
| Course filming day in the Bunker, up to 8h, 2×4K, incl. basic editing (camera routing, cuts, best takes, slide sync) | ₪5,000 | Alon, 20.11.2026 |
| SRT captions file per lesson | ₪3 per net minute after editing | Alon, 20.11.2026 |
| Burned-in captions in custom design + chapter titles | ₪10 per net minute after editing | Alon, 20.11.2026 |
| VSL for the course landing page (script, shoot, edit) | ₪2,000 | Alon, 20.11.2026 |
| Outdoor shoot (at the client's place) | +₪1,500 per filming day | `lib/leads/video-lead.ts` OUTDOOR_SHOOT_HINT |
| Course filming day on location  | ₪7,500 per day | proposal 18.10.2026 |
| Reschedule < 48h before a shoot | ₪250 | all course proposals |
| «ליווי צמוד» during the shoot (runs the prompter / presentation) | ₪250 per hour | Alon, 22.11.2026 (5 h studio ₪2,000 + 5 h escort with one hour free = ₪3,000) |
| A guest who helps with the prompter | free | Alon, 20.11.2026 |

Site prices (studio packages, Express ₪1,500 incl. the hour + full episode + 10 reels) live in `lib/pricing/price-switch.ts` and `lib/landing-express-content.ts`. A proposal may differ from the site; when it does, the person asking decides.
