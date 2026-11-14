"""Timeline audio extraction + Hebrew transcription (ivrit.ai) + caption chunking."""
import subprocess
from pathlib import Path

import numpy as np

import paths

SAMPLE_RATE = 16000
FFMPEG = str(paths.FFMPEG)
MODEL_DIR = str(paths.MODEL_DIR)

_model = None


def _atempo_chain(speed: float) -> str:
    """ffmpeg atempo accepts 0.5-2.0; chain filters for values outside."""
    parts = []
    remaining = speed
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    parts.append(f"atempo={remaining:.6f}")
    return ",".join(parts)


def build_timeline_audio(plan: list[dict], total_duration_us: int,
                         progress=None, sample_rate: int = SAMPLE_RATE,
                         channels: int = 1, apply_volume: bool = False
                         ) -> tuple[np.ndarray, list[str]]:
    """Decode each timeline segment and place it at its target position.

    Defaults reproduce the transcription mix (mono 16kHz, raw levels — best for
    Whisper). The preview mix passes stereo/44.1k + apply_volume so the user
    hears the episode the way CapCut plays it.

    Returns (float32 array matching the CapCut timeline, warnings). Shape is
    (N,) for mono or (N, channels) for stereo.
    """
    total_samples = int(total_duration_us / 1e6 * sample_rate) + sample_rate
    shape = (total_samples,) if channels == 1 else (total_samples, channels)
    audio = np.zeros(shape, dtype=np.float32)
    warnings = []
    for i, seg in enumerate(plan):
        if progress:
            progress(i, len(plan))
        src = Path(seg["path"])
        if not src.exists():
            warnings.append(f"קובץ מקור חסר, מדלג: {src.name}")
            continue
        cmd = [FFMPEG, "-v", "error",
               "-ss", f"{seg['source_start_us'] / 1e6:.6f}",
               "-t", f"{seg['source_duration_us'] / 1e6:.6f}",
               "-i", str(src), "-vn", "-ac", str(channels), "-ar", str(sample_rate)]
        if abs(seg.get("speed", 1.0) - 1.0) > 1e-3:
            cmd += ["-af", _atempo_chain(seg["speed"])]
        cmd += ["-f", "f32le", "-"]
        out = subprocess.run(cmd, capture_output=True)
        if out.returncode != 0 or not out.stdout:
            warnings.append(f"חילוץ אודיו נכשל: {src.name}")
            continue
        chunk = np.frombuffer(out.stdout, dtype=np.float32)
        if channels > 1:
            chunk = chunk.reshape(-1, channels)
        if apply_volume:
            vol = seg.get("volume", 1.0)
            if abs(vol - 1.0) > 1e-3:
                chunk = chunk * vol
        start = int(seg["target_start_us"] / 1e6 * sample_rate)
        end = min(start + len(chunk), total_samples)
        audio[start:end] += chunk[:end - start]  # overlapping layers mix
    np.clip(audio, -1.0, 1.0, out=audio)
    return audio, warnings


def encode_audio(audio: np.ndarray, out_path: Path, sample_rate: int = SAMPLE_RATE,
                 channels: int = 1, bitrate: str = "56k") -> None:
    """Compress the timeline audio to m4a so the editor can play it back."""
    out_path.parent.mkdir(exist_ok=True)
    subprocess.run(
        [FFMPEG, "-v", "error", "-y", "-f", "f32le", "-ar", str(sample_rate),
         "-ac", str(channels), "-i", "pipe:", "-c:a", "aac", "-b:a", bitrate,
         str(out_path)],
        input=audio.tobytes(), capture_output=True, check=True)


def ensure_model(progress=None) -> None:
    """Download the Hebrew model once, on first use. It's ~1.6GB from
    HuggingFace's free CDN into the writable data dir; every launch after finds
    it locally and returns instantly. `progress(fraction)` drives the UI bar.

    Downloaded to a temp dir and moved into place atomically, so a download that
    dies halfway never leaves a half-model that looks 'ready' but is corrupt."""
    if paths.model_ready():
        return

    from huggingface_hub import hf_hub_download

    paths.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    staging = paths.MODEL_DIR.with_name(paths.MODEL_DIR.name + ".part")
    if staging.exists():
        import shutil
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)

    files = paths.MODEL_FILES
    for i, fname in enumerate(files):
        if progress:
            progress(i / len(files))
        hf_hub_download(repo_id=paths.MODEL_REPO, filename=fname,
                        local_dir=str(staging))
    if progress:
        progress(0.99)

    # atomic swap — only now does model_ready() flip to True
    staging.rename(paths.MODEL_DIR)


def load_model():
    global _model
    if _model is None:
        ensure_model()
        from faster_whisper import WhisperModel
        _model = WhisperModel(MODEL_DIR, device="cpu", compute_type="int8",
                              cpu_threads=8)
    return _model


def transcribe(audio: np.ndarray, progress=None) -> list[dict]:
    """Word-level Hebrew transcription. Returns [{text, start_s, end_s}]."""
    model = load_model()
    total_s = len(audio) / SAMPLE_RATE
    segments, _info = model.transcribe(
        audio, language="he", word_timestamps=True,
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 300},
    )
    words = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append({"text": text, "start_s": w.start, "end_s": w.end})
        if progress and total_s:
            progress(min(seg.end / total_s, 1.0))
    return words


PUNCT_BREAK = (".", "!", "?", ",", ":", ";")


def chunk_captions(words: list[dict], max_words: int = 3,
                   max_duration_s: float = 3.0, max_gap_s: float = 0.6,
                   strip_punctuation: bool = True) -> list[dict]:
    """Group words into short reel-style captions.

    Returns [{text, start_us, duration_us, words:[{text,start_ms,end_ms}]}].
    """
    captions = []
    current = []

    def flush():
        if not current:
            return
        start = current[0]["start_s"]
        end = current[-1]["end_s"]
        texts = [w["text"] for w in current]
        if strip_punctuation and texts:
            texts[-1] = texts[-1].rstrip(".,;:")
        captions.append({
            "text": " ".join(texts),
            "start_us": int(start * 1e6),
            "duration_us": max(int((end - start) * 1e6), 200_000),
            "words": [{
                "text": w["text"],
                "start_ms": int((w["start_s"] - start) * 1000),
                "end_ms": int((w["end_s"] - start) * 1000),
            } for w in current],
        })
        current.clear()

    for w in words:
        if current:
            gap = w["start_s"] - current[-1]["end_s"]
            duration = w["end_s"] - current[0]["start_s"]
            if (len(current) >= max_words or gap > max_gap_s
                    or duration > max_duration_s
                    or current[-1]["text"].endswith(PUNCT_BREAK)):
                flush()
        current.append(w)
    flush()

    # gap-free rule: each caption holds until the next begins (also kills overlap)
    for i in range(len(captions) - 1):
        captions[i]["duration_us"] = captions[i + 1]["start_us"] - captions[i]["start_us"]
    return captions
