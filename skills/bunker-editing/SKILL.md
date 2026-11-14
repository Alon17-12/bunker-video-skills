---
name: bunker-editing
description: >-
  עריכת סרטונים — הבונקר. The whole בונקר אקספרס service (פרק מהיום למחר + 10 רילס) from the RØDECaster SSD folder
  and the client's spec HTML (אפיון) to two CapCut projects and a three-folder delivery (חומרי גלם · הפרק השלם · רילס):
  intake, who-is-who, mic dialogue, transcription, picks, hand-cut reels planned in Remotion and built in CapCut, the
  episode in CapCut with a picture-checked start/end and routing QA, mp3 + YouTube texts, team and client corrections.
  Use whenever Alon or the team says «בונקר אקספרס», «סשן אקספרס», «תערוך את הסשן של X», «התיקייה על ה-SSD»,
  «קובץ האפיון», «הערות לרילס/לפרק של X», «פרומפט תיקונים», «תמסור את הסשן», or points at a session or SSD folder —
  and for any Bunker podcast episode + reels job. Not for a צומת 20 episode (tsomet-20-episode) or a single stand-alone reel.
---

# עריכת סרטונים — הבונקר (בונקר אקספרס)

**השירות:** הלקוח מקליט בבונקר, ולמחרת מקבל פרק ערוך + 10 רילס, לפי טופס אפיון שמילא לפני הסשן; סבב תיקונים אחד.
**השיטה נבנתה על** «לקוח R #62» (17–18.10.2026, 3 סבבים מול אלון). כל כלל והסיבה שלו: `references/house-rules.md`.

```
PY=~/bunker-video-engine/.venv/bin/python      # python 3.12 + whisper + the CapCut library
cd ~/bunker-video-engine/bunker-session                       # every "$PY -m bsession …" and reels/scripts/… runs from here
```

**עם אלון ועם הצוות — עברית בלבד**, גם בשורות ההתקדמות. בסוף כל שלב: משפט אחד מה הסתיים ומה הבא.
`$PY -m bsession status "<session>"` לפני כל שלב — ממשיכים מהשלב הבא, אף פעם לא עושים שלב שהסתיים פעמיים.

## 0. מה צריך כדי להתחיל
- **תיקיית ההקלטה על ה-SSD** (מה שה-RØDECaster כתב: `… | וידאו/… | 1.mp4`, `… | 2.mp4`, `… | מקור.mp4`, `… | אודיו/`).
- **קובץ האפיון** `אפיון — <תוכנית> — <תאריך>.html` — מחלון הסשן ביומן או מתיקיית המסירה. **בלעדיו לא מתחילים**
  (הטופס הוא תנאי השירות); אם אין — מבקשים אותו. כמה קבצים (הלקוח שלח שוב) — לוקחים את האחרון; `bsession spec` שוב על
  סשן קיים שומר את «מי זה מי» ואת המותג מהאתר.
- מקום בדיסק: `df -h ~` — כל העבודה הכבדה על ה-SSD; כל רינדור מוחק את החבילה שלו.

## 1. סשן ואפיון
```
$PY -m bsession init "<ssd>/בונקר אקספרס" "<show>" <YYYY-MM-DD>
$PY -m bsession spec "<session>" "<אפיון….html>"        # → אפיון.json + אפיון.html בסשן (references/spec-format.md)
$PY -m bsession check-spec "<session>"
```
`landing_page.url` עם `brand` ריק → שואבים מהאתר פונט, צבעים, לוגו וערכים ל-`landing_page.brand` (כמו בלקוח M ובבונקר).
**הפונט של הרילס = הפונט שהאתר באמת מציג** (בבונקר Heebo — נבדק ב-CSS החי).

## 2. קליטה
```
$PY -m bsession ingest "<ssd folder>" "<session>" --in-place      # בלי העתקה מה-SSD
```
יציאה 1 → מראים לאלון את הבעיות כמו שהן ועוצרים (שתי הקלטות בתיקייה, קובץ קטוע, מצלמה לא מסונכרנת).

## 3. מי זה מי
פריים אחד מכל מצלמה (`ffmpeg -ss 200 … -frames:v 1`) → אלון/איש צוות מאשר מי בכל מצלמה → `speakers[].mic/camera` ו-`camera_confirmed`
באפיון. המארח = זהב, השאר לבן.

## 4. במקביל — דיאלוג ותמלול
- `$PY ~/.claude/skills/bunker-editing/vendor/mic_dialogue.py master "<אודיו>" "<session>/פרק/דיאלוג.wav"` + `check` חייב PASS
  (סאונד רק מהמיקרופונים, אף פעם לא Live-Mix).
