"""
# Widget log output FFmpeg (read-only, auto-scroll).
"""
from __future__ import annotations

from PySide6.QtGui import QTextCharFormat, QTextCursor, QColor
from PySide6.QtWidgets import QPlainTextEdit

class LogViewer(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(5000)  # prevent memory bloat

    def append_line(self, job_id: str, line: str) -> None:
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.appendPlainText(f"{line}")
        # self.appendPlainText(f"[{job_id[:8]}] {line}")

    def append_app_log(self, message: str) -> None:
        self.moveCursor(QTextCursor.MoveOperation.End)

        format = QTextCharFormat()

        if "[INFO]" in message:
            format.setForeground(QColor("#00FF00"))
        elif "[WARNING]" in message:
            format.setForeground(QColor("#FFB700"))
        elif "[ERROR]" in message:
            format.setForeground(QColor("#F14C4C"))
        elif "[CRITICAL]" in message:
            format.setForeground(QColor("#FF0000"))

        cursor = self.textCursor()
        cursor.insertText(message + "\n", format)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_log(self) -> None:
        self.clear()