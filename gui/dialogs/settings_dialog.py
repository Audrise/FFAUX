"""Dialog konfigurasi aplikasi. Membaca/menulis lewat ConfigService,
tidak pernah menyentuh file JSON secara langsung.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.config_service import ConfigService


class SettingsDialog(QDialog):
    def __init__(self, config_service: ConfigService, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pengaturan AudriseFFTool")
        self._config_service = config_service
        config = config_service.config

        self._ffmpeg_edit = self._make_path_field(config.ffmpeg_path)
        self._ffprobe_edit = self._make_path_field(config.ffprobe_path)
        self._output_dir_edit = self._make_path_field(config.output_directory, is_dir=True)

        self._parallel_spin = QSpinBox()
        self._parallel_spin.setRange(1, 8)
        self._parallel_spin.setValue(config.max_parallel_jobs)

        form = QFormLayout()
        form.addRow("Path FFmpeg:", self._wrap_with_browse(self._ffmpeg_edit, is_dir=False))
        form.addRow("Path FFprobe:", self._wrap_with_browse(self._ffprobe_edit, is_dir=False))
        form.addRow("Folder output default:", self._wrap_with_browse(self._output_dir_edit, is_dir=True))
        form.addRow("Job paralel maksimum:", self._parallel_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _make_path_field(self, value: str, is_dir: bool = False) -> QLineEdit:
        edit = QLineEdit(value)
        return edit

    def _wrap_with_browse(self, edit: QLineEdit, is_dir: bool) -> QHBoxLayout:
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(32)

        def on_browse():
            if is_dir:
                path = QFileDialog.getExistingDirectory(self, "Pilih folder", edit.text())
            else:
                path, _ = QFileDialog.getOpenFileName(self, "Pilih file", edit.text())
            if path:
                edit.setText(path)

        browse_btn.clicked.connect(on_browse)

        row = QHBoxLayout()
        row.addWidget(edit)
        row.addWidget(browse_btn)
        return row

    def _on_save(self) -> None:
        cfg = self._config_service
        cfg.set("ffmpeg_path", self._ffmpeg_edit.text())
        cfg.set("ffprobe_path", self._ffprobe_edit.text())
        cfg.set("output_directory", self._output_dir_edit.text())
        cfg.set("max_parallel_jobs", self._parallel_spin.value())
        cfg.save()
        self.accept()
