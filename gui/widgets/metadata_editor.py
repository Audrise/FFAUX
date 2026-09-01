"""
# Widget form for editing metadata for one or more AudioFiles.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLineEdit, QScrollArea, QVBoxLayout, QWidget

from core.metadata_field_merger import VALUE_SEPARATOR, FieldView, build_field_views
from core.models.audio_file import AudioFile
from core.models.metadata import Metadata
from utils.logger import get_logger

logger = get_logger("gui.widgets.metadata_editor")

class _FocusTrackingLineEdit(QLineEdit):
    def __init__(self, on_focus, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_focus = on_focus

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._on_focus(self)

class MetadataEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._form_container = QWidget()
        self._form = QFormLayout(self._form_container)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._form_container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

        self._edits: dict[str, QLineEdit] = {}
        self._field_views: list[FieldView] = []

        self._edit_to_key: dict[QLineEdit, str] = {}
        self._new_rows: list[tuple[QLineEdit, QLineEdit]] = []

        self._deleted_keys: set[str] = set()
        self._selected_edit: QLineEdit | None = None
        self._audio_files: list[AudioFile] = []

    def load_metadata(self, metadata: Metadata) -> None:
        # Keep a single Metadata field for backward compatibility and single-file loading.
        dummy = AudioFile(path="")
        dummy.metadata = metadata
        self.load_for_files([dummy])

    def load_for_files(self, audio_files: list[AudioFile]) -> None:
        # Rebuild the form based on dynamic fields from the selected file.
        self._clear_form()
        self._audio_files = list(audio_files)
        self._field_views = build_field_views(audio_files)
        self._original_values: dict[str, str] = {}

        for view in self._field_views:
            edit = _FocusTrackingLineEdit(self._on_field_focused)
            edit.setText(view.value)
            if view.is_multi_value:
                edit.setToolTip(
                    "Values differ across the selected tracks, shown combined "
                    "and separated by \" - \" in the same order as the selected "
                    "tracks. Edit a single segment to change only that track, "
                    "or replace the whole thing with one value to apply it to "
                    "every selected track."
                )

            self._edits[view.key] = edit
            self._original_values[view.key] = view.value
            self._edit_to_key[edit] = view.key
            self._form.addRow(f"{view.label}:", edit)

    def has_changes(self) -> bool:
        for key, edit in self._edits.items():
            if edit.text().strip() != self._original_values.get(key, ""):
                return True

        for key_edit, value_edit in self._new_rows:
            if key_edit.text().strip() and value_edit.text().strip():
                return True
        return bool(self._deleted_keys)

    def add_empty_field(self) -> None:
        # Add an empty tag row; it only becomes valid after both key and value are filled and saved.
        key_edit = _FocusTrackingLineEdit(self._on_field_focused)
        key_edit.setPlaceholderText("New Tag")

        value_edit = _FocusTrackingLineEdit(self._on_field_focused)
        value_edit.setPlaceholderText("Value")

        self._new_rows.append((key_edit, value_edit))
        self._form.addRow(key_edit, value_edit)
        key_edit.setFocus()

    def delete_selected_field(self) -> bool:
        # Remove the last focused field and return True if successful.
        if self._selected_edit is None:
            return False

        # Case 1: A new field that has not yet been saved.
        for key_edit, value_edit in list(self._new_rows):
            if self._selected_edit in (key_edit, value_edit):
                self._form.removeRow(key_edit)
                self._new_rows.remove((key_edit, value_edit))
                self._selected_edit = None
                return True

        # Case 2: Built-in file field (editable or read-only).
        key = self._edit_to_key.get(self._selected_edit)
        if key is not None:
            self._form.removeRow(self._selected_edit)
            self._edits.pop(key, None)
            self._edit_to_key.pop(self._selected_edit, None)
            self._deleted_keys.add(key)
            self._selected_edit = None
            return True

        return False

    def _on_field_focused(self, edit: QLineEdit) -> None:
        self._selected_edit = edit

    def _clear_form(self) -> None:
        while self._form.rowCount():
            self._form.removeRow(0)
        self._edits.clear()
        self._field_views = []
        self._edit_to_key.clear()
        self._new_rows.clear()
        self._deleted_keys.clear()
        self._selected_edit = None

    def get_metadata(self) -> Metadata:
        view_by_key = {v.key: v for v in self._field_views}
        values = {}
        for name, edit in self._edits.items():
            view = view_by_key.get(name)
            if view is not None and view.is_multi_value:
                continue
            values[name] = edit.text().strip() or None

        for key_edit, value_edit in self._new_rows:
            key = key_edit.text().strip()
            value = value_edit.text().strip()
            if key and value:
                values[key] = value
        return Metadata.from_dict({k: v for k, v in values.items() if v is not None})

    def get_per_file_overrides(self) -> dict[str, dict[str, str]]:
        # Returns {audio_file.id: {field_key: new_value}}
        overrides: dict[str, dict[str, str]] = {}
        view_by_key = {v.key: v for v in self._field_views}

        for key, edit in self._edits.items():
            view = view_by_key.get(key)
            if view is None or not view.is_multi_value:
                continue

            current_text = edit.text().strip()
            if current_text == view.value:
                continue

            segments = current_text.split(VALUE_SEPARATOR)

            if len(segments) == len(self._audio_files):
                for audio_file, original, new_value in zip(
                    self._audio_files, view.per_file_values, segments
                ):
                    new_value = new_value.strip()
                    if new_value != original:
                        overrides.setdefault(audio_file.id, {})[key] = new_value

            elif len(segments) == 1:
                new_value = segments[0].strip()
                for audio_file, original in zip(self._audio_files, view.per_file_values):
                    if new_value != original:
                        overrides.setdefault(audio_file.id, {})[key] = new_value

            else:
                logger.warning(f"Ignoring edit to {key} {len(segments)} {len(self._audio_files)}")

        return overrides

    def get_deleted_keys(self) -> set[str]:
        return set(self._deleted_keys)

    def apply_template(self, template_metadata: Metadata) -> None:
        # Read-only fields (which differ between tracks) are left untouched—this is not yet supported.
        template_data = template_metadata.to_dict()
        for key, edit in self._edits.items():
            if key in template_data:
                edit.setText(str(template_data[key]))
