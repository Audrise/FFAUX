"""
# Metadata template management: save frequently used tag schemes.

Templates are stored as separate JSON files in `assets/templates/`,
making them easy to share between users (simply copy the file).
"""
from __future__ import annotations

import json
from pathlib import Path

from core.models.metadata import Metadata

TEMPLATE_SCHEMA_VERSION = 1

class TemplateService:
    def __init__(self, templates_dir: str | Path):
        self.templates_dir = Path(templates_dir)

    def list_templates(self) -> list[str]:
        return sorted(p.stem for p in self.templates_dir.glob("*.json"))

    def save_template(self, name: str, metadata: Metadata) -> Path:
        path = self._path_for(name)
        payload = {
            "version": TEMPLATE_SCHEMA_VERSION,
            "name": name,
            "metadata": metadata.to_dict(),
        }
        path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")
        return path

    def load_template(self, name: str) -> Metadata:
        path = self._path_for(name)
        if not path.exists():
            raise FileNotFoundError(f"Template '{name}' not found!")
        data = json.loads(path.read_text(encoding="utf-8"))
        return Metadata.from_dict(data.get("metadata", {}))

    def delete_template(self, name: str) -> None:
        path = self._path_for(name)
        if path.exists():
            path.unlink()

    def _path_for(self, name: str) -> Path:
        safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip()
        if not safe_name:
            raise ValueError("Invalid Template Name!")
        return self.templates_dir / f"{safe_name}.json"
