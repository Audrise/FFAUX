"""Model data untuk file audio dalam batch."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from core.models.metadata import Metadata


class FileStatus(str, Enum):
    """Status satu file audio dalam antrian batch."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AudioFile:
    """Representasi satu file audio dalam batch, beserta status pemrosesannya."""

    path: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Metadata = field(default_factory=Metadata)
    status: FileStatus = FileStatus.PENDING
    progress: float = 0.0
    duration_seconds: Optional[float] = None
    bitrate_kbps: Optional[int] = None
    codec: Optional[str] = None
    sample_rate_hz: Optional[int] = None
    file_size_bytes: Optional[int] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def filename(self) -> str:
        return Path(self.path).name

    @property
    def stem(self) -> str:
        return Path(self.path).stem

    @property
    def suffix(self) -> str:
        return Path(self.path).suffix.lower()

    def mark_running(self) -> None:
        self.status = FileStatus.RUNNING
        self.error_message = None

    def mark_done(self, output_path: Optional[str] = None) -> None:
        self.status = FileStatus.DONE
        self.progress = 100.0
        if output_path:
            self.output_path = output_path

    def mark_failed(self, message: str) -> None:
        self.status = FileStatus.FAILED
        self.error_message = message
