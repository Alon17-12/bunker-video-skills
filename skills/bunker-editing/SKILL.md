---
name: bunker-editing
description: >-
  עריכת סרטונים — הבונקר. The whole בונקר אקספרס service (פרק מהיום למחר + 10 רילס) from the RØDECaster SSD folder
  and the client's spec HTML (אפיון) to two CapCut projects and a three-folder delivery (חומרי גלם · הפרק השלם · רילס):
  intake, who-is-who, mic dialogue, transcription, picks, hand-cut reels planned in Remotion and built in CapCut, the
  episode in CapCut with a picture-checked start/end and routing QA, mp3 + YouTube texts, team and client corrections.
  Use whenever Alon or the team says «בונקר אקספרס», «סשן אקספרס», «תערוך את הסשן של X», «התיקייה על ה-SSD»,
  «קובץ האפיון», «הערות לרילס/לפרק של X», «פרומפט תיקונים», «תמסור את הסשן», or points at a session or SSD folder —
  and for any Bunker podcast episode + reels job. Also use for the Bunker's OWN content reels shot as takes (not cut from
  an episode): «תוכן הבונקר <תאריך>», «טייקים לרילס», «רילס לבונקר מהטייקים» — references/content-reels.md.
  And when Alon already cut the content reels himself in CapCut and wants them dressed in the house style — «הפרויקט זה
  רילס לעריכה <תאריך>», «לערוך לפי הסגנון העדכני (צבע, מעקב מצלמה, כתוביות, מוזיקה)», «כשאני מצביע למעלה תראה אייקונים»,
  «שכל שתי שניות יקרה משהו» — references/content-reels-dress.md.
  And for a CLIENT's podcast reels edited in Remotion at premium level from times or quotes Alon hands over — «תגזור רילס
  לפי הזמנים האלה», «הוק … התחלה … סיום», «לא בטוח אם הוא סימן לפי המקור או לפי הרז», «תערוך ב-remotion לפי הסקיל»,
  «תעלה לו למערכת שיוכל לסמן תיקונים» — references/podcast-reels-remotion.md (clocks, finding a quote in another
  session, cut/route/split, follow camera, LUT sheet, graphics, 4K checked against the 720, delivery through the admin).
  And for a «רז» — the routed full episode of a recording as an editable CapCut project: «תכין קובץ רז», «רז לסשן של X»,
  «מצלמות 1+2, ניקוי פתיחה וסיום, LUT, פייד, ניתוב לפי גלי הקול», «לא יותר מדקה בלי לראות את הדובר השני» —
  references/raz.md (mic routing, media inside the draft, listener cutaways on Alon's current timeline).
  Not for a צומת 20 episode (tsomet-20-episode) or a single stand-alone reel. Long-form outside Express — a digital
  course, a multi-episode interview project, a VSL — is long-form-editing.
---

> **Windows:** לפני העבודה הראשונה במחשב Windows, קרא `~/.claude/skills/bunker-editing/references/windows.md`: מה שונה (נתיבים, CapCut סגור לגמרי, כוננים, מקודדים) ובדיקת המוכנות `doctor.py`.

# עריכת סרטונים — הבונקר (בונקר אקספרס)

**השירות:** הלקוח מקליט בבונקר, ולמחרת מקבל פרק ערוך + 10 רילס, לפי טופס אפיון שמילא לפני הסשן; סבב תיקונים אחד.
**האפיון:** `~/bunker-video-engine/projects/bunker-session/docs/superpowers/specs/2026-10-18-bunker-express-design.md`.
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
- `$PY ~/.claude/skills/tsomet-20-episode/scripts/mic_dialogue.py master "<אודיו>" "<session>/פרק/דיאלוג.wav"` + `check` חייב PASS
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
**קודם `references/reels-checklist.md`** — סדר העבודה והבדיקות שמונעים סבבים (לקוח B: 6 סבבים על משימה בסיסית). הכל ב-`references/reels.md`. בקצרה, לפי הסדר:
1. `python3 reels/scripts/new_session.py "<session>"` — `<session>/רילס/remotion/{public,work}` (SFX, מוזיקה לפי המצב, לוגו, דיאלוג).
2. `$PY reels/scripts/qa_transcribe.py "<session>" <טווחים>` — פענוח שני במודל המלא; תיקוני מילים **לפי זמן** ב-`work/fixes.json`.
3. `work/edl_rN.sh` לכל ריל (חיתוך ידני, **`tighten_edl.py … --story`** — השתיקה בונה מתח) → `$PY reels/scripts/build_cuts.py "<session>"`
   → `$PY reels/scripts/refine_edges.py "<session>"` (קצוות על השקט + מרווח נשימה).
4. צבע לחלונות (`grade_windows.py` עם `Bunker.cube` → `public/`); מיקום הפנים:
   `python3 ~/.claude/skills/ai-reel-remotion/scripts/teaser/face_pos.py "<מצלמה 1>" "<מצלמה 2>" --samples 40` → `public/face.json`
   (`{"1": {"x","y"}, "2": {"x","y"}}`; מצלמה שבה הדובר מסתכל הצידה — לבדוק בעין בפריים).
5. `$PY reels/scripts/react_sheets.py "<session>"` → תגובות אמיתיות בעין → `public/plans.json` (תגובות, מסכים משולבים, זום, תוויות, מונה).
6. `npx tsx reels/scripts/dump.ts "<session>"` חייב «all reels clean»; `node reels/scripts/stills.mjs "<session>" rN "t,…"` — מסתכלים.
7. `npx tsx reels/scripts/export_capcut.ts "<session>"` → `node reels/scripts/render_gfx.mjs "<session>"` →
   (קאפקאט סגור) `$PY reels/scripts/capcut_reels.py "<session>" "<show> · 10 רילס · <date>"` — פרויקט אחד, חוצץ לפני כל ריל.
8. תצוגה לבדיקה בלי לפתוח קאפקאט: `PROJ="<project>" python3 reels/scripts/capcut_preview.py out.jpg "t1,t2"`.
אם אלון רוצה לראות קובץ לפני קאפקאט: `node reels/scripts/render.mjs "<session>" v1 r1,r2 2` (4K) + `$PY reels/scripts/reel_asr_qa.py "<session>" v1`.

## 7. פרק — קאפקאט
**תוכן ארוך מחוץ לאקספרס** (קורס, כמה פרקים בפרויקט אחד, VSL) → הסקיל `long-form-editing`: שלוש גרסאות, ברירות מחדל לכל סוג, ושער `longform_gate.py` לפני כל מסירה. השער רץ גם על פרק אקספרס.
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

## «רז» — הפרק המנותב כפרויקט קאפקאט («תכין רז», «קובץ רז לסשן של X»)
**`references/raz.md`** — לקרוא קודם. נבנה 22.11.2026 על מנחה M3 + מנחה R2, «מעולה». הכלים ב-`scripts/raz/`.
1. **התוצר = פרויקט קאפקאט** שאלון מתקן בעצמו, לא mp4 (`render.py` רק כשמבקשים קובץ).
2. **ניתוב:** משתי המצלמות לפי המיקרופונים (`route.py`, ‏6 dB, תגובה < 1 שנ' לא תופסת מסך, שוט ≥ 2 שנ'). «מקור» לא משמש.
3. **התחלה וסוף:** מהמילים (`edges.py`) ומהשקט במעטפות. בלי צוות יוצא ובלי פתיחה שנכשלה. טייק חוזר באמצע מציינים, לא חותכים.
4. **בנייה** (`build_raz_project.py`): מצלמה 1 = שדרה, מצלמה 2 = מסלול «ניתוב», LUT הבונקר ב-1.0, פייד 0.5, דיאלוג מהמיקים.
5. **המדיה לתוך הטיוטה** (`localize_media.py`) לפני שאלון פותח. אחרת «File not accessible», והוא לא עושה Relink. בודקים מקום בדיסק.
6. **הקשבה** (`listener_plan` → `edge_check` → `listener_apply`): אף מצלמה לא מעל 60 שנ' ברצף.
   - קאטים בהפסקות של הדובר, המאזין שותק ורגוע, בלי יד בפריים מהקצה.
   - תמיד על הטיוטה החיה, אחרי החיתוכים של אלון.

## רילס תוכן כשאלון כבר חתך בקאפקאט («רילס לעריכה <תאריך>», «תערוך לפי הסגנון העדכני»)
**`references/content-reels-dress.md`** — לקרוא קודם. הלבשה של החיתוך שלו ב-Remotion (מנוע C1911, אושר 19.11.2026):
אייקונים עם Pop מעל האצבע בכל הצבעה, בירול 16:9 מאחורי הראש (שכבת דמות חתוכה), כתוביות שהגיוון שלהן בפריסה ולא בתנועה,
מילה־מילה רק איפה שהוא מבקש, בדיקת צפיפות (משהו בכל ~2 שנ'), קובץ נפרד לכל ריל, 720 → «מאושר» → 4K → כונן + Drive → מייקי.

## רילס מפודקאסט של לקוח ב-Remotion («תגזור רילס לפי הזמנים», «תערוך ב-remotion לפי הסקיל»)
**`references/podcast-reels-remotion.md`** — לקרוא קודם. פרויקט-דוגמה N3 20.11.2026, שבעה סבבים עד «מדהים», מנוע CClient:
1. **איתור:** באיזה שעון הוא סימן (מצלמות או «רז», לכל סשן בנפרד), המילים קובעות. ציטוט שלא נמצא מחפשים ב-`reel_transcripts` של שאר הסשנים.
2. **חיתוך:** רק בשקט מדוד, בדיקת שני המיקים במעברי דוברים, והשהיה שקטה אחרי הוק.
3. **ניתוב ופריימינג:** ניתוב לפי המיקים, מסך מפוצל בחילופי דברים, מעקב ראש עדין (calm), וזום שמתחלף רק בקאט אמיתי.
4. **צבע:** דף LUT לבחירה של אלון.
5. **כתוביות וגרפיקה:** כתוביות y 1300, בירולים של הלקוח בלי כפילויות, ובירול AI ב-Wan.
6. **סאונד:** המוזיקה 20 dB מתחת לדיבור המנורמל.
7. **4K:** מושווה פריים-פריים ל-720 המאושר.
8. **מסירה:** ליד הגלם ב-`רילס/` (לא לדרייב). אחר כך האדמין החדש: «ריל מוכן — העלאה ישירה» (חיוב או מתנה לפי אלון), ושליחה רק אחרי «שלח».

## רילס תוכן של הבונקר: טייקים, לא מתוך פרק
**`references/content-reels.md`** — התהליך מ-17.11.2026 לפי הסדר:
1. **סידור התיקייה:** תיקייה לכל טייק, בתוכה מצלמות 1–2, אודיו 1–2, ‏Live-Mix ומקור.
2. **פרויקט קאפקאט:** ‏Multi-camera לכל טייק. כל מצלמה מותאמת ל-9:16: מירכוז, עיניים על השליש העליון. שכבת Adjust עם הפריסט «הבונקר». עריכת מולטי-קאם.
3. **אלון בוחר את הקטעים.**
4. **Remotion בגרסאות:** ‏720p עם ציון זמן לבקרה, הערות ותיקונים, ואחרי אישור 4K.

ערוץ קול אחד, בלי שני עותקי מצלמה מושמעים. אין גרייד מפרויקט תבנית של לקוח אחר.

## כללים שלא מתפשרים עליהם (הסיבות ב-`references/house-rules.md`)
0. מחיקות בפרק ארוך: מציעים כבלוקים במסלול «למחיקה» וכקובץ SRT, ולא חותכים בעצמנו. בלוק שנשאר אחרי שאלון עבר = מאושר וחותכים. בלוק שנמחק = נדחה. עריכה ידנית של אלון = נשמרת. כל מחיקה שבוצעה מקבלת מרקר אדום לוידוא. הפירוט ב-`references/episode.md`.
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
