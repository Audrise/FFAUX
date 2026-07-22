"""
# JobManager: the sole GUI entry point for running batch jobs.

The GUI NEVER calls subprocesses or FFmpeg directly—it always goes
through JobManager.enqueue(). This allows the backend to be fully tested
independently of the GUI and ensures the GUI does not need to know
anything about FFmpeg commands.

Signals emitted (see also the signal contract table in the design):
    jobAdded(job_id)
    jobStarted(job_id)
    jobProgress(job_id, percent)
    jobLog(job_id, line)
    jobFinished(job_id, success, message)
    batchFinished()
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QThreadPool, Signal

from core.models.job import Job
from core.ffmpeg_worker import FFmpegWorker
from ffmpeg.ffmpeg_runner import FFmpegRunner

class JobManager(QObject):
    jobAdded = Signal(str)
    jobStarted = Signal(str)
    jobProgress = Signal(str, float)
    jobLog = Signal(str, str)
    jobFinished = Signal(str, bool, str)
    batchFinished = Signal()

    def __init__(self, ffmpeg_path: str = "ffmpeg", max_parallel_jobs: int = 2, parent=None):
        super().__init__(parent)
        self._ffmpeg_runner = FFmpegRunner(ffmpeg_path)
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(max(1, max_parallel_jobs))

        self._jobs: dict[str, Job] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._active_count = 0
        self._total_count = 0

    def set_ffmpeg_path(self, path: str) -> None:
        self._ffmpeg_runner = FFmpegRunner(path)

    def set_max_parallel_jobs(self, count: int) -> None:
        self._pool.setMaxThreadCount(max(1, count))

    def enqueue(self, job: Job) -> None:
        self._jobs[job.id] = job
        cancel_event = threading.Event()
        self._cancel_events[job.id] = cancel_event

        worker = FFmpegWorker(job, self._ffmpeg_runner, cancel_event)
        worker.signals.started.connect(self.jobStarted)
        worker.signals.progress.connect(self.jobProgress)
        worker.signals.log.connect(self.jobLog)
        worker.signals.finished.connect(self._on_job_finished)

        self._total_count += 1
        self._active_count += 1
        self.jobAdded.emit(job.id)
        self._pool.start(worker)

    def enqueue_many(self, jobs: list[Job]) -> None:
        for job in jobs:
            self.enqueue(job)

    def cancel(self, job_id: str) -> None:
        event = self._cancel_events.get(job_id)
        if event:
            event.set()

    def cancel_all(self) -> None:
        for event in self._cancel_events.values():
            event.set()

    def _on_job_finished(self, job_id: str, success: bool, message: str) -> None:
        self.jobFinished.emit(job_id, success, message)
        self._active_count -= 1
        if self._active_count <= 0:
            self._active_count = 0
            self._total_count = 0
            self.batchFinished.emit()

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def wait_for_done(self, timeout_ms: int = -1) -> bool:
        # Block until all jobs are complete; for testing/CLI scripts.
        return self._pool.waitForDone(timeout_ms)
