"""
# Data model for a single unit of work (Job) run by FFmpeg
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

from core.models.audio_file import AudioFile

class OperationType(str, Enum):
    # To add a new operation, add an entry here and a builder
    # function in ffmpeg/command_builder.py
    CONVERT = "convert"
    APPLY_METADATA = "apply_metadata"
    REMOVE_COVER = "remove_cover"
    EXTRACT_COVER = "extract_cover"
    SET_COVER = "set_cover"
    NORMALIZE = "normalize"
    TRIM = "trim"
    GENERATE_SPECTROGRAM = "generate_spectrogram"

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Job:
    audio_file: AudioFile
    operation: OperationType
    params: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    output_path: Optional[str] = None