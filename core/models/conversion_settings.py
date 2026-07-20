"""Model pengaturan konversi audio: format output, sample rate, bit depth,
bitrate, resampler SOXR, compression level (khusus FLAC), dan custom
output folder.

Dipisah dari core.models.job.Job supaya bisa diedit lewat dialog GUI
sebagai satu kesatuan (ConversionSettingsDialog), lalu dikonversi ke
Job.params dict saat batch job benar-benar dibuat (lihat to_job_params()).

Aturan bisnis penting (sesuai spesifikasi eksplisit dari user):
- SOXR + precision + sample_fmt + "-map 0 -map_metadata 0 -c:v copy"
  HANYA berlaku untuk output FLAC dan WAV -- bukan opsi yang bisa dipilih
  untuk format lain sama sekali (bukan cuma di-nonaktifkan, tapi memang
  tidak relevan/tidak ditawarkan).
- Bitrate HANYA relevan untuk format selain FLAC/WAV, karena bitrate FLAC
  bersifat variable (VBR-like, tergantung compression_level), bukan
  static seperti MP3/AAC/OGG/Opus.
- Compression level (0-12) cuma ada di FLAC (WAV tidak punya opsi ini di
  FFmpeg).
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


# Format yang tidak pakai Bitrate kbps sama sekali (pakai Bit Depth alih-alih).
LOSSLESS_FORMATS = {OutputFormat.FLAC, OutputFormat.WAV, OutputFormat.ALAC}

# Format yang pakai Bitrate kbps (static, mis. 192/256/320).
LOSSY_FORMATS = {OutputFormat.MP3, OutputFormat.AAC, OutputFormat.OGG, OutputFormat.OPUS}

# HANYA dua format ini yang pakai resampler SOXR + -sample_fmt +
# -map 0 -map_metadata 0 -c:v copy, sesuai spesifikasi command FFmpeg
# yang diberikan eksplisit oleh user untuk FLAC dan WAV.
SOXR_FORMATS = {OutputFormat.FLAC, OutputFormat.WAV}

_CODEC_BY_FORMAT = {
    OutputFormat.MP3: "libmp3lame",
    OutputFormat.AAC: "aac",
    OutputFormat.FLAC: "flac",
    OutputFormat.OGG: "libvorbis",
    OutputFormat.OPUS: "libopus",
    OutputFormat.ALAC: "alac",
    # WAV sengaja tidak ada di sini -- codec-nya ditentukan oleh bit depth,
    # lihat codec_name() di bawah (pcm_s16le / pcm_s24le / pcm_s32le).
}

_PCM_CODEC_BY_BIT_DEPTH = {16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_s32le"}

# Mapping bit depth -> nilai "-sample_fmt" FFmpeg. FLAC secara teknis cuma
# punya representasi internal 16-bit (s16) atau sampai 32-bit container
# (s32, dipakai juga untuk audio 24-bit karena FLAC tidak punya sample_fmt
# 24-bit "murni" -- disimpan di container 32-bit).
_SAMPLE_FMT_BY_BIT_DEPTH = {16: "s16", 24: "s32", 32: "s32"}

# Sample rate standar yang valid secara audio engineering. Sengaja dibatasi
# ke daftar ini (bukan rentang bebas 44100-192000) karena sample rate
# non-standar tidak bermakna untuk kebanyakan hardware/software playback.
STANDARD_SAMPLE_RATES = [44100, 48000, 88200, 96000, 176400, 192000]


@dataclass
class ConversionSettings:
    output_format: OutputFormat = OutputFormat.MP3
    sample_rate_hz: int = 44100
    bit_depth: int = 16
    bitrate_kbps: int = 192
    soxr_precision: int = 20  # 1-33, opsi "precision" resampler SOXR di FFmpeg
    flac_compression_level: int = 5  # 0-12, opsi -compression_level FFmpeg untuk flac
    custom_output_dir: str = ""  # kosong = pakai folder default (config output_directory / folder sumber)

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
        """Ubah jadi dict untuk Job.params, dikonsumsi oleh
        ffmpeg.command_builder._build_convert().
        """
        params: dict = {
            "codec": self.codec_name(),
            "sample_rate_hz": self.sample_rate_hz,
        }

        if self.output_format in SOXR_FORMATS:
            # FLAC & WAV: -map 0 -map_metadata 0 -c:v copy -af
            # aresample=resampler=soxr:precision=X -sample_fmt Y -- SELALU
            # aktif, bukan pilihan (sesuai command FFmpeg yang diberikan).
            params["preserve_streams"] = True
            params["use_soxr"] = True
            params["soxr_precision"] = self.soxr_precision
            params["sample_fmt"] = self.sample_fmt()
            if self.output_format == OutputFormat.FLAC:
                params["flac_compression_level"] = self.flac_compression_level
        elif self.output_format in LOSSY_FORMATS:
            params["bitrate_kbps"] = self.bitrate_kbps
        # ALAC: lossless tapi bukan FLAC/WAV -- di luar cakupan spesifikasi
        # SOXR yang diberikan, jadi encode biasa tanpa SOXR/bitrate/sample_fmt.

        return params
