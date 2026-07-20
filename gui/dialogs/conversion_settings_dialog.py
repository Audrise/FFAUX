"""Dialog pengaturan konversi audio -- WAJIB muncul setiap kali user
menekan Convert (Ctrl+R / menu / klik-kanan), SATU KALI untuk mewakili
seluruh track yang dipilih (bukan per-track, berapa pun jumlah track-nya).
Lihat MainWindow._on_process_clicked untuk alur pemanggilannya.

Analog dengan MetadataEditorDialog tapi untuk parameter konversi teknis:
format output, sample rate, bit depth, bitrate, resampler SOXR + precision
(khusus FLAC/WAV), compression level (khusus FLAC), dan custom output
folder.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.models.conversion_settings import (
    LOSSLESS_FORMATS,
    SOXR_FORMATS,
    STANDARD_SAMPLE_RATES,
    ConversionSettings,
    OutputFormat,
)

_FORMAT_LABELS = {
    OutputFormat.MP3: "MP3",
    OutputFormat.AAC: "AAC",
    OutputFormat.FLAC: "FLAC",
    OutputFormat.WAV: "WAV",
    OutputFormat.OGG: "OGG (Vorbis)",
    OutputFormat.OPUS: "Opus",
    OutputFormat.ALAC: "ALAC",
}


class ConversionSettingsDialog(QDialog):
    def __init__(self, current_settings: ConversionSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pengaturan Konversi")
        self.resize(440, 320)

        # --- Format output ---
        self._format_combo = QComboBox()
        for fmt in OutputFormat:
            self._format_combo.addItem(_FORMAT_LABELS[fmt], userData=fmt)
        self._format_combo.setCurrentIndex(list(OutputFormat).index(current_settings.output_format))

        # --- Sample rate: daftar standar 44.1kHz - 192kHz, bukan rentang
        # bebas (nilai non-standar tidak bermakna secara audio engineering). ---
        self._sample_rate_combo = QComboBox()
        for hz in STANDARD_SAMPLE_RATES:
            self._sample_rate_combo.addItem(f"{hz} Hz", userData=hz)
        if current_settings.sample_rate_hz in STANDARD_SAMPLE_RATES:
            self._sample_rate_combo.setCurrentIndex(
                STANDARD_SAMPLE_RATES.index(current_settings.sample_rate_hz)
            )

        # --- Bit depth (lossless: FLAC/WAV/ALAC) ---
        self._bit_depth_combo = QComboBox()
        for depth in (16, 24, 32):
            self._bit_depth_combo.addItem(f"{depth}-bit", userData=depth)
        self._bit_depth_combo.setCurrentIndex((16, 24, 32).index(current_settings.bit_depth))

        # --- Bitrate kbps (HANYA untuk format selain FLAC/WAV -- bitrate
        # FLAC bersifat variable/tergantung compression level, bukan
        # static seperti MP3/AAC/OGG/Opus). ---
        self._bitrate_spin = QSpinBox()
        self._bitrate_spin.setRange(32, 320)
        self._bitrate_spin.setSuffix(" kbps")
        self._bitrate_spin.setValue(current_settings.bitrate_kbps)

        # --- SOXR: HANYA relevan untuk FLAC & WAV, dan untuk keduanya
        # SELALU aktif (bukan pilihan) -- lihat SOXR_FORMATS di model.
        # Baris ini disembunyikan total untuk format lain, bukan cuma
        # di-nonaktifkan. ---

        # self._soxr_info_label = QLabel("SOXR (wajib aktif untuk FLAC/WAV)")
        # self._soxr_info_label.setStyleSheet("color: palette(mid);")

        self._soxr_precision_spin = QSpinBox()
        self._soxr_precision_spin.setRange(1, 33)
        self._soxr_precision_spin.setValue(current_settings.soxr_precision)

        # --- FLAC compression level (HANYA FLAC, WAV tidak punya opsi ini) ---
        self._flac_compression_spin = QSpinBox()
        self._flac_compression_spin.setRange(0, 12)
        self._flac_compression_spin.setValue(current_settings.flac_compression_level)

        # --- Custom output folder (opsional) ---
        self._output_dir_edit = QLineEdit(current_settings.custom_output_dir)
        self._output_dir_edit.setPlaceholderText("Kosongkan untuk pakai folder default")
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(32)
        browse_btn.clicked.connect(self._on_browse_output_dir)
        output_dir_row = QHBoxLayout()
        output_dir_row.addWidget(self._output_dir_edit)
        output_dir_row.addWidget(browse_btn)

        self._form = QFormLayout()
        self._form.addRow("Format Output:", self._format_combo)
        self._form.addRow("Sample Rate:", self._sample_rate_combo)
        self._form.addRow("Bit Depth:", self._bit_depth_combo)
        self._form.addRow("Bitrate:", self._bitrate_spin)
        # self._form.addRow(self._soxr_info_label)
        self._form.addRow("SOXR Precision (1-33):", self._soxr_precision_spin)
        self._form.addRow("FLAC Compression Level (0-12):", self._flac_compression_spin)
        self._form.addRow("Custom Output Folder:", output_dir_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(self._form)
        layout.addWidget(buttons)

        self._format_combo.currentIndexChanged.connect(self._update_field_states)
        self._update_field_states()

    # ------------------------------------------------------------------
    def _current_format(self) -> OutputFormat:
        # PySide6 kadang "meratakan" nilai str-Enum (OutputFormat mewarisi
        # str) jadi str biasa saat lewat QVariant (userData() combo box).
        # OutputFormat(data) aman dipanggil baik data-nya sudah OutputFormat
        # maupun cuma str mentahnya -- Enum(value) selalu rekonstruksi ulang
        # member yang benar.
        data = self._format_combo.currentData()
        return OutputFormat(data)

    def _set_row_visible(self, field_widget, visible: bool) -> None:
        field_widget.setVisible(visible)
        label = self._form.labelForField(field_widget)
        if label is not None:
            label.setVisible(visible)

    def _update_field_states(self) -> None:
        fmt = self._current_format()
        is_lossless = fmt in LOSSLESS_FORMATS  # FLAC, WAV, ALAC -> no bitrate
        is_soxr_format = fmt in SOXR_FORMATS  # FLAC, WAV -> SOXR wajib aktif
        is_flac = fmt == OutputFormat.FLAC

        self._set_row_visible(self._bit_depth_combo, is_lossless)
        self._set_row_visible(self._bitrate_spin, not is_lossless)

        # SOXR (+ precision) cuma ditampilkan untuk FLAC/WAV -- bukan
        # opsi yang bisa dipilih untuk format lain sama sekali.
        # self._soxr_info_label.setVisible(is_soxr_format)
        self._set_row_visible(self._soxr_precision_spin, is_soxr_format)

        self._set_row_visible(self._flac_compression_spin, is_flac)

    def _on_browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Pilih folder output", self._output_dir_edit.text()
        )
        if path:
            self._output_dir_edit.setText(path)

    def get_settings(self) -> ConversionSettings:
        return ConversionSettings(
            output_format=self._current_format(),
            sample_rate_hz=self._sample_rate_combo.currentData(),
            bit_depth=self._bit_depth_combo.currentData(),
            bitrate_kbps=self._bitrate_spin.value(),
            soxr_precision=self._soxr_precision_spin.value(),
            flac_compression_level=self._flac_compression_spin.value(),
            custom_output_dir=self._output_dir_edit.text().strip(),
        )
