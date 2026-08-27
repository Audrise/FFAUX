"""
# Reads metadata from a single file using ffprobe in a separate thread.

Keeps the UI responsive when adding multiple files by running metadata
probing off the GUI thread.

Uses the same QRunnable + QObject pattern as core/ffmpeg_worker.py,
since QRunnable can't emit signals directly. This is one of the few
core/ modules that imports PySide6.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from core.metadata_service import MetadataService
from core.models.audio_file import AudioFile

class WorkerSignals(QObject):
    # target_id is the placeholder AudioFile ID in MainWindow._audio_files / TrackTable,
    # not probed_audio_file.id, since the probed file is a separate AudioFile.
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