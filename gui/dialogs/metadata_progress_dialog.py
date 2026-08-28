"""
# Dialog shown after clicking "Save" in the Metadata Editor.

Similar to ConversionProgressDialog. Reuses ProgressPanel and
the same 0-100% progress reporting used by CONVERT jobs.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialogButtonBox, QVBoxLayout, QLabel, QFrame, QDialog

from core.models.job import Job
from gui.widgets.progress_panel import ProgressPanel
from utils.logger import get_logger

logger = get_logger("gui.dialogs.metadata_progress")

_TITLES = {
    "metadata": ("Metadata Saved", "Metadata has been saved successfully."),
    "cover": ("Cover Art Saved", "Cover art has been saved successfully."),
    "metadata_and_cover": (
        "Metadata and Cover Art Saved",
        "Metadata and cover art have been saved successfully.",
    ),
}

class MetadataProgressDialog(QDialog):
    cancelRequested = Signal()

    def __init__(self, jobs: list[Job], kind: str, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Saving")
        self.resize(480, 240)

        self._kind = kind
        self._total_jobs = len(jobs)
        self._completed_jobs = 0
        self._failed_jobs = 0
        self._current_job_index = 1
        self._cancelled = False
        self._finished = False

        self._status_label = QLabel(self._status_text())
        self._status_label.setProperty("class", "dialog-title")

        current_file_label = QLabel("CURRENT FILE:")
        current_file_label.setProperty("class", "section-caption")

        self._source_label = QLabel("-")
        self._source_label.setWordWrap(True)

        current_file_layout = QVBoxLayout()
        current_file_layout.setContentsMargins(10, 8, 10, 8)
        current_file_layout.setSpacing(2)
        current_file_layout.addWidget(self._source_label)
        current_file_frame = QFrame()
        current_file_frame.setFrameShape(QFrame.Shape.StyledPanel)
        current_file_frame.setLayout(current_file_layout)

        self._progress_panel = ProgressPanel()
        self._progress_panel.reset(total=self._total_jobs)

        self._stats_label = QLabel("+ 0 Completed     - 0 Failed")

        self._buttons = QDialogButtonBox()
        self._cancel_btn = self._buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(self._status_label)
        layout.addWidget(current_file_label)
        layout.addWidget(current_file_frame)
        layout.addWidget(self._stats_label)
        layout.addWidget(self._progress_panel)
        layout.addWidget(self._buttons)

    def _status_text(self) -> str:
        if self._total_jobs == 1:
            return "Saving..."
        return f"Saving {self._current_job_index} of {self._total_jobs} files"

    def _on_cancel_clicked(self) -> None:
        self._cancelled = True
        logger.warning("Saving metadata/cover art cancelled")
        self.cancelRequested.emit()
        self.reject()

    def set_current_file(self, source_name: str) -> None:
        if self._cancelled or self._finished:
            return
        self._source_label.setText(source_name)
        if self._total_jobs == 1:
            logger.info("Saving %s", source_name)

    def update_job_progress(self, job_id: str, percent: float) -> None:
        if self._cancelled or self._finished:
            return
        self._progress_panel.update_job_progress(job_id, percent)

    def mark_job_done(self, failed: bool = False) -> None:
        # IMPORTANT: Ignore late "job done" signals after Cancel.
        if self._cancelled or self._finished:
            return

        self._progress_panel.mark_job_done()

        if failed:
            self._failed_jobs += 1
        else:
            self._completed_jobs += 1

        finished_jobs = self._completed_jobs + self._failed_jobs
        self._stats_label.setText(f"+ {self._completed_jobs} Completed     - {self._failed_jobs} Failed")

        if finished_jobs >= self._total_jobs:
            self._on_saving_finished()
            return

        self._current_job_index = finished_jobs + 1
        self._status_label.setText(self._status_text())

        if self._total_jobs > 1:
            logger.info("Saving %d of %d files", self._current_job_index, self._total_jobs)

    def _on_saving_finished(self) -> None:
        if self._cancelled or self._finished:
            return
        self._finished = True

        logger.info("Saving finished: %d completed, %d failed", self._completed_jobs, self._failed_jobs)

        self.accept()
        self._show_result()

    def _show_result(self) -> None:
        all_success = self._failed_jobs == 0

        if all_success:
            title, text = _TITLES.get(self._kind, _TITLES["metadata"])
        else:
            title = "Saving Completed with Errors"
            text = (
                f"{self._completed_jobs} of {self._total_jobs} file(s) were saved successfully.\n"
                f"{self._failed_jobs} file(s) failed."
            )

        result_dialog = QDialog(self.parentWidget())
        result_dialog.setWindowTitle(title)
        result_dialog.resize(480, 240)

        status_label = QLabel(title)
        status_label.setProperty("class", "dialog-title")

        detail_label = QLabel(f"{self._completed_jobs} of {self._total_jobs} file(s) saved")
        detail_label.setProperty("class", "section-caption")

        text_label = QLabel(text)
        text_label.setWordWrap(True)

        detail_layout = QVBoxLayout()
        detail_layout.setContentsMargins(10, 8, 10, 8)
        detail_layout.setSpacing(2)
        detail_layout.addWidget(text_label)
        detail_frame = QFrame()
        detail_frame.setFrameShape(QFrame.Shape.StyledPanel)
        detail_frame.setLayout(detail_layout)

        stats_label = QLabel(f"+ {self._completed_jobs} Completed     - {self._failed_jobs} Failed")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(result_dialog.accept)

        layout = QVBoxLayout(result_dialog)
        layout.setSpacing(8)
        layout.addWidget(status_label)
        layout.addWidget(detail_label)
        layout.addWidget(detail_frame)
        layout.addWidget(stats_label)
        layout.addWidget(buttons)

        result_dialog.show()
        result_dialog.raise_()
        result_dialog.activateWindow()