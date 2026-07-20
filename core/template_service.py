"""Manajemen template metadata: simpan skema tag yang sering dipakai berulang.

Template disimpan sebagai file JSON individual di assets/templates/,
sehingga mudah di-share antar pengguna (tinggal copy file).
"""
from __future__ import annotations

import json
from pathlib import Path

from core.models.metadata import Metadata

TEMPLATE_SCHEMA_VERSION = 1


class TemplateService:
    def __init__(self, templates_dir: str | Path):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self) -> list[str]:
        return sorted(p.stem for p in self.templates_dir.glob("*.json"))

    def save_template(self, name: str, metadata: Metadata) -> Path:
        path = self._path_for(name)
        payload = {
            "version": TEMPLATE_SCHEMA_VERSION,
            "name": name,
            "metadata": metadata.to_dict(),
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def load_template(self, name: str) -> Metadata:
        path = self._path_for(name)
        if not path.exists():
            raise FileNotFoundError(f"Template '{name}' tidak ditemukan")
        data = json.loads(path.read_text(encoding="utf-8"))
        return Metadata.from_dict(data.get("metadata", {}))

    def delete_template(self, name: str) -> None:
        path = self._path_for(name)
        if path.exists():
            path.unlink()

    def _path_for(self, name: str) -> Path:
        safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip()
        if not safe_name:
            raise ValueError("Nama template tidak valid")
        return self.templates_dir / f"{safe_name}.json"
