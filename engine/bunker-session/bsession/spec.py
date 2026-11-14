"""אפיון.json — the one form every agent reads. 'בלי גרפיקות' beats everything."""
import json, re
from pathlib import Path

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def load_spec(session: Path) -> dict:
    return json.loads((Path(session) / "אפיון.json").read_text(encoding="utf-8"))


def validate_spec(spec: dict, known_fonts: set[str]) -> list[str]:
    errs = []
    if not spec.get("client"):
        errs.append("חסר שם לקוח")
    sp = spec.get("speakers") or []
    if not sp:
        errs.append("חסרים דוברים")
    for s in sp:
        if s.get("mic") not in (1, 2):
            errs.append(f"דובר {s.get('name')}: מיקרופון חייב להיות 1 או 2")
        if not HEX.match(s.get("color", "")):
            errs.append(f"דובר {s.get('name')}: צבע לא תקין")
    font = spec.get("reels", {}).get("font")
    if font not in known_fonts:
        errs.append(f"הפונט {font} לא ברשימת הפונטים")
    for target in ("reels", "episode"):
        lg = spec.get(target, {}).get("logo", {})
        if lg.get("on") and not lg.get("path"):
            errs.append(f"לוגו ב-{target} מסומן בלי קובץ")
    cta = spec.get("episode", {}).get("cta", {})
    if cta.get("on") and not cta.get("text"):  # the bell banner (18.10) has text, an optional image and no link
        errs.append("באנר הפעמון מסומן בלי טקסט")
    return errs


def graphics_on(spec: dict) -> bool:
    return bool(spec.get("reels", {}).get("graphics"))


def logo_for(spec: dict, target: str) -> str | None:
    lg = spec.get(target, {}).get("logo", {})
    return lg.get("path") if lg.get("on") else None


def speakers(spec: dict) -> list[dict]:
    return list(spec.get("speakers") or [])
