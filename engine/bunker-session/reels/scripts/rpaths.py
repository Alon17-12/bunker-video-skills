"""The one session every reels script works on: <session>/רילס/remotion/{public,work,out} (plan 2026-10-18, task 3)."""
import sys
from pathlib import Path


def session_paths(argv):
    if len(argv) < 2 or not (Path(argv[1]) / "יומן.md").exists():
        sys.exit("צריך נתיב לתיקיית הסשן (עם יומן.md) כארגומנט הראשון")
    s = Path(argv[1])
    rm = s / "רילס" / "remotion"
    return s, rm, rm / "public", rm / "work"


def reel_dir(picks, sid):
    """r3 → «03 - <title>» by the pick's own number n — never by its position (a dropped pick shifts positions)."""
    n = int(str(sid).lstrip("r"))
    p = next((p for p in picks if int(p["n"]) == n), None)
    if p is None:
        raise ValueError(f"אין בחירה מספר {n} ב-רילס/רילס.json")
    return f"{n:02d} - {p['title']}"


def listener_crop_x(face, cam, size=760, src_w=1920):
    """x of the square crop around the listener's face in a reaction sheet — from the session's face.json."""
    x = int(float(face[str(cam)]["x"]) * src_w) - size // 2
    return max(0, min(src_w - size, x))
