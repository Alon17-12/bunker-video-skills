"""בדיקת מוכנות — מריצים אחרי ההתקנה ובכל פעם שמשהו לא עובד.

    ~/bunker-video-engine/.venv/bin/python ~/bunker-video-engine/doctor.py

Checks (Mac + Windows): Python, UTF-8 mode, ffmpeg/ffprobe, the Hebrew model, the face model,
the CapCut projects folder, and — the one that matters most — whether this CapCut version
stores projects in a format the engine can write (plain JSON, no Timelines/ split).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ENGINE = Path.home() / "bunker-video-engine"
sys.path.insert(0, str(ENGINE / "app"))
OK, WARN, BAD = "✓", "⚠", "✗"
problems = 0


def line(mark, text):
    global problems
    if mark == BAD:
        problems += 1
    print(f"  {mark} {text}")


def tool(name):
    for c in (Path.home() / "ffmpeg-bin" / name, Path.home() / "ffmpeg-bin" / f"{name}.exe",
              ENGINE / "bin" / name, ENGINE / "bin" / f"{name}.exe"):
        if c.exists():
            return str(c)
    return shutil.which(name)


print(f"מערכת: {sys.platform} · Python {sys.version.split()[0]}")
line(OK if sys.version_info >= (3, 11) else BAD, f"Python {sys.version_info.major}.{sys.version_info.minor}")
if os.name == "nt":
    line(OK if sys.flags.utf8_mode else BAD,
         "PYTHONUTF8=1 (בלי זה קבצי הפרויקט בעברית נקראים בקידוד הלא נכון)" if sys.flags.utf8_mode
         else "PYTHONUTF8 לא מוגדר — להריץ שוב את install.ps1 ולפתוח טרמינל חדש")

for t in ("ffmpeg", "ffprobe"):
    p = tool(t)
    if not p:
        line(BAD, f"{t} לא נמצא")
        continue
    v = subprocess.run([p, "-version"], capture_output=True, text=True).stdout.split("\n")[0]
    line(OK, f"{t}: {v[:60]}")

m = ENGINE / "models" / "ivrit-whisper-large-v3-turbo-ct2" / "model.bin"
line(OK if m.exists() else BAD, "מודל תמלול עברית" + ("" if m.exists() else " חסר — להריץ שוב את ההתקנה"))
y = ENGINE / "models" / "face_detection_yunet_2023mar.onnx"
line(OK if y.exists() else WARN, "מודל זיהוי פנים" + ("" if y.exists() else " חסר"))

try:
    import capcut
except Exception as e:  # noqa: BLE001
    line(BAD, f"מנוע הקפטן לא נטען: {e}")
    sys.exit(1)

d = capcut.DRAFTS_DIR
print(f"\nתיקיית הפרויקטים של CapCut: {d}")
if not d.exists():
    line(BAD, "לא קיימת. פותחים את CapCut, יוצרים פרויקט ריק אחד וסוגרים. אם CapCut שומר במקום אחר: "
              "מגדירים משתנה סביבה BUNKER_CAPCUT_DRAFTS לנתיב של com.lveditor.draft")
    sys.exit(1)
drafts = [p for p in d.iterdir() if p.is_dir() and not p.name.startswith(".")]
line(OK, f"{len(drafts)} פרויקטים")
line(OK if not capcut.capcut_running() else WARN,
     "CapCut סגור" if not capcut.capcut_running() else
     "CapCut פתוח — " + ("ב-Windows סוגרים אותו לגמרי לפני ש-Claude כותב לפרויקט" if os.name == "nt"
                         else "סוגרים את הפרויקט (חוזרים למסך הבית) לפני ש-Claude כותב אליו"))

# the format check: newest few drafts
versions, enc, split = set(), [], []
for p in sorted(drafts, key=lambda p: p.stat().st_mtime, reverse=True)[:8]:
    try:
        f = capcut._draft_file(p)
    except FileNotFoundError:
        continue
    raw = f.read_bytes()[:1]
    if raw != b"{":
        enc.append(p.name)
        continue
    try:
        j = json.loads(f.read_text(encoding="utf-8"))
        versions.add((j.get("last_modified_platform") or j.get("platform") or {}).get("app_version", "?"))
    except Exception:  # noqa: BLE001
        enc.append(p.name)
    if (p / "Timelines").is_dir():
        split.append(p.name)

if versions:
    line(OK, "גרסת CapCut בפרויקטים: " + ", ".join(sorted(versions)) + " (הכלים נבנו על 7.8 במק)")
if enc:
    line(BAD, f"{len(enc)} פרויקטים שמורים מוצפנים/לא כ-JSON ({', '.join(enc[:3])}) — "
              "המנוע לא יכול לכתוב אליהם. לעצור ולדבר עם אלון על גרסת CapCut.")
if split:
    line(WARN, f"{len(split)} פרויקטים עם תיקיית Timelines/ ({', '.join(split[:3])}) — בגרסאות 8.7+ CapCut "
               "עלול לקרוא את הטיימליין משם ולהתעלם משינויים. לבדוק על פרויקט ניסיון קודם (ראו windows.md).")
if not drafts:
    line(WARN, "אין עדיין פרויקטים — יוצרים פרויקט ריק אחד ב-CapCut ומריצים שוב")

fonts = Path.home() / "Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts"
if os.name == "nt":
    line(OK if (fonts / "Heebo-ExtraBold.ttf").exists() else WARN, f"פונטים לסקריפטים: {fonts}")

print("\n" + ("✓ הכול מוכן." if problems == 0 else f"✗ {problems} בעיות — לתקן לפני עבודה."))
sys.exit(1 if problems else 0)
