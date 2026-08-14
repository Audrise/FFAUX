"""
# Dialog shown right after the user clicks "Save" in Conversion Settings.

Replaces the old always-in-window bottom progress bar (previously
toggled via View > Show Progress Bar / Ctrl+.), which has been removed.

Non-modal (.show(), not .exec()) so the main window stays fully usable
while conversion runs in the background:
  - OK: just dismisses this dialog. Conversion keeps running regardless --
    JobManager's QThreadPool workers are independent of whether this
    dialog is open or closed.
  - Cancel: emits cancelRequested (MainWindow wires this to the same
    cancel_all() used by "Cancel All"), then dismisses the dialog.

Reuses gui/widgets/progress_panel.py's ProgressPanel for the actual
aggregate progress bar/counter logic instead of reimplementing it.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from core.models.job import Job
from gui.widgets.progress_panel import ProgressPanel

class ConversionProgressDialog(QDialog):
    cancelRequested = Signal()

    def __init__(self, jobs: list[Job], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Converting")
        self.resize(420, 120)

        self._message_label = QLabel("Converting...")
        self._message_label.setWordWrap(True)

        self._progress_panel = ProgressPanel()
        self._progress_panel.reset(total=len(jobs))

        self._total_jobs = len(jobs)
        self._completed_jobs = 0

        buttons = QDialogButtonBox()
        ok_btn = buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self._on_cancel_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(self._message_label)
        layout.addWidget(self._progress_panel)
        layout.addWidget(buttons)

    def _on_cancel_clicked(self) -> None:
        self.cancelRequested.emit()
        self.reject()

    def set_current_file(self, source_name: str, target_name: str) -> None:
        self._message_label.setText(
            f"Converting {source_name} to {target_name}"
        )

    def update_job_progress(self, job_id: str, percent: float) -> None:
        self._progress_panel.update_job_progress(job_id, percent)

    def mark_job_done(self) -> None:
        self._progress_panel.mark_job_done()

        self._completed_jobs += 1

        if self._completed_jobs >= self._total_jobs:
            self.accept()