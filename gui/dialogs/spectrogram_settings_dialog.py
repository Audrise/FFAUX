"""
# Spectrogram generation settings dialog.

Shown before a GENERATE_SPECTROGRAM job is enqueued (right-click on the
track table, or Edit > Generate Spectrogram...). Analogous in structure
to ConversionSettingsDialog, but much smaller: only output naming,
image resolution, and output folder -- no audio-format-specific options.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

RESOLUTIONS = ["640x480", "1280x720", "1920x1080", "2560x1440", "3840x2160"]
_DEFAULT_RESOLUTION = "1920x1080"

class SpectrogramSettingsDialog(QDialog):
    def __init__(self, default_output_dir: str = "", default_spectrogram_suffix: str = "" ,source_filename: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate Spectrogram")
        self.setMinimumSize(420, 200)
        self._spectrogram_suffix = default_spectrogram_suffix

        self._output_name_edit = QLineEdit()
        placeholder = f"{Path(source_filename).stem}{self._spectrogram_suffix}" if source_filename else "_spec"
        self._output_name_edit.setPlaceholderText(placeholder)

        self._resolution_combo = QComboBox()
        for res in RESOLUTIONS:
            self._resolution_combo.addItem(res, userData=res)
        self._resolution_combo.setCurrentIndex(RESOLUTIONS.index(_DEFAULT_RESOLUTION))

        self._output_dir_edit = QLineEdit()
        self._output_dir_edit.setPlaceholderText(default_output_dir)

        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(32)
        browse_btn.clicked.connect(self._on_browse_output_dir)
        output_dir_row = QHBoxLayout()
        output_dir_row.addWidget(self._output_dir_edit)
        output_dir_row.addWidget(browse_btn)

        form = QFormLayout()
        form.addRow("Output name:", self._output_name_edit)
        form.addRow("Resolution:", self._resolution_combo)
        form.addRow("Output path:", output_dir_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._generate_btn = buttons.addButton("Generate", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _on_browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select the output folder", self._output_dir_edit.text())
        if path:
            self._output_dir_edit.setText(path)

    def output_name(self) -> str:
        return self._output_name_edit.text().strip()

    def resolution(self) -> str:
        return self._resolution_combo.currentData()

    def output_dir(self) -> str:
        return self._output_dir_edit.text().strip()