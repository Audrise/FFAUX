from __future__ import annotations

import sys

from pathlib import Path

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
from utils.logger import setup_logging, get_logger

logger = get_logger("main")

def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent

def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

RESOURCE_ROOT = _resource_root()
APP_ROOT = _app_root()

# FFAUX
APP_SPLASH_PATH = RESOURCE_ROOT / "assets" / "splash" / "FFAUX.png"
APP_ICON_PATH = RESOURCE_ROOT / "assets" / "icons" / "FFAUX.ico"

# main_window assets
UNDO_ICON_PATH = RESOURCE_ROOT / "assets" / "icons" / "Undo.ico"
REDO_ICON_PATH = RESOURCE_ROOT / "assets" / "icons" / "Redo.ico"
SEARCH_ICON_PATH = RESOURCE_ROOT / "assets" / "icons" / "Search.ico"

def _resolve_tool_path(path_str: str) -> str:
    path = Path(path_str)
    if path.is_absolute():
        return str(path)
    return str(APP_ROOT / path)

REQUIRED_DIRS = ("config", "assets/templates")

def _missing_required_dirs() -> list[Path]:
    return [APP_ROOT / rel for rel in REQUIRED_DIRS if not (APP_ROOT / rel).is_dir()]

def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("FFAUX")

    # Mandatory folder validation
    missing = _missing_required_dirs()
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
        setup_logging(log_file=APP_ROOT / "config" / "ffaux.log")
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Startup Failed",
            f"Failed to initialize logging:\n\n{exc}"
        )
        return 1

    # Load QT Stylesheet
    qss_path = RESOURCE_ROOT / "assets" / "styles" / "main.qss"
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
            APP_ROOT / "config" / "ffaux.json"
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

            title = QLabel("Format Whatever You Want.")
            title.setAlignment(Qt.AlignCenter)
            title.setObjectName("splashSlogan")

            inner.addWidget(logo)
            inner.addWidget(app_title)
            inner.addWidget(title)

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

    ffprobe_runner = FFprobeRunner(ffprobe_path=_resolve_tool_path(config.ffprobe_path))
    ffmpeg_runner = FFmpegRunner(ffmpeg_path=_resolve_tool_path(config.ffmpeg_path))

    metadata_service = MetadataService(ffprobe_runner, ffmpeg_runner)
    template_service = TemplateService(APP_ROOT / "assets" / "templates")

    job_manager = JobManager(
        ffmpeg_path=_resolve_tool_path(config.ffmpeg_path),
        max_parallel_jobs=config.max_parallel_jobs,
    )

    discord_presence = DiscordPresenceService(client_id=config.discord_client_id)
    if config.enable_discord_presence:
        discord_presence.start()

    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))

    window = MainWindow(
        config_service=config_service,
        job_manager=job_manager,
        metadata_service=metadata_service,
        template_service=template_service,
        discord_presence_service=discord_presence,
        undo_icon_path=UNDO_ICON_PATH,
        redo_icon_path=REDO_ICON_PATH,
        search_icon_path=SEARCH_ICON_PATH,
    )

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

    logger.info("FFAUX started successfully")

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
