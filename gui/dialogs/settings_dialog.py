"""
# Application configuration dialog.

Reads/writes via ConfigService. never accesses the JSON file directly.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.config_service import ConfigService
from core.models.conversion_settings import (
    LOSSLESS_FORMATS,
    SOXR_FORMATS,
    STANDARD_SAMPLE_RATES,
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

class SettingsDialog(QDialog):
    def __init__(self, config_service: ConfigService, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FFTool Settings")
        self.resize(440, 320)
        self._config_service = config_service
        config = config_service.config

        self._ffmpeg_edit = self._make_path_field(config.ffmpeg_path)
        self._ffprobe_edit = self._make_path_field(config.ffprobe_path)
        self._output_dir_edit = self._make_path_field(config.output_directory, is_dir=True)

        self._parallel_spin = QSpinBox()
        self._parallel_spin.setRange(1, 8)
        self._parallel_spin.setValue(config.max_parallel_jobs)

        form = QFormLayout()
        form.addRow("FFmpeg Path:", self._wrap_with_browse(self._ffmpeg_edit, is_dir=False))
        form.addRow("FFprobe Path:", self._wrap_with_browse(self._ffprobe_edit, is_dir=False))
        form.addRow("Default ouput folder:", self._wrap_with_browse(self._output_dir_edit, is_dir=True))
        form.addRow("Maximum parallel jobs:", self._parallel_spin)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)

        # --- Default Conversion Settings ---------------------------------
        # Seeds MainWindow's ConversionSettings on startup (see main.py),
        # instead of every launch always starting from hardcoded defaults
        # (MP3 44100Hz etc). Mirrors ConversionSettingsDialog's fields/
        # visibility behavior so both dialogs stay consistent.
        self._format_combo = QComboBox()
        for fmt in OutputFormat:
            self._format_combo.addItem(_FORMAT_LABELS[fmt], userData=fmt)
        self._format_combo.setCurrentIndex(
            list(OutputFormat).index(OutputFormat(config.default_output_format))
        )

        self._sample_rate_combo = QComboBox()
        for hz in STANDARD_SAMPLE_RATES:
            self._sample_rate_combo.addItem(f"{hz} Hz", userData=hz)
        if config.default_sample_rate_hz in STANDARD_SAMPLE_RATES:
            self._sample_rate_combo.setCurrentIndex(
                STANDARD_SAMPLE_RATES.index(config.default_sample_rate_hz)
            )

        self._bit_depth_combo = QComboBox()
        for depth in (16, 24, 32):
            self._bit_depth_combo.addItem(f"{depth}-bit", userData=depth)
        self._bit_depth_combo.setCurrentIndex((16, 24, 32).index(config.default_bit_depth))

        self._bitrate_spin = QSpinBox()
        self._bitrate_spin.setRange(32, 320)
        self._bitrate_spin.setSuffix(" kbps")
        self._bitrate_spin.setValue(config.default_bitrate_kbps)

        self._flac_compression_spin = QSpinBox()
        self._flac_compression_spin.setRange(0, 12)
        self._flac_compression_spin.setValue(config.default_flac_compression_level)

        self._use_soxr_check = QCheckBox("Use SOX Resampler for FLAC/WAV")
        self._use_soxr_check.setChecked(config.default_use_soxr)

        self._soxr_precision_spin = QSpinBox()
        self._soxr_precision_spin.setRange(1, 33)
        self._soxr_precision_spin.setValue(config.default_soxr_precision)

        self._conversion_form = QFormLayout()
        self._conversion_form.addRow("Output Format:", self._format_combo)
        self._conversion_form.addRow("Sample Rate:", self._sample_rate_combo)
        self._conversion_form.addRow("Bitrate:", self._bitrate_spin)
        self._conversion_form.addRow("Bit Depth:", self._bit_depth_combo)
        self._conversion_form.addRow("FLAC Compression Level (0-12):", self._flac_compression_spin)
        self._conversion_form.addRow("", self._use_soxr_check)
        self._conversion_form.addRow("SOXR Precision (1-33):", self._soxr_precision_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(separator)
        layout.addLayout(self._conversion_form)
        layout.addWidget(buttons)

        self._format_combo.currentIndexChanged.connect(self._update_conversion_field_states)
        self._use_soxr_check.toggled.connect(self._update_conversion_field_states)
        self._update_conversion_field_states()

    def _make_path_field(self, value: str, is_dir: bool = False) -> QLineEdit:
        edit = QLineEdit(value)
        return edit

    def _wrap_with_browse(self, edit: QLineEdit, is_dir: bool) -> QHBoxLayout:
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(32)

        def on_browse():
            if is_dir:
                path = QFileDialog.getExistingDirectory(self, "Select folder", edit.text())
            else:
                path, _ = QFileDialog.getOpenFileName(self, "Select file", edit.text())
            if path:
                edit.setText(path)

        browse_btn.clicked.connect(on_browse)

        row = QHBoxLayout()
        row.addWidget(edit)
        row.addWidget(browse_btn)
        return row

    def _current_format(self) -> OutputFormat:
        # See ConversionSettingsDialog._current_format for why OutputFormat(data)
        # is used instead of just returning currentData() directly.
        return OutputFormat(self._format_combo.currentData())

    def _set_row_visible(self, field_widget, visible: bool) -> None:
        # See ConversionSettingsDialog._set_row_visible -- setRowVisible
        # (not just widget.setVisible()) is needed so the row's spacing
        # actually collapses instead of leaving stacked-up blank gaps.
        self._conversion_form.setRowVisible(field_widget, visible)

    def _update_conversion_field_states(self) -> None:
        fmt = self._current_format()
        is_lossless = fmt in LOSSLESS_FORMATS
        is_soxr_format = fmt in SOXR_FORMATS
        is_flac = fmt == OutputFormat.FLAC

        self._set_row_visible(self._bit_depth_combo, is_lossless)
        self._set_row_visible(self._bitrate_spin, not is_lossless)
        self._set_row_visible(self._use_soxr_check, is_soxr_format)
        self._set_row_visible(
            self._soxr_precision_spin, is_soxr_format and self._use_soxr_check.isChecked()
        )
        self._set_row_visible(self._flac_compression_spin, is_flac)

        #  forcing a fixed resize(440, 320)
        # here backfires: when hidden rows make the content shorter than
        # 320px, Qt has to fill that leftover space *somewhere* in the
        # stacked layouts, and it lands as a stray gap around the
        # separator since neither QFormLayout has an explicit stretch
        # factor telling Qt where the slack should go.
        self._conversion_form.activate()
        self.adjustSize()

    def _on_save(self) -> None:
        cfg = self._config_service
        cfg.set("ffmpeg_path", self._ffmpeg_edit.text())
        cfg.set("ffprobe_path", self._ffprobe_edit.text())
        cfg.set("output_directory", self._output_dir_edit.text())
        cfg.set("max_parallel_jobs", self._parallel_spin.value())

        cfg.set("default_output_format", self._current_format().value)
        cfg.set("default_sample_rate_hz", self._sample_rate_combo.currentData())
        cfg.set("default_bit_depth", self._bit_depth_combo.currentData())
        cfg.set("default_bitrate_kbps", self._bitrate_spin.value())
        cfg.set("default_use_soxr", self._use_soxr_check.isChecked())
        cfg.set("default_soxr_precision", self._soxr_precision_spin.value())
        cfg.set("default_flac_compression_level", self._flac_compression_spin.value())

        cfg.save()
        self.accept()