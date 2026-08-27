"""
# Widget log output FFmpeg (read-only and auto-scroll).
"""
from __future__ import annotations

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

class LogViewer(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(5000)  # prevent memory bloat

    def append_line(self, job_id: str, line: str) -> None:
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.appendPlainText(f"[{job_id[:8]}] {line}")

    def clear_log(self) -> None:
        self.clear()