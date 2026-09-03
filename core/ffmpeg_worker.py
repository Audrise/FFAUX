"""
# Runs a single FFmpeg job in a separate thread

This is one of the only places in core/ that imports PySide6.
Heavy logic stays in the pure-Python ffmpeg/ and core/ modules.
This worker just connects callbacks to Qt signals.

Uses QRunnable with a separate QObject for signals since QRunnable
can't emit signals directly
"""
from __future__ import annotations

import os
import shutil
import threading

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from core.models.job import Job, JobStatus
from ffmpeg.command_builder import build as build_command
from ffmpeg.ffmpeg_runner import FFmpegRunner
from ffmpeg.progress_parser import ProgressParser

class WorkerSignals(QObject):
    started = Signal(str)                     # job_id
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
        """print("SOURCE DURATION:", job.audio_file.duration_seconds)"""

        def on_line(line: str) -> None:
            self.signals.log.emit(job.id, line)
            """print("FFMPEG LINE:", repr(line))"""

            state = parser.feed_line(line)

            if state is not None:
                percent = parser.percent(state)

                """print(
                    "PARSED:",
                    state.out_time_seconds,
                    percent,
                    state.is_done,
                )"""

                if percent is not None:
                    self.signals.progress.emit(job.id, percent)

        result = self._ffmpeg_runner.run(
            args,
            on_line=on_line,
            cancel_event=self._cancel_event,
            extra_args=["-nostdin", "-progress", "pipe:1", "-nostats"],
        )

        if result.cancelled:
            self._cleanup_temporary_output()
            job.status = JobStatus.CANCELLED
            job.audio_file.status = job.audio_file.status
            self._finish(success=False, message="Cancelled by the user", cancelled=True)

        elif result.success:
            if not self._preserve_cover_art():
                self._cleanup_temporary_output()
                self._finish(
                    success=False,
                    message="Failed to preserve cover art",
                )
                return

            if job.params.get("overwrite_source"):
                source_path = Path(job.params.get("source_path", job.audio_file.path))
                temporary_path = Path(job.output_path)

                try:
                    os.replace(temporary_path, source_path)
                except OSError as exc:
                    self._cleanup_temporary_output()
                    self._finish(
                        success=False,
                        message=f"Failed to overwrite original file: {exc}",
                    )
                    return

                job.output_path = str(source_path)

            self._finish(success=True, message="Success")

        else:
            self._cleanup_temporary_output()
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

    def _cleanup_temporary_output(self) -> None:
        if not self.job.params.get("overwrite_source"):
            return

        temporary_path = Path(self.job.output_path)

        try:
            if temporary_path.exists():
                temporary_path.unlink()

        except OSError:
            pass

    def _preserve_cover_art(self) -> bool:
        job = self.job

        if not job.params.get("preserve_cover_art"):
            return True

        source_path = Path(
            job.params.get("source_path", job.audio_file.path)
        )
        output_path = Path(job.output_path)

        cover_path = output_path.with_suffix(".cover.jpg")

        extract_args = [
            "-y",
            "-i", str(source_path),
            "-map", "0:v:0",
            "-c", "copy",
            "-f", "image2",
            str(cover_path),
        ]

        extract_result = self._ffmpeg_runner.run(
            extract_args,
            cancel_event=self._cancel_event,
            extra_args=["-nostdin"],
        )

        """print("COVER EXTRACT CMD:", extract_args)
        print("COVER EXTRACT SUCCESS:", extract_result.success)
        print("COVER EXTRACT ERROR:", extract_result.error_message)
        print("COVER PATH:", cover_path)
        print("COVER EXISTS:", cover_path.exists())"""

        if not extract_result.success:
            return False

        if output_path.suffix.lower() == ".m4a":
            temp_path = output_path.with_suffix(".cover_tmp.m4a")
        elif output_path.suffix.lower() == ".mp3":
            temp_path = output_path.with_suffix(".cover_tmp.mp3")
        elif output_path.suffix.lower() == ".opus":
            temp_path = output_path.with_suffix(".cover_tmp.opus")
        elif output_path.suffix.lower() == ".ogg":
            temp_path = output_path.with_suffix(".cover_tmp.ogg")
        else:
            temp_path = output_path.with_suffix(".cover_tmp.flac")

        attach_args = [
            "-y",
            "-i", str(output_path),
            "-i", str(cover_path),
            "-map", "0:a:0",
            "-map", "1:v:0",
            "-map_metadata", "0",
            "-c:a", "copy",
            "-c:v", "mjpeg",
            "-disposition:v:0", "attached_pic",
        ]

        if output_path.suffix.lower() == ".m4a":
            attach_args += [
                "-metadata:s:v:0", "title=Cover",
                "-metadata:s:v:0", "comment=Cover (front)",
            ]

        attach_args += [str(temp_path)]

        attach_result = self._ffmpeg_runner.run(
            attach_args,
            cancel_event=self._cancel_event,
            extra_args=["-nostdin"],
        )

        """print("COVER ATTACH CMD:", attach_args)
        print("COVER ATTACH SUCCESS:", attach_result.success)
        print("COVER ATTACH ERROR:", attach_result.error_message)
        print("TEMP PATH:", temp_path)
        print("TEMP EXISTS:", temp_path.exists())"""

        if not attach_result.success:
            if cover_path.exists():
                cover_path.unlink()
            if temp_path.exists():
                temp_path.unlink()
            return False

        try:
            os.replace(temp_path, output_path)
        except OSError:
            if cover_path.exists():
                cover_path.unlink()
            if temp_path.exists():
                temp_path.unlink()
            return False

        if cover_path.exists():
            cover_path.unlink()

        return True
