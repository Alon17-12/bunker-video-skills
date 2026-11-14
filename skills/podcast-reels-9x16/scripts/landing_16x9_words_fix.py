"""Apply the QA word fixes (two decodes + reading for context) and print indexed words."""
import json, os, re
SP = os.path.expanduser(os.environ.get("WORK", "~/Movies/reel-captions-work/landing-16x9"))
W = json.load(open(f"{SP}/0919_words.json"))
# phrase replacements: (video, old phrase, new phrase) — old matched on punctuation-stripped tokens, all occurrences
FIX = [
 (0, "וויידבורד", "WhiteBoard"), (0, "Whiteboard Education", "WhiteBoard Education"), (0, "Whiteboard", "WhiteBoard"), (0, "ל -Wideboard", "ל-WhiteBoard"),
 (0, "הכוחות", "הלקוחות"), (0, "X", "איקס"), (0, "השונת", "משנת"), (0, "חוסרים", "חוסכים"), (0, "במכירות", "ומכירות"), (0, "בשדרוג במערכת", "בשדרוג למערכת"),
 (0, "הפונטלית", "הפרונטלית"), (0, "ותשלום, סדרת וסרטונים", "ותשלום, סדרת סרטונים"), (0, "דיבור אלקטרוני", "דיוור אלקטרוני"), (0, "האחוז הקרוב", "האחוז הקבוע"),
 (0, "ל -2026", "ל-2026"), (0, "10 %", "10%"), (0, "40 %", "40%"), (0, "1 ,600", "1,600"), (0, "הכול", "הכל"), (0, "ווין ווין", "win win"),
 (1, "כל התאריך שאתנו עובד", "כל התהליך איתנו עובד"), (1, "שהראיתם", "שראיתם"), (1, "שמנה יוצאים מפרק", "שממנה יוצא פרק"), (1, "ניתון מצלמות", "ניתוב מצלמות"),
 (1, "רעיון וחצי איתי", "ראיון איתי"), (1, "הקלינק", "הלינק"), (1, "לסך של", "למסך של"), (1, "הכישורים", "האישורים"), (1, "VSO 'ים", "VSL-ים"),
 (1, "עושה של היכרות", "סשן היכרות"), (1, "תראיינו", "תתאמו"), (1, "ידולב", "דולב"), (1, "אולי זה יעני", "אולי זה אני"), (1, "אחד אחרי מהצוות", "אחד אחר מהצוות"),
 (1, "אקבל אתכם", "יקבל אתכם"), (1, "שתאורה", "של תאורה"), (1, "שבולכם", "שמולכם"), (1, "הגיעו אליכם", "יגיעו אליכם"), (1, "לנצור", "ליצור"), (1, "רידס", "רילס"),
 (1, "עריכת מתקדמת", "עריכה מתקדמת"), (1, "מי שככה רוצה לא", "מי שרוצה, לא"), (1, "חדרים שותנים", "חדרים שנותנים"), (1, "לבתים הקטנים", "לפרטים הקטנים"),
 (1, "יודעים לי", "תאמינו לי"), (1, "ונדאג את", "ומדייק את"), (1, "אמרנו בפרומפטר", "אמרנו, פרומפטר"), (1, "הנה, שיש קליק, תתערבו בנו", "ואם יש קליק, תתאהבו בנו"),
 (1, "באות הפודעה", "באותה הודעה"), (1, "שהיה לנו המון", "שיהיה לנו המון"), (1, "ה -15", "ה-15"), (1, "החבר 'ה", "החבר׳ה"),
]
def core(t): return t.strip(".,?!:;")
def apply(words, old, new):
    ot = old.split(); n = len(ot); out = []; i = 0; hits = 0
    while i < len(words):
        seq = words[i:i+n]
        if len(seq) == n and all(core(w["text"]) == core(o) for w, o in zip(seq, ot)) and all(w["text"].startswith(core(o)) for w, o in zip(seq, ot)):
            tail = seq[-1]["text"][len(core(ot[-1])):]           # trailing punctuation of the last old token
            nt = new.split(); t0, t1 = seq[0]["start_s"], seq[-1]["end_s"]; step = (t1 - t0) / len(nt)
            for k, tok in enumerate(nt):
                out.append({"text": tok + (tail if k == len(nt)-1 else ""), "start_s": t0 + k*step, "end_s": t0 + (k+1)*step})
            i += n; hits += 1
        else:
            out.append(dict(words[i])); i += 1
    return out, hits
for vi, v in enumerate(W["videos"]):
    ws = v["words"]
    for fv, old, new in FIX:
        if fv != vi: continue
        ws, h = apply(ws, old, new)
        if h == 0: print(f"  !! no hit video {vi+1}: {old!r}")
    v["words"] = ws
json.dump(W, open(f"{SP}/0919_words_fixed.json", "w"), ensure_ascii=False, indent=0)
for vi, v in enumerate(W["videos"]):
    print(f"=== VIDEO {vi+1}")
    line = []; t0 = v["words"][0]["start_s"]; i0 = 0
    for i, w in enumerate(v["words"]):
        line.append(w["text"])
        if w["text"][-1:] in ".?!":
            print(f"[{t0:6.1f} #{i0}-{i}] " + " ".join(line)); line = []; i0 = i+1; t0 = v["words"][i+1]["start_s"] if i+1 < len(v["words"]) else 0
    if line: print(f"[{t0:6.1f} #{i0}-{i}] " + " ".join(line))
    lat = [(i, w["text"]) for i, w in enumerate(v["words"]) if re.search(r"[A-Za-z]", w["text"])]; print("latin:", lat)
