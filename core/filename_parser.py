"""
# Parse metadata from the filename based on a user-defined pattern.

The pattern uses placeholders similar to `str.format`, for example:
    "{artist} - {title}"
    "{track_number}. {artist} - {album} - {title}"

Supported placeholders correspond to the fields in `core.models.metadata.Metadata`.
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
    # Convert a pattern like '{artist} - {title}' into a regex, then match the filename.

    def __init__(self):
        self._pattern_cache: dict[str, re.Pattern] = {}

    def pattern_to_regex(self, pattern: str) -> re.Pattern:
        if pattern in self._pattern_cache:
            return self._pattern_cache[pattern]

        regex_str = re.escape(pattern)
        for field_name in _SUPPORTED_FIELDS:
            placeholder = re.escape("{" + field_name + "}")
            regex_str = regex_str.replace(placeholder, f"(?P<{field_name}>.+?)")

        compiled = re.compile("^" + regex_str + "$")
        self._pattern_cache[pattern] = compiled
        return compiled

    def parse(self, file_path: str, pattern: str) -> Optional[Metadata]:
        """
        Try to parse the file name (without extension) according to the pattern.
        Returns:
            Metadata if it matches, None if the file name doesn't match the pattern.
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
