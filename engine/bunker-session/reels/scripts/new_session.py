#!/usr/bin/env python3
"""Prepare <session>/רילס/remotion/{public,work} for the reels: shared SFX, the spec mood's music, the client logo,
the dialogue master (public/dialogue.m4a for Remotion, work/dialogue16k.wav for whisper and the silence snap).

    python3 new_session.py <session>
"""
import json, shutil, subprocess, sys
from pathlib import Path
from PIL import Image
from rpaths import session_paths

S, RM, PUB, WORK = session_paths(sys.argv)
FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
MUSIC = Path.home() / "VideoAssets/music"
MOOD = {"חם וקצבי": "warm_acoustic", "חם וקליל": "warm_acoustic", "אנרגטי": "beat_driven", "רגוע": "lofi_talk"}
for d in (PUB, WORK, RM / "out"):
    d.mkdir(parents=True, exist_ok=True)
shutil.copytree(Path(__file__).resolve().parent.parent / "assets/sfx", PUB / "sfx", dirs_exist_ok=True)
spec = json.loads((S / "אפיון.json").read_text(encoding="utf-8"))
mood = spec.get("reels", {}).get("music", {}).get("mood", "חם וקצבי")
shutil.copy2(MUSIC / f"{MOOD.get(mood, 'warm_acoustic')}-b_mid.full.mp3", PUB / "music.mp3")
logo = S / "לוגו.png"
if logo.exists():
    im = Image.open(logo).convert("RGBA")
    im.crop(im.getbbox()).save(PUB / "logo.png")
dlg = S / "פרק/דיאלוג.wav"
if dlg.exists():
    subprocess.run([FF, "-v", "error", "-y", "-i", str(dlg), "-c:a", "aac", "-b:a", "256k", str(PUB / "dialogue.m4a")], check=True)
    subprocess.run([FF, "-v", "error", "-y", "-i", str(dlg), "-ac", "1", "-ar", "16000", str(WORK / "dialogue16k.wav")], check=True)
for f in ("fixes.json", "who.json"):
    if not (WORK / f).exists():
        (WORK / f).write_text("[]")
print(f"מוכן: {RM}  ·  מוזיקה: {mood}  ·  לוגו: {'כן' if logo.exists() else 'אין'}  ·  דיאלוג: {'כן' if dlg.exists() else 'עוד לא'}")
