# כלי העריכה של הבונקר — סקילים ל-Claude Code

ערכת הכלים שבה הבונקר עורך פודקאסטים: פרק שלם, רילס 9:16, תמלול וכתוביות בעברית, זיהוי רגעים ויראליים
וחיתוך בין המצלמות לפי המיקרופונים. הכול עובד בתוך **Claude Code** ו-**CapCut לדסקטופ**: Claude כותב את
פרויקט ה-CapCut עצמו, ואתם פותחים, בודקים ומייצאים.

## מה יש כאן

| סקיל | מה הוא עושה | איך מבקשים |
|---|---|---|
| `bunker-editing` | התהליך המלא מהקלטה לפרויקטים מוכנים: קליטת תיקיית ה-RØDECaster, מי זה מי, סאונד מהמיקרופונים, תמלול, בחירת רגעים לרילס, פרק 16:9 ב-CapCut, רילס, מסירה וסבב תיקונים | «תערוך את הסשן של X», «התיקייה על ה-SSD», «הערות לרילס של X» |
| `podcast-reels-9x16` | רילס 9:16 מפודקאסט עם 2 מצלמות: מולטי-קאם, מסך מפוצל, כתוביות בצבע לפי דובר, כותרות, בירולס, מוזיקה, LUT, סבבי תיקונים | «תכין רילס מהפרק», «רילס 1 הוק 11:00 … סיום 12:52», «תוסיף מסך מפוצל» |
| `podcast-multicam-edit` | חיתוך אוטומטי בין המצלמות לפי מי שמדבר (מגלי הקול של המיקרופונים) | «נתב לפי מי שמדבר», «אין רצף מעל 8 שניות» |
| `hakapitan-captions` | תמלול עברית מקומי (ivrit-ai) ישירות מהטיימליין הערוך: SRT, כתוביות לתוך הפרויקט, השלמת כתוביות חסרות, בקרת איכות | «תמלל את הפרק», «תוציא SRT», «תוסיף כתוביות לפרויקט X» |
| `video-breakdown` | ניתוח סרטוני רפרנס (יוטיוב/אינסטגרם): קצב חיתוכים, כתוביות, סאונד, כדי לשחזר סגנון | «תנתח לי את הריל הזה», «מה הסגנון של הקריאטור» |
| `bunker-price-proposal` | הצעת מחיר ממותגת של הבונקר כ-PDF: לוגו, הסטים, הצוות, מה כולל, תמונות מהאולפן, המחיר רק בעמוד האחרון. אחר כך שליחה ללקוח בוואטסאפ ממספר הבונקר, רק אחרי שאישרתם את נוסח ההודעה | «תכין הצעת מחיר ל-050…: שעת אולפן 400 + 10 רילס 1,500» |

מתחת לסקילים יש **מנוע** (`engine/`), שמותקן אל `~/bunker-video-engine`:
- `app/`: ספריית "הקפטן" שקוראת וכותבת פרויקטים של CapCut ומתמללת.
- `bunker-session/`: כלי הסשן (`python -m bsession …`) ופרויקט Remotion לגרפיקה של הרילס.

## דרישות