- **3 מיקרופונים ומעלה / מיקרופון USB:** `$PY skill/scripts/mic_dialogue_n.py bleed "<אודיו>"` → מיקרופון ששומע דובר אחר
  ב־> ‎-15 dB מקבל `--gate K`; USB ליד XLR מקבל `--eq K=R`, כש־R = מיקרופון ה־XLR של הדובר **שיושב לידו** (צריך לשמוע
  כל אחד מהשניים במיקרופון של השני). אחרי התמלול (צריך אותו ל־gate, ל־EQ ולרמות):
  `$PY skill/scripts/mic_dialogue_n.py master "<אודיו>" "<session>/פרק/דיאלוג.wav" --eq 3=2 --gate 2,3 --words "<session>/תמלול/transcript.json"`
  עם `--words` ה־EQ נמדד על **אותם קולות** בשני המיקרופונים והרמות לפי המילים של כל דובר — אורח C 27.10, «הגרסה הזאת
  ממש טובה»; למה: `references/house-rules.md` § סאונד. לפני הפרק השלם: דוגמת 38 שנ׳ לפני/אחרי (`--start S --dur 120`).
- `nohup $PY -m bsession transcribe "<session>" > "<session>/.tmp/transcribe.log" 2>&1 &` (~7 דק' לפרק של 14 דק').

## 5. בחירה
סוכן עם `references/pick-agent.md` → `רילס/רילס.json` (`reels.count`, 10 בשירות) → `$PY -m bsession check-picks "<session>"` עד שעובר.

## 6. רילס — תוכנית ב-Remotion, פרויקט בקאפקאט
**קודם `references/reels-checklist.md`** — סדר העבודה והבדיקות שמונעים סבבים (לקוח A: 6 סבבים על משימה בסיסית). הכל ב-`references/reels.md`. בקצרה, לפי הסדר:
1. `python3 reels/scripts/new_session.py "<session>"` — `<session>/רילס/remotion/{public,work}` (SFX, מוזיקה לפי המצב, לוגו, דיאלוג).
2. `$PY reels/scripts/qa_transcribe.py "<session>" <טווחים>` — פענוח שני במודל המלא; תיקוני מילים **לפי זמן** ב-`work/fixes.json`.
3. `work/edl_rN.sh` לכל ריל (חיתוך ידני, **`tighten_edl.py … --story`** — השתיקה בונה מתח) → `$PY reels/scripts/build_cuts.py "<session>"`
   → `$PY reels/scripts/refine_edges.py "<session>"` (קצוות על השקט + מרווח נשימה).
4. צבע לחלונות (`grade_windows.py` עם `Bunker.cube` → `public/`); מיקום הפנים:
   `python3 ~/.claude/skills/bunker-editing/vendor/teaser/face_pos.py "<מצלמה 1>" "<מצלמה 2>" --samples 40` → `public/face.json`
   (`{"1": {"x","y"}, "2": {"x","y"}}`; מצלמה שבה הדובר מסתכל הצידה — לבדוק בעין בפריים).
5. `$PY reels/scripts/react_sheets.py "<session>"` → תגובות אמיתיות בעין → `public/plans.json` (תגובות, מסכים משולבים, זום, תוויות, מונה).
6. `npx tsx reels/scripts/dump.ts "<session>"` חייב «all reels clean»; `node reels/scripts/stills.mjs "<session>" rN "t,…"` — מסתכלים.
7. `npx tsx reels/scripts/export_capcut.ts "<session>"` → `node reels/scripts/render_gfx.mjs "<session>"` →
   (קאפקאט סגור) `$PY reels/scripts/capcut_reels.py "<session>" "<show> · 10 רילס · <date>"` — פרויקט אחד, חוצץ לפני כל ריל.
8. תצוגה לבדיקה בלי לפתוח קאפקאט: `PROJ="<project>" python3 reels/scripts/capcut_preview.py out.jpg "t1,t2"`.
אם אלון רוצה לראות קובץ לפני קאפקאט: `node reels/scripts/render.mjs "<session>" v1 r1,r2 2` (4K) + `$PY reels/scripts/reel_asr_qa.py "<session>" v1`.

## 7. פרק — קאפקאט
הכל ב-`references/episode.md`: התחלה וסוף **לפי התמונה** → `$PY skill/scripts/routing_audit.py "<session>" --from <in> --to <out>` →
עין על כל מקרה → `skill/scripts/routing_patches.py --keep …` → `routing_smooth.py` → **`routing_frames.py` (לפריים, אחרי `decode_small.py`) ובסוף `routing_verify.py` חייב 0** (בלי הבזקים — `references/house-rules.md` § ניתוב בפרק) → `$PY skill/scripts/build_session_episode.py "<session>" --trim-in … --trim-out …
--first "<שם>=<s>" --patches "<session>/פרק/תיקוני-ניתוב.json"` → `פרק/יוטיוב.json` (כותרת, תיאור, פרקים).

