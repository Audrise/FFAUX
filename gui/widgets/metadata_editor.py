"""
# Widget form for editing the metadata of one or multiple AudioFiles simultaneously.

This widget does not save anything to disk or execute FFmpeg; it merely
reads/writes Metadata objects in memory. The actual saving process
(via the APPLY_METADATA job) is handled by the MainWindow or the calling dialog.

The displayed fields are DYNAMIC, based on the tags actually present in the
selected files (see core/metadata_field_merger.py), rather than a fixed list
of fields. When multiple files are selected and a field has differing values
across them, the field is displayed as read-only, showing a combination of
all those distinct values ​​(separated by " - "); it is ignored during the
save operation if left unchanged, thereby preserving each track's original value.

Two additional capabilities:
- Add a new metadata field (custom tag + value entered by the user) via
  add_empty_field().
- Delete a field (whether a built-in file field or a new, unsaved field) via
  delete_selected_field()—the field currently in focus (clicked or tabbed
  into) is the one deleted. Deleted built-in fields are marked so that,
  upon saving, the tag is actually removed from the file (rather than
  simply being cleared in the form)—see get_deleted_keys().
"""
from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLineEdit, QScrollArea, QVBoxLayout, QWidget

from core.metadata_field_merger import FieldView, build_field_views
from core.models.audio_file import AudioFile
from core.models.metadata import Metadata

class _FocusTrackingLineEdit(QLineEdit):
    """
    A standard QLineEdit, but with an added callback triggered upon gaining focus (when clicked or tabbed into);
    used to identify which field the user has "selected" for deletion.
    """

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

        # Only fields with the SAME VALUE across all selected files are included
        # here (and are editable). Fields that differ between files are displayed
        # as read-only and intentionally not stored in _edits, so that
        # get_metadata() automatically ignores them.
        self._edits: dict[str, QLineEdit] = {}
        self._field_views: list[FieldView] = []

        # widget -> key, for ALL built-in file fields (whether editable or
        # read-only) -- used by delete_selected_field() to determine the key of
        # the currently selected widget, without having to guess based on the label.
        self._edit_to_key: dict[QLineEdit, str] = {}

        # "Add Metadata" rows that haven't been saved yet: list of (key_edit, value_edit).
        # The key is freely typed by the user, so a separate widget is required,
        # rather than a static QLabel like the built-in fields.
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
                    "Different values ​​between selected tracks — cannot be edited. "
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
        key_edit.setPlaceholderText("Tag baru")

        value_edit = _FocusTrackingLineEdit(self._on_field_focused)
        value_edit.setPlaceholderText("Nilai")

        self._new_rows.append((key_edit, value_edit))
        self._form.addRow(key_edit, value_edit)
        key_edit.setFocus()

    def delete_selected_field(self) -> bool:
        """Remove the field that most recently had focus (was clicked by the user).
        Returns True if a field was successfully removed, or False if no
        field had been selected (i.e., the user hadn't clicked any field).

        - New field (unsaved, created via add_empty_field) -> simply
          discarded from the form; no special marking required.
        - Field originating from the file (whether editable or read-only) ->
          the row is removed from the form AND its key is added to
          _deleted_keys, ensuring the tag is actually deleted from the
          file upon saving (rather than just disappearing from the form view).
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
        (with both key and value) added via 'Add Metadata'. Fields that
        differ between tracks (read-only) are intentionally excluded
        to avoid overwriting the original values ​​of individual tracks
        during the merge.
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
        """Apply the template to the current form values ​​(only fields that
        CAN be edited and are populated in the template will overwrite
        the form values). Read-only fields (which differ between tracks)
        are left untouched—this is not yet supported.
        """

        template_data = template_metadata.to_dict()
        for key, edit in self._edits.items():
            if key in template_data:
                edit.setText(str(template_data[key]))
