"""
# Dialog shown right after the user clicks "Save" in Conversion Settings.

Reuses gui/widgets/progress_panel.py's ProgressPanel for the actual
aggregate progress bar/counter logic instead of reimplementing it.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialogButtonBox, QVBoxLayout, QLabel, QFrame, QDialog

from core.models.job import Job
from gui.widgets.progress_panel import ProgressPanel
from utils.logger import get_logger

logger = get_logger("gui.dialogs.conversion_progress")

class ConversionProgressDialog(QDialog):
    cancelRequested = Signal()

    def __init__(self, jobs: list[Job], parent=None):
        super().__init__(parent)

        self.setWindowTitle("Converting")
        self.resize(480, 260)

        self._buttons = QDialogButtonBox()
        self._total_jobs = len(jobs)
        self._completed_jobs = 0
        self._failed_jobs = 0
        self._current_jobs = 1
        self._source_name = ""
        self._output_dir = str(Path(jobs[0].output_path).parent) if jobs else ""
        self._cancelled = False
        self._finished = False

        # Status
        self._status_label = QLabel(f"Converting 1 of {self._total_jobs} files")
        self._status_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        # Current file title
        current_file_label = QLabel("CURRENT FILE:")
        current_file_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #888;")

        # Current source/target
        self._source_label = QLabel("-")
        self._source_label.setWordWrap(True)

        self._arrow_label = QLabel("↓")

        self._target_label = QLabel("-")
        self._target_label.setWordWrap(True)

        if self._total_jobs > 1:
            logger.info(f"Converting {self._current_jobs} of {self._total_jobs} files")

        current_file_layout = QVBoxLayout()
        current_file_layout.setContentsMargins(10, 8, 10, 8)
        current_file_layout.setSpacing(2)
        current_file_layout.addWidget(self._source_label)
        current_file_layout.addWidget(self._arrow_label)
        current_file_layout.addWidget(self._target_label)
        current_file_frame = QFrame()
        current_file_frame.setFrameShape(QFrame.Shape.StyledPanel)
        current_file_frame.setLayout(current_file_layout)

        # Progress panel
        self._progress_panel = ProgressPanel()
        self._progress_panel.reset(total=self._total_jobs)

        # Statistics
        self._stats_label = QLabel("+ 0 Completed     - 0 Failed")

        self._cancel_btn = self._buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(self._status_label)
        layout.addWidget(current_file_label)
        layout.addWidget(current_file_frame)
        layout.addWidget(self._stats_label)
        layout.addWidget(self._progress_panel)
        layout.addWidget(self._buttons)

    def _on_cancel_clicked(self) -> None:
        self._cancelled = True
        logger.warning("Converting Cancelled")
        self.cancelRequested.emit()
        self.reject()

    def set_current_file(self, source_name: str,target_name: str) -> None:
        # Ignore updates after cancellation.
        if self._cancelled or self._finished:
            return

        self._source_label.setText(source_name)
        self._target_label.setText(target_name)
        self._source_name = source_name

        self._progress_panel.reset(self._total_jobs)

        if self._total_jobs == 1:
            logger.info(f"Converting {self._source_name}")

    def update_job_progress(self, job_id: str,percent: float) -> None:
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

        finished_jobs = (self._completed_jobs + self._failed_jobs)

        # Update statistics immediately, including the final job.
        self._stats_label.setText(f"+ {self._completed_jobs} Completed     - {self._failed_jobs} Failed")

        if finished_jobs >= self._total_jobs:
            self._on_conversion_finished()
            return

        self._current_jobs = finished_jobs + 1

        self._status_label.setText(f"Converting {self._current_jobs} of {self._total_jobs} files")

        if self._total_jobs > 1:
            logger.info(f"Converting {self._current_jobs} of {self._total_jobs} files")

    def _on_conversion_finished(self) -> None:
        # Do not show result if user cancelled.
        if self._cancelled:
            return

        # Prevent this from being executed more than once.
        if self._finished:
            return

        self._finished = True

        logger.info("Conversion finished: %d completed, %d failed", self._completed_jobs, self._failed_jobs)

        self.accept()
        self._show_conversion_result()

    def _show_conversion_result(self) -> None:
        # Extra safety guard
        if self._cancelled:
            return

        self._result_dialog = QDialog(self.parentWidget())
        self._result_dialog.setWindowTitle("Conversion Complete")
        self._result_dialog.resize(480, 260)

        status_label = QLabel("Conversion Complete")
        status_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        current_file_label = QLabel(f"{self._current_jobs} of {self._total_jobs} Files converted")
        current_file_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #888;")

        source_label = QLabel(self._source_label.text())
        source_label.setWordWrap(True)

        arrow_label = QLabel("↓")

        target_label = QLabel(self._target_label.text())
        target_label.setWordWrap(True)

        current_file_layout = QVBoxLayout()
        current_file_layout.setContentsMargins(10, 8, 10, 8)
        current_file_layout.setSpacing(2)

        current_file_layout.addWidget(source_label)
        current_file_layout.addWidget(arrow_label)
        current_file_layout.addWidget(target_label)

        current_file_frame = QFrame()
        current_file_frame.setFrameShape(QFrame.Shape.StyledPanel)
        current_file_frame.setLayout(current_file_layout)

        stats_label = QLabel(f"+ {self._completed_jobs} Completed     - {self._failed_jobs} Failed")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self._result_dialog.accept)

        if self._output_dir:
            open_folder_btn = buttons.addButton("Open Output Folder", QDialogButtonBox.ButtonRole.ActionRole)
            open_folder_btn.clicked.connect(self._result_dialog.accept)
            open_folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self._output_dir)))

        layout = QVBoxLayout(self._result_dialog)
        layout.setSpacing(8)
        layout.addWidget(status_label)
        layout.addWidget(current_file_label)
        layout.addWidget(current_file_frame)
        layout.addWidget(stats_label)
        layout.addWidget(self._progress_panel)
        layout.addWidget(buttons)

        self._result_dialog.show()
        self._result_dialog.raise_()
        self._result_dialog.activateWindow()
