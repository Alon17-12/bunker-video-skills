#!/usr/bin/env python3
"""Send a proposal PDF + a short text to a client on WhatsApp (Bunker number, Green API).

    python send_whatsapp.py --phone 0501234567 --pdf "<file>.pdf" --text-file msg.txt --dry-run
    python send_whatsapp.py --phone 0501234567 --pdf "<file>.pdf" --text-file msg.txt
    python send_whatsapp.py --phone 0501234567 --status <idMessage>

ONLY send after the person you work for (Alon / Dolev) approved the exact text
in chat. The text goes out as the PDF's caption, one message.

Credentials: GREENAPI_INSTANCE_ID, GREENAPI_API_TOKEN, GREENAPI_API_URL
(optional GREENAPI_MEDIA_URL) from the environment, or from the repo's
.env.local (found by walking up from this script — e.g. one inside the skill folder). Never printed.
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import uuid
from pathlib import Path

KEYS = ("GREENAPI_INSTANCE_ID", "GREENAPI_API_TOKEN", "GREENAPI_API_URL", "GREENAPI_MEDIA_URL")


def load_env() -> dict:
    env = {k: os.environ[k] for k in KEYS if os.environ.get(k)}
    for parent in Path(__file__).resolve().parents:
        f = parent / ".env.local"
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    if k in KEYS and k not in env:
                        env[k] = v.strip().strip('"').strip("'")
            break
    missing = [k for k in KEYS[:2] if not env.get(k)]
    if missing:
        sys.exit(f"ERROR: missing {', '.join(missing)} (env or .env.local)")
    return env


def chat_id(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0"):
        digits = "972" + digits[1:]
    if not digits.startswith("972") or len(digits) != 12:
        sys.exit(f"ERROR: not an Israeli mobile number: {phone}")
    return f"{digits}@c.us"


def hosts(env: dict):
    api = (env.get("GREENAPI_API_URL") or "https://api.green-api.com").rstrip("/")
    # Replace only the FIRST "api." (the subdomain label): "7103.api.greenapi.com"
    # also contains "api." inside "greenapi.com".
    media = (env.get("GREENAPI_MEDIA_URL") or api.replace("api.", "media.", 1)).rstrip("/")
    return api, media


def send(env, chat, pdf: Path, text: str, file_name: str) -> str:
    _, media = hosts(env)
    b = "----" + uuid.uuid4().hex

    def part(name, val):
        return f'--{b}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{val}\r\n'.encode()

    body = part("chatId", chat) + part("fileName", file_name) + part("caption", text)
    body += (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
             f"Content-Type: application/pdf\r\n\r\n").encode() + pdf.read_bytes() + f"\r\n--{b}--\r\n".encode()
    url = f"{media}/waInstance{env['GREENAPI_INSTANCE_ID']}/sendFileByUpload/{env['GREENAPI_API_TOKEN']}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    r = json.load(urllib.request.urlopen(req, timeout=180))
    if not r.get("idMessage"):
        sys.exit(f"ERROR: Green API returned no idMessage: {r}")
    return r["idMessage"]


def status(env, chat, mid) -> dict:
    api, _ = hosts(env)
    url = f"{api}/waInstance{env['GREENAPI_INSTANCE_ID']}/getMessage/{env['GREENAPI_API_TOKEN']}"
    req = urllib.request.Request(url, data=json.dumps({"chatId": chat, "idMessage": mid}).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phone", required=True)
    ap.add_argument("--pdf")
    ap.add_argument("--text-file", help="UTF-8 file with the message text (the PDF caption)")
    ap.add_argument("--file-name", help="name the client sees; default: the PDF name without the client's name")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", metavar="ID_MESSAGE")
    a = ap.parse_args()
    env = load_env()
    chat = chat_id(a.phone)

    if a.status:
        r = status(env, chat, a.status)
        print(r.get("typeMessage"), r.get("statusMessage"))
        return

    if not (a.pdf and a.text_file):
        sys.exit("ERROR: --pdf and --text-file are required to send")
    pdf = Path(a.pdf).expanduser()
    text = Path(a.text_file).expanduser().read_text(encoding="utf-8").strip()
    # "הצעת מחיר - <client> - <title>.pdf" -> "הצעת מחיר - <title>.pdf"
    file_name = a.file_name or re.sub(r"^(הצעת מחיר) - [^-]+ - ", r"\1 - ", pdf.name)
    _, media = hosts(env)
    print(f"to: {chat}\nfile: {file_name} ({pdf.stat().st_size // 1024} KB)\nupload host: {media.split('//')[-1]}\n---\n{text}\n---")
    if a.dry_run:
        print("dry run: nothing sent")
        return
    mid = send(env, chat, pdf, text, file_name)
    print(f"sent, idMessage: {mid}")
    r = status(env, chat, mid)
    print("status:", r.get("typeMessage"), r.get("statusMessage"))


if __name__ == "__main__":
    main()
