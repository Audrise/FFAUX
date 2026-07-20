"""Manajemen konfigurasi aplikasi (path binary, preferensi output, dll).

Disimpan sebagai JSON di config/app_config.json. Skema divalidasi ringan
lewat dataclass supaya salah ketik key tidak lolos diam-diam.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


CONFIG_SCHEMA_VERSION = 1


@dataclass
class AppConfig:
    version: int = CONFIG_SCHEMA_VERSION
    ffmpeg_path: str = "bin/ffmpeg.exe"
    ffprobe_path: str = "bin/ffprobe.exe"
    output_directory: str = ""
    """Kosong berarti: simpan di folder yang sama dengan file sumber."""
    output_suffix: str = "_converted"
    max_parallel_jobs: int = 2
    default_bitrate: str = "192k"
    last_template: str = ""
    theme: str = "system"


class ConfigService:
    """Sumber tunggal (single source of truth) untuk konfigurasi aplikasi."""

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
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(asdict(self._config), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self._config, key, default)

    def set(self, key: str, value: Any) -> None:
        if not hasattr(self._config, key):
            raise KeyError(f"Config key tidak dikenal: {key}")
        setattr(self._config, key, value)