גרסה חדשה של פרק קיים (תיקוני ניתוב / סאונד חדש) — לא בונים מחדש: `skill/scripts/episode_repatch.py "<v1>" "<v2>" <patches> --trim-in … --audio-m4a`
מצלמה שנכנס אליה מישהו מהקצה (יד/ראש של המארח) — זום קבוע לכל הפריימים שלה: `routing_cover.py "<session>" --in <patches> --out <p2> --cam 2`
(כל שוט של המצלמה, גם מה שהיה חי ב«מקור», הופך לתיקון מהקובץ שלה) → `episode_repatch.py … <p2> --zoom 2=1.12:-0.12` (12 %, הקצה הימני נשאר).
בדיקה: אף פריים של המצלמה בשדרה בלי תיקון, `routing_verify` 0 הבזקים/קפיצות, סטילס של רגעי הכניסה (אורח C 27.10).
(הסאונד בתוך תיקיית הטיוטה — קאפקאט לא קורא מה־SSD: «File not accessible»).

## 8. ייצוא (איש צוות — לקאפקאט אין ייצוא משורת פקודה)
- הפרק → `<session>/פרק/פרק.mp4`. אם «מקור» מחוץ לתיקיית הטיוטה — Relink פעם אחת.
- פרויקט הרילס → `<session>/רילס/ייצוא.mp4` (כל הפרויקט, 4K 30fps, ההגדרות של הפרויקט).

## 9. מסירה
`$PY -m bsession deliver "<session>"` → `מסירה/הפרק השלם/` (mp4, mp3 ב-‎-16 LUFS, `כותרת ליוטיוב.txt`, `תיאור ליוטיוב.txt`),
`מסירה/רילס/` (כל ריל כקובץ — נחתך מהייצוא לפי `רילס/capcut-layout.json`), `מסירה/חומרי גלם/`. איש צוות גורר כל תיקייה
לתיקייה באותו שם במסירה בבונקר. **הסוכן לא כותב לבונקר.**

## 10. תיקונים
הפרומפט מ«העתק פרומפט» בבונקר נשמר ב-`תיקונים/<סבב>.md` →
`$PY -m bsession corrections "<session>" "תיקונים/<סבב>.md"` (פורמט: `references/corrections-format.md`) → רשימת עבודה עם זמנים
והמילים שנאמרו → ביצוע לפי `references/corrections.md` → פרויקט קאפקאט בשם גרסה חדש (לעולם לא מעל פרויקט שאלון ערך ידנית).

## כללים שלא מתפשרים עליהם (הסיבות ב-`references/house-rules.md`)
1. ניתוב = מי שמדבר; מצלמה על השותק רק בתגובה אמיתית (צחוק, יד על הפה).
2. כל מילה מדוברת מופיעה פעם אחת; אין שתי כתוביות יחד; אין מילה חתוכה.
3. סאונד דיבור רק מהמיקרופונים.
4. פנים לא מכוסות בשום גרפיקה.
5. זום רך שנוחת על מילת מפתח, לא זום-קאט; מסך משולב בחילופי דברים; אין מסגור שעומד מעל ~6 שנ'.
6. הפונט מאתר הלקוח; המארח זהב, האורח לבן, קו מתאר שחור; מילה חמה אחת.
7. הפרק מתחיל ונגמר לפי התמונה — בלי התיישבות, סידור מיקרופונים או טלפון.
8. לפני כל שליחה: סטילס של כל מה שהשתנה, ובדיקה אוטומטית נקייה — כולל `routing_verify.py` (פרק) ו-`capcut_flash_fix.py` (רילס): אף קפיצת פריים.
9. אף פעם לא כותבים לפרויקט קאפקאט כשקאפקאט פתוח.
10. גרסאות ישנות לפח רק כשאלון אומר; אף פעם לא מוחקים לצמיתות.

## זמנים (נמדד בפיילוט)
פרק של 14 דק' + 4 רילס: ~45–50 דק' מקצה לקצה (קליטה 1, תמלול 7, בחירה 2, רילס ~30, פרק ~10 במקביל). פרק של שעה + 10 רילס: ~שעתיים.
רוב הזמן הוא העבודה בעין — חיתוך ידני, תגובות, התחלה/סוף. החלק המכני מהתוכנית ועד פרויקט קאפקאט (18.10.2026, 4 רילס):
`build_cuts` 2 שנ' · `dump` + `export_capcut` 1 שנ' · `render_gfx` 26 שנ' · `capcut_reels` 33 שנ' · `deliver` 15–60 שנ' (עם ה-mp3).
