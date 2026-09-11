"""
# Centralized resource-root

Works correctly both in dev mode and in a frozen PyInstaller build (.exe)
"""
from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_DIR = ("config", "assets/templates")

def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent

def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent

def resolve_tool_path(path_str: str) -> str:
    path = Path(path_str)

    if path.is_absolute():
        return str(path)

    return str(app_root() / path)

def required_dir() -> list[Path]:
    if not getattr(sys, "frozen", False):
        return []

    root = app_root()

    return [
        root / rel
        for rel in REQUIRED_DIR
        if not (root / rel).is_dir()
    ]

def assets_path() -> Path:
    return resource_root() / "assets"

def icons_path() -> Path:
    return assets_path() / "icons"

def styles_path() -> Path:
    return assets_path() / "styles"