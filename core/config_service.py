"""
# Application configuration management (binary path, output preferences, etc.).

Stored as JSON in config/app_config.json. The schema undergoes lightweight validation
via a dataclass to ensure key typos do not go undetected.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

CONFIG_SCHEMA_VERSION = 1

@dataclass
class AppConfig:
    version: int = CONFIG_SCHEMA_VERSION
    ffmpeg_path: str = "bin/ffmpeg.exe"
    ffprobe_path: str = "bin/ffprobe.exe"
    output_directory: str = ""
    output_suffix: str = "_converted"
    max_parallel_jobs: int = 2
    default_bitrate: str = "192k"
    last_template: str = ""
    theme: str = "system"
    window_maximized: bool = True
    window_width: int = 1200
    window_height: int = 600
    window_x: int = -1
    window_y: int = -1
    enable_discord_presence: bool = True
    track_table_column_widths: list[int] = field(default_factory=list)
    track_table_hidden_columns: Optional[list[int]] = None
    track_table_column_order: Optional[list[int]] = None
    session_paths: list[str] = field(default_factory=list)

    # Default conversion settings, edited from SettingsDialog's "Default
    # Conversion Settings" section, and used to seed MainWindow's
    # ConversionSettings on startup (see main.py). Kept as plain
    # str/int/bool here (not the ConversionSettings/OutputFormat classes
    # directly) to stay consistent with the rest of this JSON-serializable
    # config -- convert via OutputFormat(value) where needed.
    default_output_format: str = "mp3"
    default_sample_rate_hz: int = 44100
    default_bit_depth: int = 16
    default_bitrate_kbps: int = 320
    default_use_soxr: bool = True
    default_soxr_precision: int = 28
    default_flac_compression_level: int = 5

class ConfigService:
    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self._config: AppConfig = AppConfig()

    @property
    def config(self) -> AppConfig:
        return self._config

    def load(self) -> AppConfig:
        if not self.config_path.exists():
            self._config = AppConfig()
            self.save()
            return self._config

        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._config = AppConfig()
            return self._config

        known_fields = set(AppConfig.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known_fields}
        self._config = AppConfig(**{**asdict(AppConfig()), **filtered})
        return self._config

    def save(self) -> None:
        self.config_path.write_text(
            json.dumps(asdict(self._config), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self._config, key, default)

    def set(self, key: str, value: Any) -> None:
        if not hasattr(self._config, key):
            raise KeyError(f"Unknown config key: {key}")
        setattr(self._config, key, value)