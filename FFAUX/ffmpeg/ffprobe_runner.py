"""
# A pure subprocess wrapper for ffprobe (reads audio file info & metadata).
"""
from __future__ import annotations

import sys
import json
import subprocess

from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class ProbeResult:
    success: bool
    raw: dict[str, Any]
    error_message: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        fmt = self.raw.get("format", {})
        duration = fmt.get("duration")
        try:
            return float(duration) if duration is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def tags(self) -> dict[str, str]:
        return self.raw.get("format", {}).get("tags", {}) or {}

    @property
    def bit_rate_kbps(self) -> Optional[int]:
        bit_rate = self.raw.get("format", {}).get("bit_rate")
        try:
            return int(bit_rate) // 1000 if bit_rate is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def size_bytes(self) -> Optional[int]:
        size = self.raw.get("format", {}).get("size")
        try:
            return int(size) if size is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def audio_codec_name(self) -> Optional[str]:
        for stream in self.raw.get("streams", []):
            if stream.get("codec_type") == "audio":
                return stream.get("codec_name")
        return None

    @property
    def cover_art_stream(self) -> Optional[dict[str, Any]]:
        streams = self.raw.get("streams", [])

        # Prefer the stream explicitly marked as attached picture.
        for stream in streams:
            if (
                stream.get("codec_type") == "video"
                and stream.get("disposition", {}).get("attached_pic")
            ):
                return stream

        # Fallback for containers that do not expose attached_pic.
        for stream in streams:
            if stream.get("codec_type") == "video":
                return stream

        return None

    @property
    def cover_art_stream_index(self) -> Optional[int]:
        stream = self.cover_art_stream
        if stream is None:
            return None

        try:
            return int(stream["index"])
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def cover_art_extension(self) -> Optional[str]:
        stream = self.cover_art_stream
        if stream is None:
            return None

        extensions = {
            "mjpeg": ".jpg",
            "png": ".png",
            "webp": ".webp",
            "bmp": ".bmp",
            "gif": ".gif",
            "tiff": ".tiff",
            "jpeg2000": ".jp2",
            "jpegls": ".jls",
            "ljpeg": ".jpg",
        }

        return extensions.get(stream.get("codec_name"))

    @property
    def sample_rate_hz(self) -> Optional[int]:
        for stream in self.raw.get("streams", []):
            if stream.get("codec_type") == "audio":
                sample_rate = stream.get("sample_rate")
                try:
                    return int(sample_rate) if sample_rate is not None else None
                except (TypeError, ValueError):
                    return None
        return None

    @property
    def bit_depth(self) -> Optional[int]:
        for stream in self.raw.get("streams", []):
            if stream.get("codec_type") == "audio":
                bits = stream.get("bits_per_raw_sample")

                try:
                    return int(bits) if bits is not None else None
                except (TypeError, ValueError):
                    return None

        return None

    @property
    def has_cover_art(self) -> bool:
        return self.cover_art_stream is not None

class FFprobeRunner:
    def __init__(self, ffprobe_path: str = "ffprobe"):
        self.ffprobe_path = ffprobe_path

    def probe(self, file_path: str) -> ProbeResult:
        args = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
                creationflags=_windows_no_console_flag(),
            )
        except FileNotFoundError as exc:
            return ProbeResult(success=False, raw={}, error_message=str(exc))
        except subprocess.TimeoutExpired:
            return ProbeResult(success=False, raw={}, error_message="ffprobe timeout")

        if completed.returncode != 0:
            return ProbeResult(success=False, raw={}, error_message=completed.stderr.strip())

        try:
            raw = json.loads(completed.stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            return ProbeResult(success=False, raw={}, error_message=f"Invalid ffprobe output: {exc}")

        return ProbeResult(success=True, raw=raw)

def _windows_no_console_flag() -> int:
    # Prevent a black console window from flashing on Windows every time
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
