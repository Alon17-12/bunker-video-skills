"""Single source of truth for where things live — the one file that knows the
difference between "shipped, read-only" and "the user's, writable".

This split is invisible in development (everything sits in the project dir) but
load-bearing once frozen into a .app:

  * RESOURCE_DIR — inside the app bundle. Read-only, especially after Apple
    notarization. The model, ffmpeg, and the web UI live here.

  * DATA_DIR — ~/Library/Application Support/hakapitan. Writable. The user's
    config (their styles/presets), their login session, and the usage ledger
    live here. Writing any of these into the bundle would fail on a real
    install — which is exactly the bug the /tmp test caught.

Everything else imports its paths from here so the split is defined once.
"""
import shutil
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)


def _resource_base() -> Path:
    if FROZEN:
        return Path(sys._MEIPASS)              # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent   # dev: project root


RESOURCE_DIR = _resource_base()
APP_DIR = RESOURCE_DIR / "app"                 # web UI is served from app/static
FFMPEG = RESOURCE_DIR / "bin" / "ffmpeg"

# The Hebrew model is the heavy part (1.6GB). It is NOT bundled — that would make
# the installer 1.6GB. Instead it downloads once from HuggingFace's free CDN into
# the writable data dir on first transcription, and lives there forever after.
MODEL_REPO = "ivrit-ai/whisper-large-v3-turbo-ct2"
MODEL_FILES = ["model.bin", "config.json", "tokenizer.json",
               "vocabulary.json", "preprocessor_config.json"]


def _data_base() -> Path:
    if FROZEN:
        d = Path.home() / "Library" / "Application Support" / "hakapitan"
    else:
        d = Path(__file__).resolve().parent.parent   # dev: project root, unchanged
    d.mkdir(parents=True, exist_ok=True)
    return d


DATA_DIR = _data_base()
CONFIG_PATH = DATA_DIR / "config.json"
SESSION_PATH = DATA_DIR / "session.json"
LEDGER_PATH = DATA_DIR / "usage_ledger.jsonl"
AUDIO_DIR = DATA_DIR / "jobs_audio"
# the user's sound toolbox (music + SFX) lives in Supabase Storage (per-user,
# RLS). This is only the local working cache of files already downloaded, so
# injection into a CapCut draft is instant after the first fetch.
ASSETS_CACHE = DATA_DIR / "assets_cache"

# Writable model home. In dev this resolves to the existing project models/ dir,
# so a developer who already has the model keeps using it and nothing re-downloads.
MODELS_DIR = DATA_DIR / "models"
MODEL_DIR = MODELS_DIR / "ivrit-whisper-large-v3-turbo-ct2"


def model_ready() -> bool:
    return (MODEL_DIR / "model.bin").exists()


def ensure_config() -> None:
    """First launch of the installed app has no user config yet — seed it from
    the read-only default shipped in the bundle (which carries the Supabase/proxy
    URLs). In dev the two paths are the same file, so this is a no-op."""
    if CONFIG_PATH.exists():
        return
    bundled = RESOURCE_DIR / "config.json"
    if bundled.exists() and bundled.resolve() != CONFIG_PATH.resolve():
        shutil.copy(bundled, CONFIG_PATH)
    else:
        CONFIG_PATH.write_text('{"styles": [], "color_presets": [], "show_presets": []}')
