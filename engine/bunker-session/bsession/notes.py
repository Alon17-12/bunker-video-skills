"""Team / customer notes → structured items. A line we can't place is returned, never dropped."""
import re

TIME = r"(\d{1,2}:\d{2}(?::\d{2})?)"
DASH = r"\s*[—–-]\s*"
TARGET = r"(?:ריל\s*(\d+)|(פרק))"
INLINE = re.compile(rf"^{TARGET}\s*,?\s*(?:{TIME})?{DASH}(.+)$")
HEADING = re.compile(rf"^#+\s*{TARGET}\s*(?:[—–-].*)?$")
UNDER = re.compile(rf"^(?:{TIME}|כל ה(?:ריל|פרק))(?:{DASH}|\s+)(.+)$")
NAMES_TARGET = re.compile(r"^(?:ריל\s*\d+|פרק)\b")
EXC = ("רגע אחר", "ריל אחר", "ריל חדש", "להחליף את הריל", "קטע אחר")


def _secs(t: str | None) -> float | None:
    if not t:
        return None
    s = 0
    for part in t.split(":"):
        s = s * 60 + int(part)
    return float(s)


def _item(target, time, text):
    text = text.strip()
    return {"target": target, "time": _secs(time), "text": text, "exception": any(k in text for k in EXC)}


def parse_notes(text: str) -> dict:
    items, unparsed, current = [], [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if m := HEADING.match(line):
            current = int(m.group(1)) if m.group(1) else "פרק"
        elif m := INLINE.match(line):
            items.append(_item(int(m.group(1)) if m.group(1) else "פרק", m.group(3), m.group(4)))
        elif NAMES_TARGET.match(line):
            unparsed.append(line)                     # names a target we can't read — never guess
        elif current is not None and (m := UNDER.match(line)):
            items.append(_item(current, m.group(1), m.group(2)))
        elif current is not None:
            items.append(_item(current, None, line))
        else:
            unparsed.append(line)
    return {"items": items, "unparsed": unparsed}
