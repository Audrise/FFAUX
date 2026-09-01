"""
# Builds the fields for the "Edit Metadata" GUI form.

This module has no Qt dependencies, so it can be tested directly with pytest,
just like core/models/metadata.py.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.models.audio_file import AudioFile

# Standard metadata fields with English labels
KNOWN_FIELD_LABELS: dict[str, str] = {
    "title": "Title",
    "artist": "Artist",
    "album": "Album",
    "album_artist": "Album Artist",
    "genre": "Genre",
    "year": "Year",
    "track_number": "Track Number",
    "disc_number": "Disc Number",
    "composer": "Composer",
    "url": "URL",
    "comment": "Comment",
}
_KNOWN_FIELD_ORDER = list(KNOWN_FIELD_LABELS.keys())

# Combined values ​​across different tracks/albums are separated by this.
VALUE_SEPARATOR = " - "

def field_label(field_key: str) -> str:
    # Display label for a field. Unknown fields are used as-is with each word capitalized.
    if field_key in KNOWN_FIELD_LABELS:
        return KNOWN_FIELD_LABELS[field_key]
    return field_key.replace("_", " ").strip().title()

@dataclass
class FieldView:
    key: str
    label: str
    value: str
    editable: bool  # kept for backward-compat; always True now (see is_multi_value)
    per_file_values: list[str]  # this field's original value per file, IN FILE ORDER (not deduplicated)
    is_multi_value: bool  # True if the selected tracks originally had differing values

def build_field_views(audio_files: list[AudioFile]) -> list[FieldView]:
    if not audio_files:
        return []

    per_file_dicts = [af.metadata.to_dict() for af in audio_files]

    ordered_keys: list[str] = []
    seen_keys: set[str] = set()

    for key in _KNOWN_FIELD_ORDER:
        if any(key in d for d in per_file_dicts):
            ordered_keys.append(key)
            seen_keys.add(key)

    for d in per_file_dicts:
        for key in d:
            if key == "cover_art_path" or key in seen_keys:
                continue
            ordered_keys.append(key)
            seen_keys.add(key)

    views: list[FieldView] = []
    for key in ordered_keys:
        values = [str(d.get(key, "") or "") for d in per_file_dicts]
        is_multi = len(set(values)) > 1
        # Positional, one segment per file (NOT deduplicated) -- so an edit
        # to segment i can be traced back to exactly file i on save.
        display_value = VALUE_SEPARATOR.join(values) if is_multi else values[0]

        views.append(
            FieldView(
                key=key,
                label=field_label(key),
                value=display_value,
                editable=True,
                per_file_values=values,
                is_multi_value=is_multi,
            )
        )
    return views