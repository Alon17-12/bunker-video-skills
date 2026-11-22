#!/usr/bin/env python3
"""Build a Bunker price proposal (הצעת מחיר) from a JSON file.

    python build_proposal.py examples/course-day.json
    python build_proposal.py my.json --out-dir ~/Downloads --no-preview

Output (same base name, in --out-dir):
    <name>.html  self-contained (images embedded), open in a browser to tweak
    <name>.pdf   rendered by headless Chrome / Edge
    <name>-pages/page-N.png   page previews, only if PyMuPDF (fitz) is installed

Standard library only. Works on macOS and Windows (Chrome or Edge).
The JSON format is documented in ../SKILL.md and in ../examples/.
"""
import argparse
import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"
DEFAULT_VAT = 18

CSS = """
@page { size: A4; margin: 15mm 16mm 16mm; }
* { box-sizing: border-box; }
body { font-family: "Heebo", "Arial Hebrew", "Arial", sans-serif; direction: rtl; font-size: 11pt; line-height: 1.6; color: #1a1a2e; margin: 0; }
.num { direction: ltr; unicode-bidi: isolate; display: inline-block; }
header { border-bottom: 3px solid #1a1a2e; padding-bottom: 10px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: flex-end; }
header .brand { font-size: 20pt; font-weight: 900; letter-spacing: -0.5px; display:flex; align-items:center; gap:12px; }
header .brand small { display: block; font-size: 10pt; font-weight: 400; color: #555; }
header .logo { height: 64px; width: auto; }
header .date { color: #555; font-size: 10.5pt; text-align: left; }
h1 { font-size: 20pt; font-weight: 900; margin: 0 0 4px; }
h2 { font-size: 13.5pt; font-weight: 700; margin: 18px 0 6px; padding-inline-start: 10px; border-inline-start: 4px solid #e63946; }
h3 { font-size: 11.5pt; font-weight: 700; margin: 12px 0 2px; }
p { margin: 4px 0; }
ul, ol { margin: 2px 0 6px; padding-inline-start: 20px; }
li { margin: 1px 0; }
a { color: #e63946; }
.sub { color: #555; font-size: 11pt; }
.note { font-size: 10.5pt; color: #444; }
.caption { font-size:9.5pt; color:#666; margin:3px 0 0; }
.pb { page-break-before: always; margin-top: 0 !important; }
.avoid { page-break-inside: avoid; }
footer { margin-top: 16px; font-size: 9.5pt; color: #777; border-top: 1px solid #ddd; padding-top: 6px; }
.sets { display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin:8px 0 4px; }
.sets img { width:100%; height:170px; object-fit:cover; border-radius:10px; display:block; }
.team { display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin:8px 0; }
.team .p { display:flex; gap:12px; align-items:center; background:#f6f6f8; border-radius:10px; padding:10px; }
.team img { width:96px; height:120px; object-fit:cover; object-position: center 20%; border-radius:10px; flex:none; }
.team strong { font-size:12pt; }
.bottom { background:#1a1a2e; color:#fff; border-radius:10px; padding:12px 16px; margin:14px 0 0; display:flex; justify-content:space-between; align-items:center; gap:12px; }
.bottom .big { font-size:17pt; font-weight:900; }
.bottom .small { font-size:10pt; color:#c9cbe0; }
.callout { background:#f6f6f8; border-radius:10px; padding:10px 16px; margin:10px 0; border-inline-start:4px solid #e63946; }
.named { display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin:8px 0; }
.named img { width:100%; height:170px; object-fit:cover; border-radius:8px; display:block; }
.gallery { display:grid; grid-template-columns: repeat(3,1fr); gap:8px; margin:8px 0; }
.gallery img { width:100%; height:112px; object-fit:cover; border-radius:8px; display:block; }
.shots2 { display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin:8px 0; }
.shots2 img { width:100%; height:150px; object-fit:cover; border-radius:8px; display:block; }
.feature { display:grid; grid-template-columns: 270px 1fr; gap:16px; align-items:center; margin:8px 0; }
.feature img { width:100%; aspect-ratio:4/3; height:auto; object-fit:cover; border-radius:10px; display:block; }
.pgallery { display:grid; grid-template-columns: repeat(3,1fr); gap:8px; margin:8px 0; }
.pgallery img { width:100%; aspect-ratio:16/9; height:auto; object-fit:cover; border-radius:8px; display:block; }
.reels { display:grid; grid-template-columns: repeat(4,1fr); gap:8px; margin:8px 0; }
.reels img { width:100%; height:215px; object-fit:cover; border-radius:10px; display:block; }
table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 11pt; }
th, td { border: 1px solid #d8d8df; padding: 6px 10px; text-align: start; vertical-align: top; }
th { background: #1a1a2e; color: #fff; font-weight: 500; }
td.price { white-space: nowrap; width: 165px; }
tr.total td { font-weight: 700; background: #eef0f6; font-size: 12pt; }
tr.sec td { background:#f6f6f8; font-weight:700; }
.paybox { border:2px solid #1a1a2e; border-radius:10px; padding:10px 16px; margin:12px 0; }
.paybox li { margin:3px 0; }
"""

