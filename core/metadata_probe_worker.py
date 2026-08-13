"""
# A worker that reads (ffprobe) metadata for a single file in a separate thread.

Prevents UI freezing when adding many files: metadata probing now runs off
the GUI thread instead of synchronously per file.

Same pattern as core/ffmpeg_worker.py: QRunnable + QObject for signals,
since QRunnable cannot emit signals directly. One of the few core/ modules
intentionally allowed to import PySide6.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from core.metadata_service import MetadataService
from core.models.audio_file import AudioFile

class WorkerSignals(QObject):
    # target_id = placeholder AudioFile ID in MainWindow._audio_files / TrackTable,
    # not probed_audio_file.id (the probed object is a separate AudioFile).
    finished = Signal(object, str)

class MetadataProbeWorker(QRunnable):
    def __init__(self, audio_file_id: str, path: str, metadata_service: MetadataService):
        super().__init__()
        self.audio_file_id = audio_file_id
        self._path = path
        self._metadata_service = metadata_service
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        audio_file = AudioFile(path=self._path)
        self._metadata_service.read_metadata(audio_file)
        self.signals.finished.emit(audio_file, self.audio_file_id)