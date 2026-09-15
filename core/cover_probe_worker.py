"""
# Extracts embedded cover art from a single file in a separate thread.

Cover extraction spawns an ffmpeg process, so running it on the GUI
thread would freeze the UI when adding many files -- same reason
metadata probing is off-thread (see core/metadata_probe_worker.py).

Uses the same QRunnable + QObject pattern as core/ffmpeg_worker.py,
since QRunnable can't emit signals directly.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from core.metadata_service import MetadataService
from core.models.audio_file import AudioFile

class WorkerSignals(QObject):
    finished = Signal(str, str)

class CoverProbeWorker(QRunnable):
    def __init__(self, audio_file_id: str, audio_file: AudioFile, metadata_service: MetadataService, output_dir: str | Path):
        super().__init__()
        self.audio_file_id = audio_file_id
        self._audio_file = audio_file
        self._metadata_service = metadata_service
        self._output_dir = str(Path(output_dir) / audio_file_id)
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        cover_path = self._metadata_service.extract_cover_art_sync(
            self._audio_file, self._output_dir
        )
        self.signals.finished.emit(cover_path or "", self.audio_file_id)