# Number runs (prices, dates, durations, 4K, 18%) get an LTR-isolated span so
# they never flip inside the Hebrew line. Applied to text only, never to tags.
NUM_RE = re.compile(r"(\d[\d,.:/]*(?:\s?₪)?%?(?:K\b)?)")
TAG_RE = re.compile(r"(<[^>]+>)")


def num(text: str) -> str:
    parts = TAG_RE.split(text)
    out = []
    for part in parts:
        if part.startswith("<"):
            out.append(part)
        else:
            out.append(NUM_RE.sub(r'<span class="num">\1</span>', part))
    return "".join(out)


def ils(n) -> str:
    n = round(float(n), 2)
    s = f"{n:,.2f}".rstrip("0").rstrip(".")
    return f"{s} ₪"


def img(rel: str) -> str:
    """Embed an image from the skill's assets/ (or an absolute path) as a data URI."""
    p = Path(rel).expanduser()
    if not p.is_absolute():
        p = ASSETS / rel
    if not p.exists():
        sys.exit(f"ERROR: image not found: {p}")
    mime = "image/png" if p.suffix.lower() == ".png" else "image/webp" if p.suffix.lower() == ".webp" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def bullets(items) -> str:
    return "<ul>" + "".join(f"<li>{num(x)}</li>" for x in items) + "</ul>"


