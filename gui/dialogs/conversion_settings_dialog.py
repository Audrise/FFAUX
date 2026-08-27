"""
# Audio conversion settings dialog.

Similar to MetadataEditorDialog, but for conversion options such as output
format, sample rate, bit depth, bitrate, SOXR resampling, compression level,
and output folder.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
    def __init__(self, current_settings: ConversionSettings, default_output_dir: str = "", output_suffix: str = "" ,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Convert Settings")
        self.setMinimumSize(480, 330)

        # Format output
        self._format_combo = QComboBox()
        for fmt in OutputFormat:
            self._format_combo.addItem(_FORMAT_LABELS[fmt], userData=fmt)
        self._format_combo.setCurrentIndex(list(OutputFormat).index(current_settings.output_format))

        self._sample_rate_combo = QComboBox()
        for hz in STANDARD_SAMPLE_RATES:
            self._sample_rate_combo.addItem(f"{hz} Hz", userData=hz)
        if current_settings.sample_rate_hz in STANDARD_SAMPLE_RATES:
            self._sample_rate_combo.setCurrentIndex(
                STANDARD_SAMPLE_RATES.index(current_settings.sample_rate_hz)
            )

        # Bit depth for lossless
        self._bit_depth_combo = QComboBox()
        for depth in (16, 24, 32):
            self._bit_depth_combo.addItem(f"{depth}-bit", userData=depth)
        self._bit_depth_combo.setCurrentIndex((16, 24, 32).index(current_settings.bit_depth))

        # Bitrate in kbps (ONLY for formats other than FLAC/WAV)
        self._bitrate_spin = QSpinBox()
        self._bitrate_spin.setRange(32, 320)
        self._bitrate_spin.setSuffix(" kbps")
        self._bitrate_spin.setValue(current_settings.bitrate_kbps)

        # FLAC compression level
        self._flac_compression_spin = QSpinBox()
        self._flac_compression_spin.setRange(0, 12)
        self._flac_compression_spin.setValue(current_settings.flac_compression_level)

        # SOXR: ONLY for FLAC & WAV
        self._use_soxr_check = QCheckBox("Use SOX Resampler for FLAC/WAV")
        self._use_soxr_check.setChecked(current_settings.use_soxr)

        self._soxr_precision_spin = QSpinBox()
        self._soxr_precision_spin.setRange(1, 33)
        self._soxr_precision_spin.setValue(current_settings.soxr_precision)

        # Custom output folder (Optional)
        self._output_dir_edit = QLineEdit(current_settings.custom_output_dir)
        self._output_dir_edit.setPlaceholderText(default_output_dir)

        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(32)
        browse_btn.clicked.connect(self._on_browse_output_dir)
        output_dir_row = QHBoxLayout()
        output_dir_row.addWidget(self._output_dir_edit)
        output_dir_row.addWidget(browse_btn)

        self._output_suffix_edit = QLineEdit(current_settings.custom_output_suffix)
        self._output_suffix_edit.setPlaceholderText(output_suffix)

        self._form = QFormLayout()
        self._form.addRow("Output Audio Format:", self._format_combo)
        self._form.addRow("Sampling Rate:", self._sample_rate_combo)
        self._form.addRow("Bitrate:", self._bitrate_spin)
        self._form.addRow("Bit Depth:", self._bit_depth_combo)
        self._form.addRow("FLAC Compression (0-12):", self._flac_compression_spin)
        self._form.addRow("", self._use_soxr_check)
        self._form.addRow("SOXR Precision (1-33):", self._soxr_precision_spin)
        self._form.addRow("Output Suffix Name:", self._output_suffix_edit)
        self._form.addRow("Output Folder:", output_dir_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(self._form)
        layout.addWidget(buttons)

        self._format_combo.currentIndexChanged.connect(self._update_field_states)
        self._use_soxr_check.toggled.connect(self._update_field_states)
        self._update_field_states()

    def _current_format(self) -> OutputFormat:
        # PySide6 may flatten str-Enum values to plain strings via QVariant/userData().
        # Calling OutputFormat(data) safely restores the correct enum member.
        data = self._format_combo.currentData()
        return OutputFormat(data)

    def _set_row_visible(self, field_widget, visible: bool) -> None:
        # Prevent hidden rows from leaving extra blank space.
        # For example, MP3 hides 4 rows.
        self._form.setRowVisible(field_widget, visible)

    def _update_field_states(self) -> None:
        fmt = self._current_format()
        is_lossless = fmt in LOSSLESS_FORMATS  # FLAC, WAV, ALAC -> no bitrate
        is_soxr_format = fmt in SOXR_FORMATS  # FLAC, WAV -> SOXR available (checkbox).
        is_flac = fmt == OutputFormat.FLAC

        self._set_row_visible(self._bit_depth_combo, is_lossless)
        self._set_row_visible(self._bitrate_spin, not is_lossless)
        self._set_row_visible(self._use_soxr_check, is_soxr_format)
        self._set_row_visible(
            self._soxr_precision_spin, is_soxr_format and self._use_soxr_check.isChecked()
        )
        self._set_row_visible(self._flac_compression_spin, is_flac)

        self._form.activate()
        self.adjustSize()

    def _on_browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select the output folder", self._output_dir_edit.text()
        )
        if path:
            self._output_dir_edit.setText(path)

    def get_settings(self) -> ConversionSettings:
        return ConversionSettings(
            output_format=self._current_format(),
            sample_rate_hz=self._sample_rate_combo.currentData(),
            bit_depth=self._bit_depth_combo.currentData(),
            bitrate_kbps=self._bitrate_spin.value(),
            use_soxr=self._use_soxr_check.isChecked(),
            soxr_precision=self._soxr_precision_spin.value(),
            flac_compression_level=self._flac_compression_spin.value(),
            custom_output_suffix=self._output_suffix_edit.text().strip(),
            custom_output_dir=self._output_dir_edit.text().strip(),
        )
