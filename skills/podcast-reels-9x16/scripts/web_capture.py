"""Bring REAL material into a draft folder: a page screenshot, an element screenshot, or an image URL —
with a provenance record, so every insert can be traced to where it came from.

    python web_capture.py "<draft>" page   https://example.com/article  --slug ynet-article [--selector "article"] [--width 1440] [--full]
    python web_capture.py "<draft>" image  https://example.com/logo.svg --slug whiteboard-logo
    python web_capture.py "<draft>" --list

Writes  <draft>/ccstudio-web-<slug>.png  and appends to  <draft>/ccstudio-web-sources.json
({slug, kind, url, title, captured_at, w, h}). SVG logos are rasterised at 2× through Chromium.
Then `register_media.py` puts the file in the Media panel and the build frames it (`framed_asset`).

What this does NOT do: decide what is true. The caller verifies that the page is the real article and
the logo the real logo (title + domain are printed for that reason), and prefers the primary source —
the company's own site, the publisher's own page — over aggregators and image search.
"""
import argparse, datetime, json, os, re, sys, time, urllib.request
from pathlib import Path
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def record(folder, entry):
    p = folder / "ccstudio-web-sources.json"
    src = json.load(open(p)) if p.exists() else []
    src = [s for s in src if s.get("slug") != entry["slug"]] + [entry]
    tmp = p.with_suffix(".json.tmp"); tmp.write_text(json.dumps(src, ensure_ascii=False, indent=1)); tmp.replace(p)


def capture_page(folder, url, slug, selector=None, width=1440, full=False, wait_ms=2500):
    from playwright.sync_api import sync_playwright
    out = folder / f"ccstudio-web-{slug}.png"
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": width, "height": int(width * 9 / 16)}, device_scale_factor=2, user_agent=UA, locale="he-IL")
        pg.goto(url, wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(wait_ms)
        for sel in ("button:has-text('קבל')", "button:has-text('Accept')", "button:has-text('אישור')", "[aria-label*=close i]"):   # cookie/consent banners
            try: pg.locator(sel).first.click(timeout=800)
            except Exception: pass
        title = pg.title()
        if selector: pg.locator(selector).first.screenshot(path=str(out))
        else: pg.screenshot(path=str(out), full_page=full)
        b.close()
    from PIL import Image; w, h = Image.open(out).size
    record(folder, {"slug": slug, "kind": "page", "url": url, "title": title, "selector": selector, "captured_at": datetime.datetime.now().isoformat(timespec="seconds"), "w": w, "h": h})
    print(f"{out.name}  {w}x{h}  «{title}»  {url}"); return out


def capture_image(folder, url, slug):
    out = folder / f"ccstudio-web-{slug}.png"
    req = urllib.request.Request(url, headers={"User-Agent": UA}); data = urllib.request.urlopen(req, timeout=60).read()
    if url.lower().split("?")[0].endswith(".svg") or data[:200].lstrip().startswith(b"<svg") or b"<svg" in data[:400]:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:                                                 # rasterise the SVG at 2× on a transparent page
            b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1600, "height": 800}, device_scale_factor=2)
            pg.set_content(f"<html><body style='margin:0;background:transparent'><img id=i src='data:image/svg+xml;base64,{__import__('base64').b64encode(data).decode()}' style='max-width:1600px;max-height:800px'></body></html>")
            pg.wait_for_timeout(500); pg.locator("#i").screenshot(path=str(out), omit_background=True); b.close()
    else:
        from PIL import Image; import io
        Image.open(io.BytesIO(data)).convert("RGBA").save(out)
    from PIL import Image; w, h = Image.open(out).size
    record(folder, {"slug": slug, "kind": "image", "url": url, "captured_at": datetime.datetime.now().isoformat(timespec="seconds"), "w": w, "h": h})
    print(f"{out.name}  {w}x{h}  {url}"); return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("draft"); ap.add_argument("kind", nargs="?", choices=["page", "image"]); ap.add_argument("url", nargs="?")
    ap.add_argument("--slug"); ap.add_argument("--selector"); ap.add_argument("--width", type=int, default=1440); ap.add_argument("--full", action="store_true"); ap.add_argument("--list", action="store_true")
    ap.add_argument("--out", help="write here instead of the draft folder (tests, research before a project exists)")
    a = ap.parse_args(); folder = Path(a.out) if a.out else capcut.DRAFTS_DIR / a.draft
    if a.out: folder.mkdir(parents=True, exist_ok=True)
    if not folder.is_dir(): sys.exit(f"no such draft: {folder}")
    if a.list:
        p = folder / "ccstudio-web-sources.json"
        for s in (json.load(open(p)) if p.exists() else []): print(f"  {s['slug']:24} {s['kind']:5} {s.get('w')}x{s.get('h')}  {s.get('title') or ''}  {s['url']}")
        return
    if not (a.kind and a.url and a.slug): sys.exit("need: kind url --slug")
    if not re.fullmatch(r"[a-z0-9\-]+", a.slug): sys.exit("slug: lowercase ascii and dashes only (file names travel through zsh and CapCut)")
    (capture_page if a.kind == "page" else capture_image)(folder, a.url, a.slug, **({"selector": a.selector, "width": a.width, "full": a.full} if a.kind == "page" else {}))


if __name__ == "__main__":
    main()