def build_html(d: dict) -> str:
    vat = d.get("vat_percent", DEFAULT_VAT)
    client = d["client"]["name"]
    date = d["date"]
    title = d["title"]
    items = d["items"]
    total = sum(i["price"] for i in items if i.get("price") is not None and i.get("in_total", True) and not i.get("unit"))
    total_vat = total * (1 + vat / 100)
    methods = d.get("payment_methods", "העברה בנקאית · ביט · כרטיס אשראי (עד 3 תשלומים)")
    logo = d.get("logo", "brand/logo-bunker.png")
    o = []

    # ---------- page 1: hello, sets, team, bottom line ----------
    o.append(f'''<header><div class="brand"><img class="logo" src="{img(logo)}" alt=""><div>{html.escape(d.get("brand_title", "הבונקר – אולפן פודקאסט ותוכן"))}<small>בית גוברין 15, רמת השרון</small></div></div>
<div class="date">הצעת מחיר<br>{num(date)}</div></header>''')
    o.append(f"<h1>הצעת מחיר – {num(html.escape(title))}</h1>")
    o.append(f'<p class="sub">לכבוד: <strong>{html.escape(d["client"].get("display", client))}</strong></p>')
    o.append(f"<p>{html.escape(d.get('greeting', client + ' היקר,'))}</p>")
    o.append(f"<p>{num(d['intro'])}</p>")

    if d.get("show_sets", True):
        o.append('''<h2>שני סטים לבחירה</h2><div class="sets avoid">''')
        o.append(f'<div><img src="{img("sets/clinic.jpg")}" alt=""><p class="caption"><strong>קליניקה</strong> – שתי כורסאות לבנות ושולחן עגול. אווירה רכה ואישית.</p></div>')
        o.append(f'<div><img src="{img("sets/bar.jpg")}" alt=""><p class="caption"><strong>בר</strong> – שולחן עץ גבוה ושני כיסאות בר. מראה עכשווי ודינמי.</p></div></div>')

    if d.get("show_team", True):
        team = d.get("team", {})
        alon = team.get("alon", "מנהל הבונקר. ילווה את הפרויקט ויוודא שהתוצרים ייצאו ברמה הכי גבוהה.")
        dolev = team.get("dolev", "המארח של הבונקר. יקבל אותך ביום הצילום וידאג שתרגיש בבית מול המצלמה.")
        o.append('<h2>מי ילווה אותך</h2><div class="team avoid">')
        o.append(f'<div class="p"><img src="{img("team/alon.jpg")}" alt=""><div><strong>אלון גבאי</strong><br><span class="note">{html.escape(alon)}</span></div></div>')
        o.append(f'<div class="p"><img src="{img("team/dolev.jpg")}" alt=""><div><strong>דולב סלע</strong><br><span class="note">{html.escape(dolev)}</span></div></div></div>')

    if d.get("show_bottom_box", False):  # price only on the last page (Alon, 22.11.2026)
        o.append(f'''<div class="bottom avoid"><div><div class="small">בשורה התחתונה – {num(html.escape(d.get("bottom_label", title)))}</div><div class="big">{num(ils(total))} + מע״מ</div></div>
<div class="small" style="text-align:left">סה״כ כולל מע״מ: <strong style="color:#fff">{num(ils(total_vat))}</strong><br>{num(html.escape(methods.replace("כרטיס ", "")))}</div></div>''')

    # ---------- page 2: what's included ----------
    o.append('<h2 class="pb">מה כולל השירות</h2>')
    for block in d["includes"]:
        if block.get("callout"):
            o.append(f'<div class="callout avoid"><strong>{num(block["heading"])}</strong>{bullets(block["bullets"])}</div>')
        else:
            o.append(f'<h3>{num(block["heading"])}</h3>{bullets(block["bullets"])}')
    terms = d.get("terms", [])
    terms_page = d.get("terms_page", "includes")  # "includes" or "price"
    if terms and terms_page == "includes":
        o.append(f'<h2>תיאום ציפיות</h2>{bullets(terms)}')
    if d.get("gallery") == "reels":
        o.append('<h2>רילסים שערכנו בבונקר</h2><div class="reels avoid">' + "".join(f'<img src="{img(f"reels/reel-{i}.jpg")}" alt="">' for i in range(1, 5)) + "</div>")

    # ---------- optional photo sections under «מה כולל» ----------
    for sec in d.get("photo_sections", []):
        o.append('<div class="avoid">')
        if sec.get("heading"):
            o.append(f'<h2>{num(sec["heading"])}</h2>')
        if sec.get("feature"):
            f = sec["feature"]
            o.append(f'<div class="feature"><img src="{img(f["image"])}" alt=""><div>'
                     + (f'<h3>{num(f["title"])}</h3>' if f.get("title") else "")
                     + (bullets(f["bullets"]) if f.get("bullets") else "") + '</div></div>')
        if sec.get("images"):
            o.append('<div class="pgallery">' + "".join(f'<img src="{img(x)}" alt="">' for x in sec["images"]) + '</div>')
        if sec.get("caption"):
            o.append(f'<p class="caption">{num(sec["caption"])}</p>')
        o.append('</div>')

    # ---------- page 3 (courses only): course gallery ----------
    if d.get("gallery") == "courses":
        named = [("courses/course-1.jpg", "קורס דיגיטלי", "צולם בלוקיישן של הלקוחה"),
                 ("courses/course-2.jpg", "מועדון תוכן", "שיעורים קבועים למנויים"),
                 ("courses/course-3.jpg", "VSL ומסלול ליווי", "צולם בבונקר"),
                 ("courses/course-4.jpg", "קורס לחברה", "הדרכה פנימית לעובדים")]
        o.append('<h2 class="pb">קורסים שצילמנו</h2><div class="named avoid">')
        for f, name, what in named:
            o.append(f'<div><img src="{img(f)}" alt=""><p class="caption"><strong>{name}</strong> – {html.escape(what)}</p></div>')
        o.append('</div><div class="gallery avoid">' + "".join(f'<img src="{img(f"courses/more-{i}.jpg")}" alt="">' for i in range(1, 7)) + "</div>")
        o.append('<p class="caption">עוד מתוך קורסים דיגיטליים שהפקנו – בבונקר ובלוקיישנים של הלקוחות.</p>')
        o.append(f'''<div class="shots2 avoid"><div><a href="https://bunker.alon-gabay.co.il/course-production" style="text-decoration:none;color:inherit"><img src="{img("courses/bts.jpg")}" alt=""><p class="caption">מאחורי הקלעים בבונקר · לחצו לדף הפקת הקורסים שלנו</p></a></div>
<div><img src="{img("courses/devices.jpg")}" alt=""><p class="caption">התוצאה: קורס שנראה מקצועי על כל מסך</p></div></div>''')

    # ---------- last page: price table, payment, add-ons ----------
    o.append('<h2 class="pb">הצעת המחיר</h2><table class="avoid"><thead><tr><th>#</th><th>השירות</th><th>מחיר לפני מע״מ</th></tr></thead><tbody>')
    n = 0
    total_row_done = False
    # The total row goes right after the last counted item: before the first
    # per-unit option, or before the stage heading that introduces it.
    first_unit = next((i for i, it in enumerate(items) if it.get("unit")), None)
    total_at = first_unit
    if first_unit is not None and first_unit > 0 and "stage" in items[first_unit - 1]:
        total_at = first_unit - 1
    for idx, it in enumerate(items):
        if idx == total_at and not total_row_done:
            o.append(_total_row(total, total_vat, vat, d.get("total_label", "סה״כ")))
            total_row_done = True
        if "stage" in it:
            o.append(f'<tr class="sec"><td></td><td colspan="2">{num(it["stage"])}</td></tr>')
            continue
        if it.get("unit") and not total_row_done:
            o.append(_total_row(total, total_vat, vat, d.get("total_label", "סה״כ")))
            total_row_done = True
        if it.get("unit"):
            mark = "+"
            price = f'{num(ils(it["price"]))} + מע״מ<br>{html.escape(it["unit"])}'
        else:
            n += 1
            mark = f'<span class="num">{n}</span>'
            price = f'{num(ils(it["price"]))} + מע״מ'
        o.append(f'<tr><td>{mark}</td><td>{num(it["desc"])}</td><td class="price">{price}</td></tr>')
    if not total_row_done:
        o.append(_total_row(total, total_vat, vat, d.get("total_label", "סה״כ")))
    o.append("</tbody></table>")
    if d.get("price_note"):
        o.append(f'<p class="note">{num(d["price_note"])}</p>')

    pay = d.get("payment_steps") or ["התשלום מראש שומר את מועד הצילום ביומן."]
    if len(pay) == 1:
        steps = f"<p>{num(pay[0])}</p>"
    else:
        steps = "<ol>" + "".join(f"<li>{num(s)}</li>" for s in pay) + "</ol>"
    o.append(f'<div class="paybox avoid"><strong>אופן התשלום</strong>{steps}<p class="note" style="margin-top:6px">אמצעי תשלום: {num(html.escape(methods))}.</p></div>')

    if terms and terms_page == "price":
        o.append(f'<h2>תיאום ציפיות</h2>{bullets(terms)}')
    if d.get("addons"):
        o.append(f'<h2>אפשר להוסיף בנפרד</h2>{bullets(d["addons"])}')
    if d.get("closing"):
        o.append(f'<p style="margin-top:10px">{num(d["closing"])}</p>')
    o.append(f'<p style="margin-top:10px"><strong>תוקף ההצעה: עד {num(d["valid_until"])}.</strong></p>')
    o.append(f'<p style="margin-top:8px">בברכה, <strong>{html.escape(d.get("signature", "אלון גבאי ודולב סלע"))}</strong> · הבונקר</p>')
    o.append(f'<footer>הצעת מחיר – {num(html.escape(title))} | {html.escape(client)} | הופק בתאריך {num(date)}</footer>')

    return f'''<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<title>הצעת מחיר - {html.escape(client)} - {html.escape(title)}</title>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;700;900&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
{chr(10).join(o)}
</body></html>'''


