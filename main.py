from __future__ import annotations

import sys
import logging

from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QWidget,
    QLabel,
    QVBoxLayout,
    QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect
)

from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtCore import Qt, QEventLoop, QPropertyAnimation

from core.config_service import ConfigService
from core.discord_presence_service import DiscordPresenceService
from core.job_manager import JobManager
from core.metadata_service import MetadataService
from core.template_service import TemplateService
from ffmpeg.ffmpeg_runner import FFmpegRunner
from ffmpeg.ffprobe_runner import FFprobeRunner
from gui.main_window import MainWindow
from gui.qt_log_handler import QtLogHandler
from utils.logger import setup_logging, get_logger

from utils.logger import (
    APP_LOGGER_NAME,
    setup_logging,
    get_logger,
    get_formatter
)

from utils.paths import (
    app_root,
    resolve_tool_path,
    required_dir,
    icons_path,
    splash_path,
    styles_path
)

logger = get_logger("main")

def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("FFAUX")

    # Mandatory folder validation
    missing = required_dir()
    if missing:
        missing_list = "\n".join(f"  - {p}" for p in missing)
        QMessageBox.critical(
            None,
            "Startup Failed",
            "FFAUX cannot start because required folders are missing:\n\n"
            f"{missing_list}\n\n"
            "This usually happens when FFAUX.exe is moved out of its "
            "installation folder. Please reinstall FFAUX using the "
            "official installer instead of moving the .exe by itself.",
        )
        return 1

    # Load logging
    try:
        setup_logging(log_file=app_root() / "config" / "ffaux.log")
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Startup Failed",
            f"Failed to initialize logging:\n\n{exc}"
        )
        return 1

    qt_log_handler = QtLogHandler()
    qt_log_handler.setFormatter(get_formatter())
    logging.getLogger(APP_LOGGER_NAME).addHandler(qt_log_handler)
    logger.info("Starting FFAUX")

    # Load QT Stylesheet
    qss_path = styles_path() / "main.qss"
    if not qss_path.exists():
        logger.error(f"Missing stylesheet: {qss_path}")

        QMessageBox.critical(
            None,
            "Startup Failed",
            "FFAUX cannot start because the required stylesheet is missing:\n\n"
            f"{qss_path}\n\n"
            "Please reinstall FFAUX using the official installer."
        )
        return 1

    app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    # Load config
    try:
        config_service = ConfigService(
            app_root() / "config" / "ffaux.json"
        )
        config = config_service.load()
        logger.info("Configuration loaded successfully")

    except Exception as exc:
        logger.warning(exc)

        QMessageBox.critical(
            None,
            "Startup Failed",
            f"Failed to load configuration:\n\n{exc}"
        )
        return 1

    splash = None
    fade_animation = None

    APP_SPLASH_PATH = splash_path() / "FFAUX.png"
    if APP_SPLASH_PATH.exists():
        pixmap = QPixmap(str(APP_SPLASH_PATH))

        if not pixmap.isNull():
            splash = QWidget()
            splash.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint
            )
            splash.setAttribute(Qt.WA_TranslucentBackground)

            container = QWidget()
            container.setObjectName("splashContainer")

            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(35)
            shadow.setOffset(0, 0)
            shadow.setColor(QColor(0, 0, 0, 120))
            container.setGraphicsEffect(shadow)

            layout = QVBoxLayout(splash)
            layout.setContentsMargins(30, 15, 30, 15)
            layout.addWidget(container)

            inner = QVBoxLayout(container)
            inner.setContentsMargins(30, 30, 30, 30)
            inner.setSpacing(4)

            logo = QLabel()
            logo.setAlignment(Qt.AlignCenter)
            logo.setPixmap(
                pixmap.scaled(
                    170,
                    170,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

            app_title = QLabel("FFAUX v1.0.0")
            app_title.setAlignment(Qt.AlignCenter)
            app_title.setObjectName("splashTitle")

            inner.addWidget(logo)
            inner.addWidget(app_title)

            splash.resize(320, 280)

            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(0)
            splash.setGraphicsEffect(opacity_effect)

            fade_animation = QPropertyAnimation(opacity_effect, b"opacity", splash)
            fade_animation.setDuration(150)
            fade_animation.setStartValue(0.0)
            fade_animation.setEndValue(1.0)

            splash.show()

            loop = QEventLoop()
            fade_animation.finished.connect(loop.quit)

            fade_animation.start()
            loop.exec()

    ffprobe_runner = FFprobeRunner(ffprobe_path=resolve_tool_path(config.ffprobe_path))
    ffmpeg_runner = FFmpegRunner(ffmpeg_path=resolve_tool_path(config.ffmpeg_path))

    metadata_service = MetadataService(ffprobe_runner, ffmpeg_runner)
    template_service = TemplateService(app_root() / "assets" / "templates")

    job_manager = JobManager(
        ffmpeg_path=resolve_tool_path(config.ffmpeg_path),
        max_parallel_jobs=config.max_parallel_jobs,
    )

    discord_presence = DiscordPresenceService(client_id=config.discord_client_id)
    if config.enable_discord_presence:
        discord_presence.start()

    APP_ICON_PATH = icons_path() / "FFAUX.ico"
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))

    window = MainWindow(
        config_service=config_service,
        job_manager=job_manager,
        metadata_service=metadata_service,
        template_service=template_service,
        discord_presence_service=discord_presence,
    )

    qt_log_handler.logRecordEmitted.connect(window.append_log_line)

    for line in qt_log_handler.drain_buffered_lines():
        window.append_log_line(line)

    logger.info("FFAUX started successfully")

    if config.window_maximized:
        window.showMaximized()

    else:
        if config.window_width > 0 and config.window_height > 0:
            window.resize(config.window_width, config.window_height)

        if config.window_x >= 0 and config.window_y >= 0:
            window.move(config.window_x, config.window_y)

        window.show()

    if splash:
        splash.close()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
