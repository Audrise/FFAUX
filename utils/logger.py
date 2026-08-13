"""
# Centralized logging configuration.

Other modules simply use: `logger = logging.getLogger(__name__)`.
The GUI can attach additional handlers (e.g., QtLogHandler) to display
logs in a widget, without other modules needing to know that the logs are being displayed in the GUI.
"""
from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime, timezone

APP_LOGGER_NAME = "FFTool"

class DayFormatter(logging.Formatter):
    DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        return f"{self.DAYS[dt.weekday()]} {dt:%d-%m-%y %H:%M:%S}"

def setup_logging(
    log_file: str | Path | None = None,
    level: int = logging.INFO,
) -> logging.Logger:
    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.setLevel(level)

    if logger.handlers:
        return logger  # already set up; avoid duplicate handlers

    formatter = DayFormatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{APP_LOGGER_NAME}.{name}")
