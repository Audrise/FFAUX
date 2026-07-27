"""
# A worker that executes a single FFmpeg job in a separate thread.

This is the ONLY place (along with job_manager.py) within core/ allowed
to import PySide6. All heavy logic (building commands, running subprocesses,
parsing progress) remains delegated to pure-Python modules in ffmpeg/ and
core/; this worker merely bridges callbacks to Qt signals.

Pattern used: QRunnable + a separate QObject for signals, because
QRunnable itself is not a QObject and cannot emit signals directly.
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from core.models.job import Job, JobStatus
from ffmpeg.command_builder import build as build_command
from ffmpeg.ffmpeg_runner import FFmpegRunner
from ffmpeg.progress_parser import ProgressParser

class WorkerSignals(QObject):
    started = Signal(str)                    # job_id
    progress = Signal(str, float)             # job_id, percent (0-100)
    log = Signal(str, str)                    # job_id, line
    finished = Signal(str, bool, str)         # job_id, success, message

class FFmpegWorker(QRunnable):
    def __init__(
        self,
        job: Job,
        ffmpeg_runner: FFmpegRunner,
        cancel_event: threading.Event | None = None,
    ):
        super().__init__()
        self.job = job
        self._ffmpeg_runner = ffmpeg_runner
        self._cancel_event = cancel_event or threading.Event()
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    def cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        job = self.job
        job.status = JobStatus.RUNNING
        job.audio_file.mark_running()
        self.signals.started.emit(job.id)

        try:
            args = build_command(job)
        except ValueError as exc:
            self._finish(success=False, message=str(exc))
            return

        parser = ProgressParser(total_duration_seconds=job.audio_file.duration_seconds)

        def on_line(line: str) -> None:
            self.signals.log.emit(job.id, line)
            state = parser.feed_line(line)
            if state is not None:
                percent = parser.percent(state)
                if percent is not None:
                    self.signals.progress.emit(job.id, percent)

        result = self._ffmpeg_runner.run(
            args,
            on_line=on_line,
            cancel_event=self._cancel_event,
            extra_args=["-nostdin", "-progress", "pipe:1", "-nostats"],
        )

        if result.cancelled:
            job.status = JobStatus.CANCELLED
            job.audio_file.status = job.audio_file.status  # tidak diubah paksa
            self._finish(success=False, message="Cancelled by the user", cancelled=True)
        elif result.success:
            self._finish(success=True, message="Success")
        else:
            self._finish(success=False, message=result.error_message or "FFmpeg Failed!")

    def _finish(self, success: bool, message: str, cancelled: bool = False) -> None:
        job = self.job
        if cancelled:
            job.status = JobStatus.CANCELLED
        elif success:
            job.status = JobStatus.DONE
            job.audio_file.mark_done(job.output_path)
        else:
            job.status = JobStatus.FAILED
            job.audio_file.mark_failed(message)

        self.signals.finished.emit(job.id, success, message)
