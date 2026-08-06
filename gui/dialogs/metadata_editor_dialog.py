"""
# Dialog for editing metadata & cover art for one OR MULTIPLE AudioFiles simultaneously (multi-select).

This dialog integrates the MetadataEditor, CoverArtViewer, and template controls,
then returns the edited results to the caller via the get_result() method.
The dialog does NOT execute FFmpeg directly; instead, the MainWindow creates
a Job (APPLY_METADATA / SET_COVER) based on the results and sends it to the
JobManager, adhering to the rule that "GUI actions always go through the JobManager."
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from core.metadata_service import MetadataService
from core.models.audio_file import AudioFile
from core.models.metadata import Metadata
from core.template_service import TemplateService
from gui.widgets.cover_art_viewer import CoverArtViewer
from gui.widgets.metadata_editor import MetadataEditor

class MetadataEditorDialog(QDialog):
    def __init__(
        self,
        audio_files: AudioFile | list[AudioFile],
        metadata_service: MetadataService,
        template_service: TemplateService,
        parent=None,
    ):
        super().__init__(parent)

        self._audio_files: list[AudioFile] = (
            [audio_files] if isinstance(audio_files, AudioFile) else list(audio_files)
        )
        self._primary_file = self._audio_files[0]

        if len(self._audio_files) > 1:
            self.setWindowTitle(f"Edit Metadata - {len(self._audio_files)} Selected Files")
        else:
            self.setWindowTitle(f"Edit Metadata - {self._primary_file.filename}")
        self.resize(760, 480)

        self._metadata_service = metadata_service
        self._template_service = template_service
        self._cover_changed = False  # True if user changing/deleting the cover

        self._metadata_editor = MetadataEditor()
        self._metadata_editor.load_for_files(self._audio_files)

        # The displayed and editable cover art always belongs to the first file in the selected sequence
        self._cover_viewer = CoverArtViewer()
        if self._primary_file.metadata.cover_art_path == "<embedded>":
            self._extract_and_show_cover()
        self._cover_viewer.extract_button.clicked.connect(self._on_extract_cover_clicked)
        self._cover_viewer.coverPathChanged.connect(self._on_cover_path_changed)

        template_row = self._build_template_row()
        field_buttons_row = self._build_field_buttons_row()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        top_row = QHBoxLayout()
        top_row.addWidget(self._metadata_editor, stretch=2)
        top_row.addWidget(self._cover_viewer, stretch=1)

        layout = QVBoxLayout(self)
        layout.addLayout(template_row)
        layout.addLayout(top_row)
        layout.addLayout(field_buttons_row)
        layout.addWidget(buttons)

    # Template: select + preview content + apply/save
    def _build_template_row(self) -> QHBoxLayout:
        self._template_combo = QComboBox()
        self._template_combo.addItems(self._template_service.list_templates())

        preview_btn = QPushButton("Preview Metadata")
        apply_btn = QPushButton("Apply Template")
        save_btn = QPushButton("Save Template as...")
        preview_btn.clicked.connect(self._on_preview_metadata_clicked)
        apply_btn.clicked.connect(self._on_apply_template_clicked)
        save_btn.clicked.connect(self._on_save_template_clicked)

        row = QHBoxLayout()
        row.addWidget(QLabel("Template:"))
        row.addWidget(self._template_combo, stretch=1)
        row.addWidget(preview_btn)
        row.addWidget(apply_btn)
        row.addWidget(save_btn)
        return row

    def _on_preview_metadata_clicked(self) -> None:
        """Open a new window displaying the content of the template currently
        selected in the "Template" combo box—replacing the old preview
        panel that appeared automatically inline below the Template row.
        """
        name = self._template_combo.currentText()
        if not name:
            QMessageBox.information(self, "Select Template", "Select a template in the dropdown first.")
            return
        try:
            template_metadata = self._template_service.load_template(name)
        except FileNotFoundError as exc:
            QMessageBox.warning(self, "Template not found!", str(exc))
            return

        data = template_metadata.to_dict()
        if data:
            preview_text = "\n".join(f"{key} - {value}" for key, value in data.items())
        else:
            preview_text = "(This template is empty.)"

        preview_window = QDialog(self)
        preview_window.setWindowTitle(f"Preview Metadata - {name}")
        preview_window.resize(480, 320)

        text_area = QPlainTextEdit()
        text_area.setReadOnly(True)
        text_area.setPlainText(preview_text)
        text_area.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")

        close_btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn.rejected.connect(preview_window.reject)
        close_btn.accepted.connect(preview_window.accept)

        preview_layout = QVBoxLayout(preview_window)
        preview_layout.addWidget(text_area)
        preview_layout.addWidget(close_btn)

        preview_window.exec()

    def _on_apply_template_clicked(self) -> None:
        name = self._template_combo.currentText()
        if not name:
            return
        try:
            template_metadata = self._template_service.load_template(name)
        except FileNotFoundError as exc:
            QMessageBox.warning(self, "Template not found", str(exc))
            return
        self._metadata_editor.apply_template(template_metadata)
        QMessageBox.information(self, "Template Applied", f'Template "{name}" has been applied.')

    def _on_save_template_clicked(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Template", "Template name:")
        if not ok or not name.strip():
            return
        self._template_service.save_template(name.strip(), self._metadata_editor.get_metadata())
        self._template_combo.clear()
        self._template_combo.addItems(self._template_service.list_templates())
        QMessageBox.information(self, "Template Saved", f'Template "{name}" has been saved.')

    # Add / Delete metadata field
    def _build_field_buttons_row(self) -> QHBoxLayout:
        add_btn = QPushButton("Add Metadata")
        delete_btn = QPushButton("Delete Selected Metadata")
        add_btn.clicked.connect(self._metadata_editor.add_empty_field)
        delete_btn.clicked.connect(self._on_delete_field_clicked)

        row = QHBoxLayout()
        row.addWidget(add_btn)
        row.addWidget(delete_btn)
        row.addStretch(1)
        return row

    def _on_add_field_clicked(self) -> None:
        self._metadata_editor.add_empty_field()
        QMessageBox.information(self, "Metadata Added", "A new empty metadata field has been added.")

    def _on_delete_field_clicked(self) -> None:
        if not self._metadata_editor.delete_selected_field():
            QMessageBox.information(
                self,
                "Select field",
                "First, click the metadata field you want to delete (focus on the column), then press this button again.",
            )
        else:
            QMessageBox.information(self, "Metadata Deleted", "The selected metadata field has been deleted.")

    # Cover art
    def _on_extract_cover_clicked(self) -> None:
        if not self._extract_and_show_cover():
            QMessageBox.information(self, "No cover", "This file doesn't have embedded cover art.")
        else:
            QMessageBox.information(self, "Cover Extracted", "Cover art has been extracted from the file.")

    def _extract_and_show_cover(self) -> bool:
        """Extract the embedded cover art (from the first selected file) and
        display it in the viewer. Return False if the file does not have
        cover art (used by both auto-extraction upon opening the dialog
        and the "Extract from File" button).
        """
        temp_dir = Path(tempfile.gettempdir()) / "fftool_covers"
        path = self._metadata_service.extract_cover_art_sync(self._primary_file, str(temp_dir))
        if path:
            self._cover_viewer.load_image(path)
            return True
        return False

    def _on_cover_path_changed(self, path) -> None:
        self._cover_changed = True

    def get_result(self) -> tuple[Metadata, str | None, bool, set[str], bool]:
        # Returns (new_metadata, new_cover_path_or_None, cover_changed, deleted_keys).
        return (
            self._metadata_editor.get_metadata(),
            self._cover_viewer.current_path(),
            self._cover_changed,
            self._metadata_editor.get_deleted_keys(),
            self._metadata_editor.has_changes(),
        )
