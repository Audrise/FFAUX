"""
# Audio conversion configuration model

Kept separate from core.models.job.Job so it can be edited as a single
unit through the ConversionSettingsDialog. When a batch job is created,
the settings are converted into the Job.params dictionary via
to_job_params().

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
    # WAV is left out intentionally since its codec depends on the bit depth
}

_PCM_CODEC_BY_BIT_DEPTH = {16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_s32le"}

# 24-bit depth is stored in a 32-bit container
_SAMPLE_FMT_BY_BIT_DEPTH = {16: "s16", 24: "s32", 32: "s32"}

# Standard sampling rates
STANDARD_SAMPLE_RATES = [44100, 48000, 88200, 96000, 176400, 192000]

@dataclass
class ConversionSettings:
    output_format: OutputFormat = OutputFormat.MP3
    sample_rate_hz: int = 44100
    bit_depth: int = 16
    bitrate_kbps: int = 320
    use_soxr: bool = True  # Only takes effect for FLAC/WAV
    soxr_precision: int = 28  # 1-33
    flac_compression_level: int = 5  # 0-12
    custom_output_suffix: str = ""
    custom_output_dir: str = ""  # use default folder (config output_directory / source folder)

    def is_lossless(self) -> bool:
        return self.output_format in LOSSLESS_FORMATS

    def uses_soxr(self) -> bool:
        return self.output_format in SOXR_FORMATS and self.use_soxr

    def codec_name(self) -> str:
        if self.output_format == OutputFormat.WAV:
            return _PCM_CODEC_BY_BIT_DEPTH.get(self.bit_depth, "pcm_s16le")
        return _CODEC_BY_FORMAT[self.output_format]

    def sample_fmt(self) -> str:
        return _SAMPLE_FMT_BY_BIT_DEPTH.get(self.bit_depth, "s16")

    def file_extension(self) -> str:
        if self.output_format == OutputFormat.AAC:
            return ".m4a"
        if self.output_format == OutputFormat.ALAC:
            return ".m4a"
        return f".{self.output_format.value}"

    def to_job_params(self) -> dict:
        # Convert to a dict so Job.params can be used by _build_convert()
        params: dict = {
            "codec": self.codec_name(),
            "sample_rate_hz": self.sample_rate_hz,
        }

        if self.output_format in SOXR_FORMATS:
            params["preserve_streams"] = True
            params["sample_fmt"] = self.sample_fmt()
            if self.use_soxr:
                params["use_soxr"] = True
                params["soxr_precision"] = self.soxr_precision

        if self.output_format == OutputFormat.FLAC:
            params["flac_compression_level"] = self.flac_compression_level
            params["preserve_cover_art"] = True

        if self.output_format == OutputFormat.ALAC:
            params["audio_only"] = True
            params["preserve_cover_art"] = True

        elif self.output_format in LOSSY_FORMATS:
            params["bitrate_kbps"] = self.bitrate_kbps

            if self.output_format == OutputFormat.MP3:
                params["audio_only"] = True
                params["preserve_cover_art"] = True

            if self.output_format == OutputFormat.AAC:
                params["preserve_streams"] = True
                params["preserve_cover_art"] = True

            if self.output_format == OutputFormat.OPUS:
                params["preserve_cover_art"] = True

            if self.output_format == OutputFormat.OGG:
                params["audio_only"] = True
                params["preserve_metadata_args"] = True

        return params