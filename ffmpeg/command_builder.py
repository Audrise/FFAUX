"""
# Constructing the FFmpeg CLI argument string from a Job.

Each operation has its own builder function. `build()` acts as a dispatcher
(Strategy pattern), ensuring that adding a new operation does not require
modifying existing code. All functions here are pure/deterministic,
making them easy to test without any mocks.
"""
from __future__ import annotations

from typing import Callable

from core.models.job import Job, OperationType

def _build_convert(job: Job) -> list[str]:
    params = job.params
    args = ["-y", "-i", job.audio_file.path]

    if params.get("preserve_streams"):
        # -map 0 -map_metadata 0 -c:v copy: include all streams (including
        # cover art as a video stream) + metadata from the source without re-encoding the video/cover.
        args += ["-map", "0", "-map_metadata", "0", "-c:v", "copy"]

    if params.get("use_soxr"):
        # SOXR resampler (higher quality than the default FFmpeg/swresample resampler). Forced "FLAC/WAV only"
        af = "aresample=resampler=soxr"
        precision = params.get("soxr_precision")
        if precision is not None:
            af += f":precision={precision}"
        args += ["-af", af]

    sample_fmt = params.get("sample_fmt")  # exm. "s16", "s32"
    if sample_fmt:
        args += ["-sample_fmt", sample_fmt]

    sample_rate = params.get("sample_rate_hz") or params.get("sample_rate")  # exm. 44100
    if sample_rate:
        args += ["-ar", str(sample_rate)]

    bitrate_kbps = params.get("bitrate_kbps")
    if bitrate_kbps is not None:
        args += ["-b:a", f"{bitrate_kbps}k"]
    elif params.get("bitrate"):
        args += ["-b:a", params["bitrate"]]

    channels = params.get("channels")  # exm. 2
    if channels:
        args += ["-ac", str(channels)]

    codec = params.get("codec")  # exm. "libmp3lame"
    if codec:
        args += ["-c:a", codec]

    compression_level = params.get("flac_compression_level")
    if compression_level is not None:
        args += ["-compression_level", str(compression_level)]

    args += [job.output_path]
    return args

def _metadata_args(job: Job) -> list[str]:
    # Build metadata args from the current in-memory metadata, including cleared keys.
    # Shared by metadata and cover-art updates to keep tags consistent and up to date.
    args: list[str] = []
    metadata = job.audio_file.metadata.to_dict()
    for key, value in metadata.items():
        if key == "cover_art_path":
            continue
        args += ["-metadata", f"{key}={value}"]

    for key in job.params.get("deleted_metadata_keys", []):
        args += ["-metadata", f"{key}="]

    return args

def _build_apply_metadata(job: Job) -> list[str]:
    args = ["-y", "-i", job.audio_file.path, "-c", "copy"]
    args += _metadata_args(job)
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
    # BUGFIX: previously this only used `-map_metadata 0`, which copies
    # tags from whatever is currently on disk in the source file.
    cover_path = job.params["cover_path"]
    args = [
        "-y",
        "-i", job.audio_file.path,
        "-i", cover_path,
        "-map", "0:a",
        "-map", "1",
        "-c:a", "copy",
        "-c:v:0", "mjpeg",
    ]
    args += _metadata_args(job)
    args += [
        "-disposition:v:0", "attached_pic",
        job.output_path,
    ]
    return args

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

def _build_spectrogram(job: Job) -> list[str]:
    # showspectrumpic reads the whole file from start to end (same as a
    # normal convert), so the existing -progress pipe:1 mechanism in
    # ffmpeg_worker.py produces a real 0-100% progress reading for this
    # too, with no special-casing needed.
    resolution = job.params.get("resolution", "1920x1080")
    args = [
        "-y", "-i", job.audio_file.path,
        "-lavfi", f"showspectrumpic=s={resolution}:legend=1",
        job.output_path,
    ]
    return args

_BUILDERS: dict[OperationType, Callable[[Job], list[str]]] = {
    OperationType.CONVERT: _build_convert,
    OperationType.APPLY_METADATA: _build_apply_metadata,
    OperationType.EXTRACT_COVER: _build_extract_cover,
    OperationType.SET_COVER: _build_set_cover,
    OperationType.NORMALIZE: _build_normalize,
    OperationType.TRIM: _build_trim,
    OperationType.GENERATE_SPECTROGRAM: _build_spectrogram,
}

def build(job: Job) -> list[str]:
    # Build FFmpeg CLI arguments (without 'ffmpeg' in front) for a Job.
    # Raises:
    #     ValueError: if the operation does not have a registered builder,
    #     or job.output_path is not set.

    if not job.output_path and job.operation != OperationType.EXTRACT_COVER:
        raise ValueError("job.output_path must be set before the build command!")

    builder = _BUILDERS.get(job.operation)
    if builder is None:
        raise ValueError(f"Operatioin not supported: {job.operation}")
    return builder(job)

def register_operation(operation: OperationType, builder: Callable[[Job], list[str]]) -> None:
    # Register a custom builder for a new operation (extensibility hook).
    _BUILDERS[operation] = builder