"""Parsing metadata dari nama file berdasarkan pola yang ditentukan user.

Pola ditulis dengan placeholder mirip str.format, misalnya:
    "{artist} - {title}"
    "{track_number}. {artist} - {album} - {title}"

Placeholder yang didukung sesuai field pada core.models.metadata.Metadata.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from core.models.metadata import Metadata

_SUPPORTED_FIELDS = [
    "title", "artist", "album", "album_artist", "genre",
    "year", "track_number", "disc_number", "composer",
]


class FilenameParser:
    """Ubah pola seperti '{artist} - {title}' menjadi regex, lalu match nama file."""

    def __init__(self):
        self._pattern_cache: dict[str, re.Pattern] = {}

    def pattern_to_regex(self, pattern: str) -> re.Pattern:
        if pattern in self._pattern_cache:
            return self._pattern_cache[pattern]

        regex_str = re.escape(pattern)
        for field_name in _SUPPORTED_FIELDS:
            placeholder = re.escape("{" + field_name + "}")
            regex_str = regex_str.replace(placeholder, f"(?P<{field_name}>.+?)")

        # Placeholder tak dikenal tetap dianggap teks literal (sudah di-escape).
        compiled = re.compile("^" + regex_str + "$")
        self._pattern_cache[pattern] = compiled
        return compiled

    def parse(self, file_path: str, pattern: str) -> Optional[Metadata]:
        """Coba parse nama file (tanpa ekstensi) sesuai pola.

        Returns:
            Metadata jika cocok, None jika nama file tidak sesuai pola.
        """
        stem = Path(file_path).stem
        regex = self.pattern_to_regex(pattern)
        match = regex.match(stem)
        if not match:
            return None

        fields = {k: v.strip() for k, v in match.groupdict().items() if v}
        return Metadata.from_dict(fields)

    @staticmethod
    def available_placeholders() -> list[str]:
        return list(_SUPPORTED_FIELDS)
