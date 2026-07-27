"""
Aggregate progress panel: average progress of all jobs in the batch.
"""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget

class ProgressPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._label = QLabel("0 / 0 Complete")

        layout.addWidget(self._bar, stretch=1)
        layout.addWidget(self._label)

        self._progress_by_id: dict[str, float] = {}
        self._done_count = 0
        self._total_count = 0

    def reset(self, total: int) -> None:
        self._progress_by_id.clear()
        self._done_count = 0
        self._total_count = total
        self._bar.setValue(0)
        self._label.setText(f"0 / {total} Complete")

    def update_job_progress(self, job_id: str, percent: float) -> None:
        self._progress_by_id[job_id] = percent
        self._recalculate()

    def mark_job_done(self) -> None:
        self._done_count += 1
        self._label.setText(f"{self._done_count} / {self._total_count} Complete")

    def _recalculate(self) -> None:
        if not self._progress_by_id:
            return
        avg = sum(self._progress_by_id.values()) / len(self._progress_by_id)
        self._bar.setValue(int(round(avg)))
