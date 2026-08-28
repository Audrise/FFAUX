"""
# Widget for displaying and changing cover art.

Handles the image display and file selection only. Cover extraction is done
by core.metadata_service through a callback, keeping FFmpeg out of this widget.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from utils.file_utils import format_file_size

_COVER_SIZE = 220
_IMAGE_FILTER = "Image (*.jpg *.jpeg *.png *.bmp *.webp)"

class CoverArtViewer(QWidget):
    coverPathChanged = Signal(object)  # str/None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path: str | None = None

        self._image_label = QLabel("No cover art")
        self._image_label.setFixedSize(_COVER_SIZE, _COVER_SIZE)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setObjectName("coverArtImage")

        # Resolution info (ex. "1400 x 1400 px") & ukuran file (ex. "312 KB")
        self._info_label = QLabel("")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_label.setObjectName("coverArtInfo")

        self._load_btn = QPushButton("Change Cover...")
        self._extract_btn = QPushButton("Extract from File")
        self._remove_btn = QPushButton("Remove")

        self._load_btn.clicked.connect(self._on_load_clicked)
        self._remove_btn.clicked.connect(self._on_remove_clicked)
        # _extract_btn is intentionally not connected here.
        # MetadataEditorDialog handles the connection because it requires access to MetadataService.

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._load_btn)
        btn_row.addWidget(self._extract_btn)
        btn_row.addWidget(self._remove_btn)

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(self._image_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(4)
        layout.addWidget(self._info_label)
        layout.addSpacing(30)
        layout.addLayout(btn_row)

    @property
    def extract_button(self) -> QPushButton:
        return self._extract_btn

    def load_image(self, path: str | None) -> None:
        self._current_path = path
        if path and Path(path).exists():
            source_pixmap = QPixmap(path)
            scaled = source_pixmap.scaled(
                _COVER_SIZE, _COVER_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._image_label.setPixmap(scaled)

            file_size = format_file_size(Path(path).stat().st_size)
            self._info_label.setText(f"{source_pixmap.width()} x {source_pixmap.height()} px  -  {file_size}")
            self._info_label.setObjectName("coverArtLabel")

        else:
            self._image_label.setText("No cover art")
            self._image_label.setPixmap(QPixmap())
            self._info_label.setText("")

    def current_path(self) -> str | None:
        return self._current_path

    def _on_load_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select cover art", "", _IMAGE_FILTER)
        if path:
            self.load_image(path)
            self.coverPathChanged.emit(path)

    def _on_remove_clicked(self) -> None:
        self.load_image(None)
        self.coverPathChanged.emit(None)