def _total_row(total, total_vat, vat, label):
    return (f'<tr class="total"><td></td><td>{html.escape(label)}<br><span class="note" style="font-weight:400">'
            f'כולל מע״מ ({num(str(vat) + "%")}): {num(ils(total_vat))}</span></td>'
            f'<td class="price">{num(ils(total))} + מע״מ</td></tr>')


def find_chrome():
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    for path in [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]:
        if os.path.exists(path):
            return path
    return None


def render_pdf(html_text: str, pdf_path: Path):
    chrome = find_chrome()
    if not chrome:
        sys.exit("ERROR: Chrome / Edge not found. Install Google Chrome.")
    # Render from a temp copy: Chrome can be blocked from reading Downloads/Desktop.
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "proposal.html"
        out = Path(tmp) / "proposal.pdf"
        src.write_text(html_text, encoding="utf-8")
        cmd = [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
               "--virtual-time-budget=6000", f"--print-to-pdf={out}", src.as_uri()]
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if not out.exists() or out.stat().st_size == 0:
            sys.exit("ERROR: Chrome did not produce a PDF.")
        shutil.copyfile(out, pdf_path)


def previews(pdf_path: Path) -> int:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("(no page previews: pip install pymupdf to get them)")
        return -1
    doc = fitz.open(str(pdf_path))
    d = pdf_path.with_name(pdf_path.stem + "-pages")
    d.mkdir(exist_ok=True)
    for i, page in enumerate(doc, 1):
        page.get_pixmap(dpi=80).save(str(d / f"page-{i}.png"))
    print(f"previews: {d}")
    return len(doc)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json")
    ap.add_argument("--out-dir", default=str(Path.home() / "Downloads"))
    ap.add_argument("--no-preview", action="store_true")
    a = ap.parse_args()
    d = json.loads(Path(a.json).expanduser().read_text(encoding="utf-8"))
    out_dir = Path(a.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[\\/:*?"<>|]', "-", f'הצעת מחיר - {d["client"]["name"]} - {d["title"]}')
    html_text = build_html(d)
    html_path = out_dir / f"{safe}.html"
    pdf_path = out_dir / f"{safe}.pdf"
    html_path.write_text(html_text, encoding="utf-8")
    render_pdf(html_text, pdf_path)
    print(f"html: {html_path}\npdf:  {pdf_path}")
    if not a.no_preview:
        pages = previews(pdf_path)
        if pages > 0:
            print(f"pages: {pages}")


if __name__ == "__main__":
    main()
