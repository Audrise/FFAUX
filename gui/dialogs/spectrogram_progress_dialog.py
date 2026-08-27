"""
# Dialog shown after clicking "Generate" in Spectrogram Settings.

Similar to ConversionProgressDialog, but for a single job. Reuses
ProgressPanel and the same 0-100% progress reporting used by CONVERT jobs.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QVBoxLayout,
    QLabel,
    QFrame,
    QDialog,
)

from core.models.job import Job
from gui.widgets.progress_panel import ProgressPanel
from utils.logger import get_logger

logger = get_logger("gui.dialogs.spectrogram_progress")

class SpectrogramProgressDialog(QDialog):
    cancelRequested = Signal()

    def __init__(self, job: Job, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generating Spectrogram")
        self.resize(480, 220)
        self._job = job
        self._job_id = job.id
        self._output_path = job.output_path
        self._cancelled = False
        self._finished = False
        self._status_label = QLabel("Scanning waveform...")
        self._status_label.setProperty("class", "dialog-title")

        current_file_label = QLabel("SOURCE FILE:")
        current_file_label.setProperty("class", "section-caption")

        self._source_label = QLabel(job.audio_file.filename)
        self._source_label.setWordWrap(True)

        current_file_layout = QVBoxLayout()
        current_file_layout.setContentsMargins(10, 8, 10, 8)
        current_file_layout.setSpacing(2)
        current_file_layout.addWidget(self._source_label)

        current_file_frame = QFrame()
        current_file_frame.setFrameShape(QFrame.Shape.StyledPanel)
        current_file_frame.setLayout(current_file_layout)

        self._progress_panel = ProgressPanel()
        self._progress_panel.reset(total=1)

        self._buttons = QDialogButtonBox()

        self._cancel_btn = self._buttons.addButton(
            "Cancel",
            QDialogButtonBox.ButtonRole.RejectRole,
        )
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(self._status_label)
        layout.addWidget(current_file_label)
        layout.addWidget(current_file_frame)
        layout.addWidget(self._progress_panel)
        layout.addWidget(self._buttons)

    def _on_cancel_clicked(self) -> None:
        self._cancelled = True
        logger.warning("Spectrogram generation cancelled")

        self.cancelRequested.emit()
        self.reject()

    def update_job_progress(self, job_id: str, percent: float) -> None:
        if (self._cancelled or self._finished or job_id != self._job_id):
            return

        self._progress_panel.update_job_progress(job_id, percent)

    def mark_job_done(self, failed: bool = False) -> None:
        if self._cancelled or self._finished:
            return

        self._finished = True

        self._progress_panel.mark_job_done()

        logger.info("Spectrogram generation finished: failed=%s", failed)
        self.accept()

        if not failed:
            self._show_result()

    def _show_result(self) -> None:
        job = self._job

        output_path = Path(self._output_path)
        output_name = output_path.name
        output_dir = str(output_path.parent)

        status_label = QLabel("Spectrogram Generated")
        status_label.setProperty("class", "dialog-title")

        current_file_label = QLabel("SOURCE FILE:")
        current_file_label.setProperty("class", "section-caption")

        source_label = QLabel(job.audio_file.filename)
        source_label.setWordWrap(True)

        current_file_layout = QVBoxLayout()
        current_file_layout.setContentsMargins(10, 8, 10, 8)
        current_file_layout.setSpacing(2)
        current_file_layout.addWidget(source_label)

        current_file_frame = QFrame()
        current_file_frame.setFrameShape(QFrame.Shape.StyledPanel)
        current_file_frame.setLayout(current_file_layout)

        output_label = QLabel("OUTPUT FILE:")
        output_label.setProperty("class", "section-caption")

        output_name_label = QLabel(output_name)
        output_name_label.setWordWrap(True)

        output_layout = QVBoxLayout()
        output_layout.setContentsMargins(10, 8, 10, 8)
        output_layout.setSpacing(2)
        output_layout.addWidget(output_name_label)

        output_frame = QFrame()
        output_frame.setFrameShape(QFrame.Shape.StyledPanel)
        output_frame.setLayout(output_layout)

        result_dialog = QDialog(self.parentWidget())
        result_dialog.setWindowTitle("Spectrogram Generated")
        result_dialog.resize(480, 220)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(result_dialog.accept)

        open_folder_btn = buttons.addButton("Open Output", QDialogButtonBox.ButtonRole.ActionRole)
        open_folder_btn.clicked.connect(result_dialog.accept)
        open_folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir)))

        layout = QVBoxLayout(result_dialog)
        layout.setSpacing(8)
        layout.addWidget(status_label)
        layout.addWidget(current_file_label)
        layout.addWidget(current_file_frame)
        layout.addWidget(output_label)
        layout.addWidget(output_frame)
        layout.addWidget(self._progress_panel)
        layout.addWidget(buttons)

        result_dialog.show()
        result_dialog.raise_()
        result_dialog.activateWindow()