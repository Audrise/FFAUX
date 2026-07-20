"""Dialog untuk mengedit metadata & cover art satu ATAU BANYAK AudioFile
sekaligus (multi-select).

Dialog ini merangkai MetadataEditor + CoverArtViewer + kontrol template,
lalu mengembalikan hasil edit ke pemanggil lewat method get_result().
Dialog TIDAK menjalankan FFmpeg langsung -- MainWindow yang akan
membuat Job (APPLY_METADATA / SET_COVER) dari hasilnya dan mengirim
ke JobManager, konsisten dengan aturan "GUI selalu lewat JobManager".

Saat lebih dari satu file dipilih:
- Field metadata bersifat dinamis mengikuti gabungan tag semua file
  terpilih. Field yang nilainya SAMA di semua file bisa diedit dan,
  kalau diubah, hasilnya berlaku untuk SEMUA file terpilih. Field yang
  nilainya BERBEDA ditampilkan read-only (gabungan nilai dipisah " - ")
  dan kalau disimpan tanpa diubah, tiap file tetap memakai nilai
  aslinya masing-masing -- lihat core/metadata_field_merger.py. Ini
  berlaku APAPUN penyebab bedanya (mis. album berbeda antar track) --
  field lain yang kebetulan SAMA tetap bisa diedit seperti biasa.
- Cover art yang ditampilkan/diedit adalah milik file PERTAMA pada
  urutan terpilih (mis. kalau album berbeda-beda, cover yang tampil
  adalah cover art dari file di indeks pertama).
- Tombol "+ Tambah Metadata" nambah baris kosong baru (nama tag +
  nilai bebas); tombol "Hapus Metadata Terpilih" hapus field yang
  terakhir diklik/fokus -- field bawaan yang dihapus beneran dibuang
  dari file lewat -metadata key= (lihat command_builder.py), bukan
  cuma hilang dari tampilan.

Pengecualian kecil: ekstraksi cover art untuk PREVIEW dijalankan
sinkron (blocking sesaat) via MetadataService, karena ini operasi
satu file yang biasanya <1 detik dan hanya untuk pratinjau, bukan
bagian dari batch job. Trade-off ini didokumentasikan di sini secara
sengaja -- jika suatu saat file besar membuat ini terasa lambat,
gampang diubah jadi async dengan memindahkannya ke JobManager biasa.
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

        # Kompatibel dengan pemanggil lama yang mengirim satu AudioFile.
        self._audio_files: list[AudioFile] = (
            [audio_files] if isinstance(audio_files, AudioFile) else list(audio_files)
        )
        self._primary_file = self._audio_files[0]

        if len(self._audio_files) > 1:
            self.setWindowTitle(f"Edit Metadata - {len(self._audio_files)} file terpilih")
        else:
            self.setWindowTitle(f"Edit Metadata - {self._primary_file.filename}")
        self.resize(760, 480)

        self._metadata_service = metadata_service
        self._template_service = template_service
        self._cover_changed = False  # True jika user mengubah/menghapus cover

        self._metadata_editor = MetadataEditor()
        self._metadata_editor.load_for_files(self._audio_files)

        # Cover art yang ditampilkan & bisa diedit selalu milik file
        # pertama pada urutan terpilih, walaupun banyak file dipilih.
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

    # ------------------------------------------------------------------
    # Template: pilih + preview isi + terapkan/simpan
    # ------------------------------------------------------------------
    def _build_template_row(self) -> QHBoxLayout:
        self._template_combo = QComboBox()
        self._template_combo.addItems(self._template_service.list_templates())

        preview_btn = QPushButton("Preview Metadata")
        apply_btn = QPushButton("Terapkan Template")
        save_btn = QPushButton("Simpan sebagai Template...")
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
        """Buka window baru yang menampilkan isi template yang SEDANG
        dipilih di combo box "Template" -- menggantikan panel preview
        lama yang tampil otomatis inline di bawah baris Template.
        """
        name = self._template_combo.currentText()
        if not name:
            QMessageBox.information(self, "Pilih Template", "Pilih template di dropdown terlebih dahulu.")
            return
        try:
            template_metadata = self._template_service.load_template(name)
        except FileNotFoundError as exc:
            QMessageBox.warning(self, "Template tidak ditemukan", str(exc))
            return

        data = template_metadata.to_dict()
        if data:
            preview_text = "\n".join(f"{key} - {value}" for key, value in data.items())
        else:
            preview_text = "(template ini kosong)"

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
            QMessageBox.warning(self, "Template tidak ditemukan", str(exc))
            return
        self._metadata_editor.apply_template(template_metadata)

    def _on_save_template_clicked(self) -> None:
        name, ok = QInputDialog.getText(self, "Simpan Template", "Nama template:")
        if not ok or not name.strip():
            return
        self._template_service.save_template(name.strip(), self._metadata_editor.get_metadata())
        self._template_combo.clear()
        self._template_combo.addItems(self._template_service.list_templates())

    # ------------------------------------------------------------------
    # Tambah / Hapus field metadata
    # ------------------------------------------------------------------
    def _build_field_buttons_row(self) -> QHBoxLayout:
        add_btn = QPushButton("Tambah Metadata")
        delete_btn = QPushButton("Hapus Metadata Terpilih")
        add_btn.clicked.connect(self._metadata_editor.add_empty_field)
        delete_btn.clicked.connect(self._on_delete_field_clicked)

        row = QHBoxLayout()
        row.addWidget(add_btn)
        row.addWidget(delete_btn)
        row.addStretch(1)
        return row

    def _on_delete_field_clicked(self) -> None:
        if not self._metadata_editor.delete_selected_field():
            QMessageBox.information(
                self,
                "Pilih field",
                "Klik dulu field metadata yang ingin dihapus (fokus ke kolomnya), lalu tekan tombol ini lagi.",
            )

    # ------------------------------------------------------------------
    # Cover art
    # ------------------------------------------------------------------
    def _on_extract_cover_clicked(self) -> None:
        if not self._extract_and_show_cover():
            QMessageBox.information(self, "Tidak ada cover", "File ini tidak memiliki cover art tertanam.")

    def _extract_and_show_cover(self) -> bool:
        """Ekstrak cover art tertanam (milik file pertama terpilih) lalu
        tampilkan di viewer. Return False kalau file memang tidak punya
        cover (dipakai baik oleh auto-extract saat dialog dibuka maupun
        tombol "Ekstrak dari File").
        """
        temp_dir = Path(tempfile.gettempdir()) / "audrisefftool_covers"
        path = self._metadata_service.extract_cover_art_sync(self._primary_file, str(temp_dir))
        if path:
            self._cover_viewer.load_image(path)
            return True
        return False

    def _on_cover_path_changed(self, path) -> None:
        self._cover_changed = True

    # ------------------------------------------------------------------
    def get_result(self) -> tuple[Metadata, str | None, bool, set[str]]:
        """Kembalikan (metadata_baru, cover_path_baru_atau_None, cover_berubah,
        deleted_keys).

        `metadata_baru` hanya berisi field yang bisa diedit (nilainya sama
        di semua file terpilih, atau field baru yang diketik user). Field
        yang berbeda antar track (read-only) sengaja tidak disertakan --
        pemanggil (MainWindow) men-merge metadata_baru ke metadata masing2
        file, sehingga field yang tidak disertakan otomatis mempertahankan
        nilai asli tiap file.

        `deleted_keys` berisi key tag yang eksplisit dihapus user lewat
        tombol Hapus Metadata Terpilih -- pemanggil perlu mengirim ini
        sebagai job.params["deleted_metadata_keys"] supaya tag itu BENAR
        dihapus dari file output (bukan cuma hilang dari tampilan form).
        """
        return (
            self._metadata_editor.get_metadata(),
            self._cover_viewer.current_path(),
            self._cover_changed,
            self._metadata_editor.get_deleted_keys(),
        )