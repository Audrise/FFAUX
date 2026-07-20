"""Konfigurasi logging terpusat.

Modul lain cukup: `logger = logging.getLogger(__name__)`.
GUI dapat memasang handler tambahan (mis. QtLogHandler) untuk menampilkan
log ke widget, tanpa modul lain perlu tahu bahwa lognya ditampilkan di GUI.
"""
from __future__ import annotations

import logging
from pathlib import Path

APP_LOGGER_NAME = "audrise"


def setup_logging(log_file: str | Path | None = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.setLevel(level)

    if logger.handlers:
        return logger  # sudah pernah di-setup, hindari duplikasi handler

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{APP_LOGGER_NAME}.{name}")
