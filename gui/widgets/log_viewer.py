"""
# Widget log output FFmpeg (read-only, auto-scroll).
"""
from __future__ import annotations

import re

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

        match = re.match(r"(\[[^\]]+\])\s+(\[[A-Z]+\])\s+(.*)", message)

        timestamp_format = QTextCharFormat()
        timestamp_format.setForeground(QColor("#808080"))

        level_format = QTextCharFormat()
        message_format = QTextCharFormat()

        message_format.setForeground(QColor("#D4D4D4"))

        if "[INFO]" in message:
            level_format.setForeground(QColor("#6A9955"))
        elif "[WARNING]" in message:
            level_format.setForeground(QColor("#D7BA7D"))
        elif "[ERROR]" in message:
            level_format.setForeground(QColor("#F14C4C"))
        elif "[CRITICAL]" in message:
            level_format.setForeground(QColor("#FF5555"))
        else:
            level_format.setForeground(QColor("#D4D4D4"))

        cursor = self.textCursor()

        if match:
            timestamp, level, text = match.groups()

            cursor.insertText(f"{timestamp} ", timestamp_format)
            cursor.insertText(f"{level} ", level_format)
            cursor.insertText(f"{text}\n", message_format)
        else:
            cursor.insertText(f"{message}\n", message_format)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_log(self) -> None:
        self.clear()