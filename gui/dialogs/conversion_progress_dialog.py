"""
# Dialog shown right after the user clicks "Save" in Conversion Settings.

Replaces the old always-in-window bottom progress bar (previously
toggled via View > Show Progress Bar / Ctrl+.), which has been removed.

Reuses gui/widgets/progress_panel.py's ProgressPanel for the actual
aggregate progress bar/counter logic instead of reimplementing it.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QFrame

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

        self._total_jobs = len(jobs)
        self._completed_jobs = 0
        self._failed_jobs = 0
        self._current_jobs = 1
        self._source_name = ""

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

        # logger.info(f"Converting 1 of {self._total_jobs} files")

        if self._total_jobs > 1:
            logger.info(
                f"Converting {self._current_jobs} of {self._total_jobs} files"
            )

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
        self._stats_label = QLabel(
            "+ 0 Completed     - 0 Failed"
        )

        # Buttons
        self._buttons = QDialogButtonBox()

        self._ok_btn = self._buttons.addButton(
            "OK",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )

        self._cancel_btn = self._buttons.addButton(
            "Cancel",
            QDialogButtonBox.ButtonRole.RejectRole,
        )

        self._ok_btn.clicked.connect(self.accept)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)

        # Hide OK while converting
        self._ok_btn.setVisible(False)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(self._status_label)

        layout.addWidget(current_file_label)
        layout.addWidget(current_file_frame)

        layout.addWidget(self._stats_label)

        # Progress bar at the bottom of the content
        layout.addWidget(self._progress_panel)

        # Buttons at the very bottom
        layout.addWidget(self._buttons)

    def _on_cancel_clicked(self) -> None:
        logger.warning("Converting Cancelled")
        self.cancelRequested.emit()
        self.reject()

    def set_current_file(self, source_name: str, target_name: str) -> None:
        self._source_label.setText(source_name)
        self._target_label.setText(target_name)
        self._source_name = source_name

        if self._total_jobs == 1:
            logger.info(f"Converting {self._source_name}")

    def update_job_progress(self, job_id: str, percent: float) -> None:
        self._progress_panel.update_job_progress(job_id, percent)

    def mark_job_done(self, failed: bool = False) -> None:
        self._progress_panel.mark_job_done()

        if failed:
            self._failed_jobs += 1
        else:
            self._completed_jobs += 1

        finished_jobs = self._completed_jobs + self._failed_jobs

        # Update statistics immediately, including the final job.
        self._stats_label.setText(
            f"+ {self._completed_jobs} Completed     "
            f"- {self._failed_jobs} Failed"
        )

        if finished_jobs >= self._total_jobs:
            self._on_conversion_finished()
            return

        self._current_jobs = finished_jobs + 1
        self._status_label.setText(
            f"Converting {self._current_jobs} of {self._total_jobs} files"
        )

        if self._total_jobs > 1:
            logger.info(
                f"Converting {self._current_jobs} of {self._total_jobs} files"
            )

    def _on_conversion_finished(self) -> None:
        self.setWindowTitle("Conversion Complete")
        self._status_label.setText("Conversion Complete")

        self._cancel_btn.setVisible(False)
        self._ok_btn.setVisible(True)
        # self.accept()