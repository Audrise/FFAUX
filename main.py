from __future__ import annotations

import sys

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtCore import Qt

from core.config_service import ConfigService
from core.discord_presence_service import DiscordPresenceService
from core.job_manager import JobManager
from core.metadata_service import MetadataService
from core.template_service import TemplateService
from ffmpeg.ffmpeg_runner import FFmpegRunner
from ffmpeg.ffprobe_runner import FFprobeRunner
from gui.main_window import MainWindow
from utils.logger import setup_logging

APP_ROOT = Path(__file__).resolve().parent

def main() -> int:
    setup_logging(log_file=APP_ROOT / "config" / "app.log")

    app = QApplication(sys.argv)
    app.setApplicationName("AudriseFFTool")

    splash = None
    splash_path = APP_ROOT / "assets" / "icons" / "logo.png"

    if splash_path.exists():
        pixmap = QPixmap(str(splash_path))

        if not pixmap.isNull():
            splash = QWidget()
            splash.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint
            )
            splash.setAttribute(Qt.WA_TranslucentBackground)

            container = QWidget()

            container.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border-radius: 15px;
            }
            """)

            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(30)
            shadow.setOffset(0, 8)
            shadow.setColor(QColor(0, 0, 0, 120))
            container.setGraphicsEffect(shadow)

            layout = QVBoxLayout(splash)
            layout.setContentsMargins(15, 15, 15, 15)
            layout.addWidget(container)

            inner = QVBoxLayout(container)
            inner.setContentsMargins(30, 30, 30, 30)
            inner.setSpacing(5)

            logo = QLabel()
            logo.setAlignment(Qt.AlignCenter)
            logo.setPixmap(
                pixmap.scaled(
                    180,
                    180,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

            title = QLabel("AudriseFFTool")
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("""
                color: white;
                font-size: 18px;
                font-weight: 600;
            """)

            title_version = QLabel("Version 1.0")
            title_version.setAlignment(Qt.AlignCenter)
            title_version.setStyleSheet("""
                color: white;
                font-size: 14px;
                font-weight: 500;
            """)

            inner.addWidget(logo)
            inner.addWidget(title)
            inner.addWidget(title_version)

            splash.resize(320, 280)
            splash.show()

            app.processEvents()

    config_service = ConfigService(APP_ROOT / "config" / "app_config.json")
    config = config_service.load()

    ffprobe_runner = FFprobeRunner(ffprobe_path=config.ffprobe_path)
    ffmpeg_runner = FFmpegRunner(ffmpeg_path=config.ffmpeg_path)

    metadata_service = MetadataService(ffprobe_runner, ffmpeg_runner)
    template_service = TemplateService(APP_ROOT / "assets" / "templates")

    job_manager = JobManager(
        ffmpeg_path=config.ffmpeg_path,
        max_parallel_jobs=config.max_parallel_jobs,
    )

    # Discord Rich Presence is entirely optional
    # it's a safe no-op if pypresence isn't installed, Discord isn't running, or no
    # discord_client_id is configured yet (see: core/discord_presence_service.py for details).
    discord_presence = DiscordPresenceService(client_id=config.discord_client_id)
    if config.enable_discord_presence:
        discord_presence.start()

    icon_path = APP_ROOT / "assets" / "icons" / "logo.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    qss_path = APP_ROOT / "assets" / "styles" / "main.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    window = MainWindow(
        config_service=config_service,
        job_manager=job_manager,
        metadata_service=metadata_service,
        template_service=template_service,
        discord_presence_service=discord_presence,
    )

    # Restore the window size/position the user last left it at (see
    # MainWindow.closeEvent). Falls back to maximized on first run, since
    # config.window_maximized defaults to True.
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