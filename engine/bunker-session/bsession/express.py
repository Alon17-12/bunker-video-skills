"""The Bunker Express spec form → אפיון.json. The client fills the form in the Bunker; the submit renders ONE HTML file
into the delivery: a page people read, with the data embedded for this reader (spec 2026-10-18, schema v1)."""
import json, re

BLOCK = re.compile(r'<script[^>]*id="bunker-express-spec"[^>]*>(.*?)</script>', re.S)
TONE_MOOD = {"warm": "חם וקצבי", "calm": "רגוע", "energetic": "אנרגטי", "light": "חם וקליל"}
HOST, GUEST = "#F6C453", "#FFFFFF"          # house colours: the host gold, everyone else white


def read_express_html(text: str) -> dict:
    m = BLOCK.search(text)
    if not m:
        raise ValueError("לא נמצא בלוק האפיון בקובץ — זה לא קובץ אפיון של בונקר אקספרס")
    x = json.loads(m.group(1))   # the renderer writes "<\/" for "</" inside the JSON, so the match ends at the real tag
    if x.get("v") != 1:
        raise ValueError(f"גרסה לא נתמכת של האפיון: {x.get('v')}")
    return x


def to_session_spec(x: dict) -> dict:
    look, reels, ep = x.get("look") or {}, x.get("reels") or {}, x.get("episode") or {}
    speakers = [{"name": p.get("name", ""), "role": p.get("role", ""), "mic": i + 1, "color": HOST if i == 0 else GUEST}
                for i, p in enumerate(x.get("speakers") or [])]
    logo = "לוגו.png" if look.get("logo_url") else None
    cta = ep.get("cta") or {}
    return {
        "client": x.get("client") or x.get("show", ""), "show": x.get("show", ""), "booking_date": x.get("booking_date"),
        "speakers": speakers, "terms": list(x.get("terms") or []), "notes": x.get("notes", ""),
        "reels": {"count": int(reels.get("count") or 10), "font": "Heebo", "graphics": True,
                  "music": {"on": bool(reels.get("music", True)), "mood": TONE_MOOD.get(reels.get("tone"), "חם וקצבי")},
                  "logo": {"on": bool(reels.get("logo")), "path": logo or ("לוגו.png" if reels.get("logo") else None),
                           "source": "הטופס" if logo else "האתר"},
                  "tone": reels.get("tone", ""), "reference_reel": reels.get("reference_url") or None},
        "episode": {"names_on_screen": bool(ep.get("names_on_screen", True)),
                    "logo": {"on": bool(ep.get("logo")), "path": "לוגו.png" if ep.get("logo") else None,
                             "source": "הטופס" if logo else "האתר"},
                    # one banner since 18.10: the YouTube bell («לא לשכוח ללחוץ על הפעמון»), photo · text · bell · arrow down
                    "cta": {"on": bool(cta.get("on")), "style": "bell", "text": cta.get("text") or "לא לשכוח ללחוץ על הפעמון",
                            "image": cta.get("image") or None, "link": "", "at": ""},
                    "intro": bool(ep.get("intro")), "outro": bool(ep.get("outro")),
                    # the client's files, paths inside the delivery («חומרי גלם/מהלקוח/…»)
                    "intro_media": ep.get("intro_media") or None, "outro_media": ep.get("outro_media") or None},
        # a link AND an uploaded logo → the uploaded logo wins; the site gives colours and fonts, never a second logo
        "landing_page": {"url": look.get("site_url") or None, "brand": None, "mode": look.get("mode", "brand"),
                         "logo_from_site": not logo},
        "template": bool(x.get("template")),
    }


KEEP_PER_SPEAKER = ("mic", "camera", "camera_confirmed", "color")


def carry_over(new: dict, old: dict) -> tuple[dict, list[str]]:
    """A re-submitted form must not undo what the team already settled: who is on which mic/camera (matched by name)
    and the brand pulled from the client's site."""
    kept = []
    by_name = {p.get("name"): p for p in old.get("speakers") or []}
    for p in new.get("speakers") or []:
        o = by_name.get(p.get("name"))
        if o and o.get("camera_confirmed"):
            for k in KEEP_PER_SPEAKER:
                if k in o:
                    p[k] = o[k]
            kept.append(f"מי זה מי: {p['name']}")
    brand = (old.get("landing_page") or {}).get("brand")
    if brand and not (new.get("landing_page") or {}).get("brand"):
        new.setdefault("landing_page", {})["brand"] = brand
        kept.append("המותג מהאתר")
    return new, kept
