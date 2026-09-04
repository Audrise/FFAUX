"""
# Bridges Python's `logging` module into the GUI's LogViewer widget.

logging calls can happen from any thread (e.g. FFmpegWorker running inside
a QThreadPool worker thread), so this handler never touches the widget
directly -- it only emits a Qt signal, and the receiving slot (connected
on the main thread) is the one that actually appends to LogViewer.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

class QtLogHandler(logging.Handler, QObject):
    logRecordEmitted = Signal(str)

    def __init__(self, level: int = logging.NOTSET):
        logging.Handler.__init__(self, level)
        QObject.__init__(self)
        self._buffer: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            self.handleError(record)
            return

        self._buffer.append(message)
        self.logRecordEmitted.emit(message)

    def drain_buffered_lines(self) -> list[str]:
        # Call once the LogViewer is ready, to backfill anything logged
        # before logRecordEmitted had a listener connected.
        lines, self._buffer = self._buffer, []
        return lines