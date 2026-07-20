"""Widget untuk menampilkan & mengganti cover art.

Widget ini hanya urusan visual + memilih file gambar. Ekstraksi cover
dari file audio (butuh FFmpeg) didelegasikan ke core.metadata_service,
dipanggil dari luar (dialog) lewat callback, bukan dari widget ini
langsung -- supaya widget tetap tidak tahu apa-apa soal FFmpeg.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from utils.file_utils import format_file_size

_COVER_SIZE = 180
_IMAGE_FILTER = "Gambar (*.jpg *.jpeg *.png *.bmp *.webp)"


class CoverArtViewer(QWidget):
    """Emit coverPathChanged(str | None) setiap kali cover diganti/dihapus.

    None berarti "hapus cover art dari file output".
        """

    coverPathChanged = Signal(object)  # str atau None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path: str | None = None

        self._image_label = QLabel("Tidak ada cover art")
        self._image_label.setFixedSize(_COVER_SIZE, _COVER_SIZE)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("border: 1px solid palette(white); border-radius: 4px; color: palette(mid);")

        # Info resolusi (mis. "1400 x 1400 px") & ukuran file (mis. "312 KB")
        # cover art yang sedang ditampilkan, di bawah gambarnya.
        self._info_label = QLabel("")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_label.setStyleSheet("color: palette(white); font-size: 11px;")

        self._load_btn = QPushButton("Ganti Gambar...")
        self._extract_btn = QPushButton("Ekstrak dari File")
        self._remove_btn = QPushButton("Hapus")

        self._load_btn.clicked.connect(self._on_load_clicked)
        self._remove_btn.clicked.connect(self._on_remove_clicked)
        # _extract_btn sengaja tidak di-connect di sini; MetadataEditorDialog
        # yang menyambungkannya karena butuh akses ke MetadataService.

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._load_btn)
        btn_row.addWidget(self._extract_btn)
        btn_row.addWidget(self._remove_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._image_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._info_label)
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
            self._info_label.setText(
                f"{source_pixmap.width()} x {source_pixmap.height()} px  -  {file_size}"
            )
        else:
            self._image_label.setText("Tidak ada cover art")
            self._image_label.setPixmap(QPixmap())
            self._info_label.setText("")

    def current_path(self) -> str | None:
        return self._current_path

    def _on_load_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Pilih gambar cover", "", _IMAGE_FILTER)
        if path:
            self.load_image(path)
            self.coverPathChanged.emit(path)

    def _on_remove_clicked(self) -> None:
        self.load_image(None)
        self.coverPathChanged.emit(None)