- **מק** עם Apple Silicon (M1 ומעלה), **או Windows 10/11 ‏64-bit**
- [Claude Code](https://claude.com/claude-code). ב-Windows צריך גם [Git for Windows](https://git-scm.com/download/win), כי Claude Code מריץ פקודות דרך Git Bash.
- [CapCut לדסקטופ](https://www.capcut.com/)
- [Node.js](https://nodejs.org), בשביל Remotion (רילס עם גרפיקה). ב-Windows המתקין מנסה להתקין אותו לבד.
- כ-5GB פנויים. מודל התמלול לבדו שוקל 1.6GB.

## התקנה — מק

```bash
git clone https://github.com/Alon17-12/bunker-video-skills.git
cd bunker-video-skills
./install.sh
```

## התקנה — Windows

פותחים **PowerShell** ומריצים:

```powershell
git clone https://github.com/Alon17-12/bunker-video-skills.git
cd bunker-video-skills
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

ההתקנה ב-Windows עושה גם את הדברים הבאים:
- מסדרת קיצורי דרך, כך שהפקודות בסקילים (שנכתבו למק) רצות כמו שהן.
- מתקינה את הפונטים של הבית: Heebo, ‏Assistant, ‏Fredoka.
- מגדירה `PYTHONUTF8=1`, בשביל שמות קבצים ופרויקטים בעברית.

**לפני העבודה הראשונה:** פותחים ב-CapCut פרויקט ריק אחד וסוגרים את התוכנה. אחר כך פותחים שיחה חדשה ב-Claude Code
ומבקשים: «תקרא את windows.md ותריץ את doctor.py». ב-Windows סוגרים את CapCut **לגמרי** לפני ש-Claude כותב לפרויקט.
כל ההבדלים מפורטים ב-[`skills/bunker-editing/references/windows.md`](skills/bunker-editing/references/windows.md).

## אחרי ההתקנה (בשתי המערכות)

ההתקנה מכניסה את הסקילים ל-`~/.claude/skills`, ובנוסף מתקינה Python 3.12 ואת הספריות, ffmpeg, מודל תמלול
עברית ומודל זיהוי פנים. סקיל שכבר קיים אצלכם לא נדרס. כדי להחליף אותו מריצים `./install.sh --force`
(ב-Windows: ‏`-Force`), והגרסה הישנה נשמרת כגיבוי.

אחרי ההתקנה פותחים **שיחה חדשה** ב-Claude Code, והסקילים נטענים לבד. בדיקת מוכנות אפשר להריץ בכל רגע:

```bash
~/bunker-video-engine/.venv/bin/python ~/bunker-video-engine/doctor.py
```

## עדכון

```bash
git pull
./install.sh --force
```

ב-Windows: `git pull`, ואחריו `powershell -ExecutionPolicy Bypass -File .\install.ps1 -Force`.

**כלים אופציונליים** (כבדים, ולכן לא מותקנים מראש):
- ניקוי קול בחדר (`voice_clean.py`): ‏`uv pip install --python ~/bunker-video-engine/.venv/bin/python nara_wpe deepfilternet soundfile`
- חיתוך דמות מהרקע (`matte_clip.py`): ‏`rembg`

## מה להגדיר אצלכם

- **ספריית חומרים** ב-`~/VideoAssets`: מוזיקה ב-`music/` ואפקטים ב-`סאונד/SFX/`. אם החומרים שלכם בתיקייה
  אחרת, תגידו ל-Claude איפה הם.
- **פונטים:** הכתוביות משתמשות בפונטים שמותקנים ב-CapCut. הפונט הבית `bamberger-grunge-bold-fm` לא כלול כאן,
  ואפשר להחליף אותו בכל פונט עברי. רשימת פונטים חינמיים שנבדקו נמצאת ב-`skills/hakapitan-captions/SKILL.md`.
- **הצעות מחיר:** כדי לשלוח בוואטסאפ צריך את מפתחות Green API של הבונקר (מאלון). שומרים אותם בקובץ
  `.env.local` בתוך `~/.claude/skills/bunker-price-proposal/`, בשורות `GREENAPI_INSTANCE_ID=…`,
  `GREENAPI_API_TOKEN=…` ו-`GREENAPI_API_URL=…`. הקובץ לא עולה לגיטהאב. בלי המפתחות אפשר עדיין להכין PDF
  ולשלוח אותו ידנית. בשביל ה-PDF צריך Google Chrome מותקן.
- **כללי הבית** (`references/house-rules.md` בכל סקיל) הם הטעם של הבונקר: קצב, צבעים, גודל כתוביות. אפשר
  לשנות אותם.

## כללי בטיחות שחשוב להכיר

- **לא כותבים לפרויקט שפתוח ב-CapCut.** סוגרים את הפרויקט (חוזרים למסך הבית של CapCut) לפני ש-Claude כותב אליו.
- לפני כל שינוי Claude שומר גיבוי של הפרויקט בתיקייה שלו.
- התמלול רץ מקומית על המחשב, ושום חומר לא עולה לענן.

---
נבנה בבונקר, אולפן הפודקאסטים של אלון גבאי. שמות הלקוחות שבדוגמאות הוחלפו בכינויים (לקוח A, אורח B…).
הפונטים בתיקייה `fonts/` מופצים לפי רישיון SIL Open Font License.
