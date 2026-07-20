"""Model data untuk satu unit pekerjaan (Job) yang dieksekusi FFmpeg."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from core.models.audio_file import AudioFile


class OperationType(str, Enum):
    """Jenis operasi yang didukung.

    Menambah operasi baru = menambah entri di sini + satu builder function
    di ffmpeg/command_builder.py. Tidak perlu mengubah JobManager atau
    FFmpegWorker sama sekali (lihat prinsip Strategy pattern pada rancangan).
    """

    CONVERT = "convert"
    APPLY_METADATA = "apply_metadata"
    EXTRACT_COVER = "extract_cover"
    SET_COVER = "set_cover"
    NORMALIZE = "normalize"
    TRIM = "trim"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Satu unit pekerjaan: satu operasi FFmpeg untuk satu AudioFile."""

    audio_file: AudioFile
    operation: OperationType
    params: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    output_path: Optional[str] = None
