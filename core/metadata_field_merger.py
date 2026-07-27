"""
# A pure-Python utility for constructing the list of fields for the "Edit Metadata" form.

This module intentionally has no Qt dependencies (using only dataclasses and
dicts) so that its logic can be tested directly with pytest, consistent with
core/models/metadata.py.
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
    """Display label for a field.
    Extra or unrecognized fields (additional tags such as ISRC, publisher) are used
    as-is, with the first letter of each word capitalized.
    """
    if field_key in KNOWN_FIELD_LABELS:
        return KNOWN_FIELD_LABELS[field_key]
    return field_key.replace("_", " ").strip().title()

@dataclass
class FieldView:
    key: str
    label: str
    value: str
    editable: bool  # False if the values ​​differ across selected tracks

def build_field_views(audio_files: list[AudioFile]) -> list[FieldView]:
    # Build a FieldView list for one or multiple selected AudioFiles.
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
        distinct_values = list(dict.fromkeys(values))  # unik, urutan kemunculan pertama
        if len(distinct_values) <= 1:
            views.append(
                FieldView(
                    key=key,
                    label=field_label(key),
                    value=distinct_values[0] if distinct_values else "",
                    editable=True,
                )
            )
        else:
            views.append(
                FieldView(
                    key=key,
                    label=field_label(key),
                    value=VALUE_SEPARATOR.join(distinct_values),
                    editable=False,
                )
            )
    return views
