"""
# File-related helpers for extension validation, collecting files from drag & drop.
"""
from __future__ import annotations

from pathlib import Path

SUPPORTED_AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma", ".opus", ".alac",
}

def is_supported_audio(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS

def format_bit_depth(bits: int | None) -> str:
    if not bits or bits <= 0:
        return "-"
    return f"{bits} Bits"

def format_sample_rate(hz: int | None) -> str:
    if not hz or hz <= 0:
        return "-"
    return f"{hz} Hz"

def format_bitrate(kbps: int | None) -> str:
    if not kbps or kbps <= 0:
        return "-"
    return f"{kbps} Kbps"

def format_duration(seconds: float | None) -> str:
    if not seconds or seconds < 0:
        return "-"
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

def format_file_size(num_bytes: int | None) -> str:
    if not num_bytes or num_bytes < 0:
        return "-"
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def collect_audio_files(paths: list[str], recursive: bool = True) -> list[str]:
    # Accept file and folder paths from drag-and-drop, then return a sorted,
    # duplicate-free list of supported audio files.
    found: set[str] = set()

    for raw_path in paths:
        p = Path(raw_path)
        if p.is_file() and is_supported_audio(p):
            found.add(str(p.resolve()))
        elif p.is_dir():
            pattern = "**/*" if recursive else "*"
            for child in p.glob(pattern):
                if child.is_file() and is_supported_audio(child):
                    found.add(str(child.resolve()))

    return sorted(found)
