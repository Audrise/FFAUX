"""
# Audio conversion configuration model

Separated from `core.models.job.Job` to allow editing via a GUI dialog
as a single unit (`ConversionSettingsDialog`), then converted into the
`Job.params` dictionary when the batch job is actually created
(see `to_job_params()`).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

class OutputFormat(str, Enum):
    MP3 = "mp3"
    AAC = "aac"
    FLAC = "flac"
    WAV = "wav"
    OGG = "ogg"
    OPUS = "opus"
    ALAC = "alac"

LOSSLESS_FORMATS = {OutputFormat.FLAC, OutputFormat.WAV, OutputFormat.ALAC}
LOSSY_FORMATS = {OutputFormat.MP3, OutputFormat.AAC, OutputFormat.OGG, OutputFormat.OPUS}
SOXR_FORMATS = {OutputFormat.FLAC, OutputFormat.WAV}

_CODEC_BY_FORMAT = {
    OutputFormat.MP3: "libmp3lame",
    OutputFormat.AAC: "aac",
    OutputFormat.FLAC: "flac",
    OutputFormat.OGG: "libvorbis",
    OutputFormat.OPUS: "libopus",
    OutputFormat.ALAC: "alac",
    # WAV is intentionally not here because its codec is determined by bit depth.
}

_PCM_CODEC_BY_BIT_DEPTH = {16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_s32le"}

# 24-bit sample_fmt—it is stored in a 32-bit container).
_SAMPLE_FMT_BY_BIT_DEPTH = {16: "s16", 24: "s32", 32: "s32"}

# Standard sample rate valid in audio engineering. Intentionally limited.
STANDARD_SAMPLE_RATES = [44100, 48000, 88200, 96000, 176400, 192000]

@dataclass
class ConversionSettings:
    output_format: OutputFormat = OutputFormat.MP3
    sample_rate_hz: int = 44100
    bit_depth: int = 16
    bitrate_kbps: int = 320
    soxr_precision: int = 28  # 1-33
    flac_compression_level: int = 5  # 0-12
    custom_output_dir: str = ""  # use default folder (config output_directory / source folder)

    def is_lossless(self) -> bool:
        return self.output_format in LOSSLESS_FORMATS

    def uses_soxr(self) -> bool:
        return self.output_format in SOXR_FORMATS

    def codec_name(self) -> str:
        if self.output_format == OutputFormat.WAV:
            return _PCM_CODEC_BY_BIT_DEPTH.get(self.bit_depth, "pcm_s16le")
        return _CODEC_BY_FORMAT[self.output_format]

    def sample_fmt(self) -> str:
        return _SAMPLE_FMT_BY_BIT_DEPTH.get(self.bit_depth, "s16")

    def file_extension(self) -> str:
        return f".{self.output_format.value}"

    def to_job_params(self) -> dict:
        # Convert to a dict for Job.params, consumed by ffmpeg.command_builder._build_convert().
        params: dict = {
            "codec": self.codec_name(),
            "sample_rate_hz": self.sample_rate_hz,
        }

        if self.output_format in SOXR_FORMATS:
            params["preserve_streams"] = True
            params["use_soxr"] = True
            params["soxr_precision"] = self.soxr_precision
            params["sample_fmt"] = self.sample_fmt()
            if self.output_format == OutputFormat.FLAC:
                params["flac_compression_level"] = self.flac_compression_level
        elif self.output_format in LOSSY_FORMATS:
            params["bitrate_kbps"] = self.bitrate_kbps

        return params
