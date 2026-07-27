"""
# Widget form for editing the metadata of one or multiple AudioFiles simultaneously.

The displayed fields are DYNAMIC, based on the tags actually present in the
selected files (see core/metadata_field_merger.py), rather than a fixed list
of fields. When multiple files are selected and a field has differing values
across them, the field is displayed as read-only, showing a combination of
all those distinct values ​​(separated by " - "); it is ignored during the
save operation if left unchanged, thereby preserving each track's original value.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLineEdit, QScrollArea, QVBoxLayout, QWidget

from core.metadata_field_merger import FieldView, build_field_views
from core.models.audio_file import AudioFile
from core.models.metadata import Metadata

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

    def load_metadata(self, metadata: Metadata) -> None:
        """Backward-compatible: return a single Metadata field.
        Also used internally by load_for_files() for the case of a single
        selected file.
        """

        dummy = AudioFile(path="")
        dummy.metadata = metadata
        self.load_for_files([dummy])

    def load_for_files(self, audio_files: list[AudioFile]) -> None:
        # Rebuild the form based on dynamic fields from the selected file.
        self._clear_form()
        self._field_views = build_field_views(audio_files)
        self._original_values: dict[str, str] = {}

        for view in self._field_views:
            edit = _FocusTrackingLineEdit(self._on_field_focused)
            edit.setText(view.value)
            if not view.editable:
                edit.setReadOnly(True)
                edit.setToolTip(
                    "Different values ​​between selected tracks cannot be edited. "
                    "If saved without modification, each track retains its respective value.."
                )

            else:
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
        """Add a new empty row below the last field: one field for the
        tag name (user-entered), and one for its value. It only
        becomes a valid tag if both are filled in and the dialog is saved.
        """

        key_edit = _FocusTrackingLineEdit(self._on_field_focused)
        key_edit.setPlaceholderText("New Tag")

        value_edit = _FocusTrackingLineEdit(self._on_field_focused)
        value_edit.setPlaceholderText("Value")

        self._new_rows.append((key_edit, value_edit))
        self._form.addRow(key_edit, value_edit)
        key_edit.setFocus()

    def delete_selected_field(self) -> bool:
        """Remove the field that most recently had focus (was clicked by the user).
        Returns True if a field was successfully removed, or False if no
        field had been selected (i.e., the user hadn't clicked any field).
        """

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

    # ------------------------------------------------------------------
    def get_metadata(self) -> Metadata:
        """Return metadata from editable fields (where values ​​are identical
        across all selected files) PLUS new, fully populated fields
        (with both key and value) added via 'Add Metadata'.
        """

        values = {name: edit.text().strip() or None for name, edit in self._edits.items()}
        for key_edit, value_edit in self._new_rows:
            key = key_edit.text().strip()
            value = value_edit.text().strip()
            if key and value:
                values[key] = value
        return Metadata.from_dict({k: v for k, v in values.items() if v is not None})

    def get_deleted_keys(self) -> set[str]:
        """Key tag explicitly removed by the user via the 'Remove Metadata' button
        (a field inherent to the file, not a new field that hasn't been saved yet).
        """

        return set(self._deleted_keys)

    def apply_template(self, template_metadata: Metadata) -> None:
        """Read-only fields (which differ between tracks)
        are left untouched—this is not yet supported.
        """
        template_data = template_metadata.to_dict()
        for key, edit in self._edits.items():
            if key in template_data:
                edit.setText(str(template_data[key]))
