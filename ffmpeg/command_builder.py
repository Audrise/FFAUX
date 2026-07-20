"""Membangun argumen CLI FFmpeg dari sebuah Job.

Setiap operasi punya fungsi builder sendiri. `build()` adalah dispatcher
(Strategy pattern) sehingga menambah operasi baru tidak mengubah kode lama.
Semua fungsi di sini pure/deterministic -> mudah diuji tanpa mock apa pun.
"""
from __future__ import annotations

from typing import Any, Callable

from core.models.job import Job, OperationType


def _build_convert(job: Job) -> list[str]:
    params = job.params
    args = ["-y", "-i", job.audio_file.path]

    if params.get("preserve_streams"):
        # -map 0 -map_metadata 0 -c:v copy: bawa semua stream (termasuk
        # cover art sebagai video stream) + metadata dari source apa
        # adanya, tanpa re-encode video/cover. Cuma dipakai untuk FLAC &
        # WAV sesuai spesifikasi command FFmpeg yang diberikan.
        args += ["-map", "0", "-map_metadata", "0", "-c:v", "copy"]

    # Resampler SOXR (kualitas lebih tinggi dari resampler default FFmpeg/
    # swresample). Pemaksaan "hanya untuk FLAC/WAV" terjadi di layer model
    # (ConversionSettings.to_job_params, lewat SOXR_FORMATS), bukan di
    # sini, supaya command_builder tetap murni "terjemahkan dict jadi
    # argumen CLI" tanpa aturan bisnis format tertentu.
    if params.get("use_soxr"):
        af = "aresample=resampler=soxr"
        precision = params.get("soxr_precision")
        if precision is not None:
            af += f":precision={precision}"
        args += ["-af", af]

    sample_fmt = params.get("sample_fmt")  # mis. "s16", "s32"
    if sample_fmt:
        args += ["-sample_fmt", sample_fmt]

    sample_rate = params.get("sample_rate_hz") or params.get("sample_rate")  # mis. 44100
    if sample_rate:
        args += ["-ar", str(sample_rate)]

    # Bitrate: dukung dua bentuk -- key baru "bitrate_kbps" (int, dari
    # ConversionSettings) dan key lama "bitrate" (string mis. "192k",
    # dipakai alur lama sebelum dialog konversi ini ada). Tidak pernah ada
    # untuk FLAC/WAV karena ConversionSettings tidak menyertakannya untuk
    # kedua format itu (bitrate FLAC bersifat variable, bukan static).
    bitrate_kbps = params.get("bitrate_kbps")
    if bitrate_kbps is not None:
        args += ["-b:a", f"{bitrate_kbps}k"]
    elif params.get("bitrate"):
        args += ["-b:a", params["bitrate"]]

    channels = params.get("channels")  # mis. 2
    if channels:
        args += ["-ac", str(channels)]

    codec = params.get("codec")  # mis. "libmp3lame"
    if codec:
        args += ["-c:a", codec]

    compression_level = params.get("flac_compression_level")
    if compression_level is not None:
        args += ["-compression_level", str(compression_level)]

    args += [job.output_path]
    return args


def _build_apply_metadata(job: Job) -> list[str]:
    args = ["-y", "-i", job.audio_file.path, "-c", "copy"]
    metadata = job.audio_file.metadata.to_dict()
    for key, value in metadata.items():
        if key == "cover_art_path":
            continue
        args += ["-metadata", f"{key}={value}"]

    # Tag yang dihapus user lewat "Hapus Metadata" (lihat
    # gui/widgets/metadata_editor.py) -- FFmpeg menghapus tag dengan cara
    # men-set nilainya jadi kosong. Ditaruh SETELAH loop di atas supaya
    # kalau key yang sama sempat keluar dari .to_dict() (mis. belum
    # ke-update di objek in-memory), baris "-metadata key=" ini yang
    # menang (FFmpeg pakai definisi -metadata TERAKHIR untuk key yang sama).
    for key in job.params.get("deleted_metadata_keys", []):
        args += ["-metadata", f"{key}="]

    args += [job.output_path]
    return args


def _build_extract_cover(job: Job) -> list[str]:
    return [
        "-y",
        "-i", job.audio_file.path,
        "-an",
        "-vcodec", "copy",
        job.output_path,
    ]


def _build_set_cover(job: Job) -> list[str]:
    cover_path = job.params["cover_path"]
    return [
        "-y",
        "-i", job.audio_file.path,
        "-i", cover_path,
        "-map", "0:a",
        "-map", "1:v",
        "-c", "copy",
        "-id3v2_version", "3",
        "-metadata:s:v", "title=Album cover",
        "-metadata:s:v", "comment=Cover (front)",
        job.output_path,
    ]


def _build_normalize(job: Job) -> list[str]:
    target_lufs = job.params.get("target_lufs", -14)
    args = [
        "-y", "-i", job.audio_file.path,
        "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
        job.output_path,
    ]
    return args


def _build_trim(job: Job) -> list[str]:
    start = job.params.get("start", "00:00:00")
    end = job.params.get("end")
    args = ["-y", "-i", job.audio_file.path, "-ss", str(start)]
    if end:
        args += ["-to", str(end)]
    args += ["-c", "copy", job.output_path]
    return args


_BUILDERS: dict[OperationType, Callable[[Job], list[str]]] = {
    OperationType.CONVERT: _build_convert,
    OperationType.APPLY_METADATA: _build_apply_metadata,
    OperationType.EXTRACT_COVER: _build_extract_cover,
    OperationType.SET_COVER: _build_set_cover,
    OperationType.NORMALIZE: _build_normalize,
    OperationType.TRIM: _build_trim,
}


def build(job: Job) -> list[str]:
    """Bangun argumen CLI FFmpeg (tanpa 'ffmpeg' di depan) untuk sebuah Job.

    Raises:
        ValueError: jika operasi belum punya builder terdaftar,
            atau job.output_path belum diset.
    """
    if not job.output_path and job.operation != OperationType.EXTRACT_COVER:
        raise ValueError("job.output_path harus diset sebelum build command")

    builder = _BUILDERS.get(job.operation)
    if builder is None:
        raise ValueError(f"Operasi belum didukung: {job.operation}")
    return builder(job)


def register_operation(operation: OperationType, builder: Callable[[Job], list[str]]) -> None:
    """Daftarkan builder kustom untuk operasi baru (extensibility hook)."""
    _BUILDERS[operation] = builder
