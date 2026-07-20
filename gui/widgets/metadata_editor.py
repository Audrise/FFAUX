"""Widget form untuk mengedit metadata satu atau banyak AudioFile sekaligus.

Widget ini tidak menyimpan apa pun ke disk / menjalankan FFmpeg -- hanya
membaca/menulis objek Metadata di memori. Penyimpanan sesungguhnya
(via job APPLY_METADATA) dilakukan oleh MainWindow/dialog pemanggil.

Field yang ditampilkan bersifat DINAMIS mengikuti tag yang benar-benar
dimiliki file terpilih (lihat core/metadata_field_merger.py), bukan daftar
field tetap. Saat lebih dari satu file dipilih dan sebuah field punya nilai
berbeda antar file, field itu ditampilkan read-only berisi gabungan semua
nilai berbeda tsb (dipisah " - ") dan diabaikan saat disimpan tanpa diubah,
sehingga nilai asli tiap track tetap dipertahankan.

Dua kemampuan tambahan:
- Tambah field metadata baru (tag + value bebas, diketik user) lewat
  add_empty_field().
- Hapus field (baik field bawaan file maupun field baru yang belum
  disimpan) lewat delete_selected_field() -- field yang terakhir dapat
  fokus (diklik/di-tab ke situ) yang dihapus. Field bawaan yang dihapus
  ditandai supaya saat Save, tag itu benar-benar dibuang dari file
  (bukan cuma dikosongkan di form) -- lihat get_deleted_keys().
"""
from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLineEdit, QScrollArea, QVBoxLayout, QWidget

from core.metadata_field_merger import FieldView, build_field_views
from core.models.audio_file import AudioFile
from core.models.metadata import Metadata


class _FocusTrackingLineEdit(QLineEdit):
    """QLineEdit biasa, cuma nambah callback saat dapat fokus (diklik/di-tab
    ke situ), dipakai buat tau field mana yang "dipilih" user untuk Hapus.
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

        # Hanya field yang NILAINYA SAMA di semua file terpilih yang masuk
        # ke sini (bisa diedit). Field yang beda antar file ditampilkan
        # read-only dan sengaja tidak disimpan di _edits, supaya
        # get_metadata() otomatis mengabaikannya.
        self._edits: dict[str, QLineEdit] = {}
        self._field_views: list[FieldView] = []

        # widget -> key, untuk SEMUA field bawaan file (editable maupun
        # read-only) -- dipakai delete_selected_field() cari tau key dari
        # widget yang lagi dipilih, tanpa perlu nebak-nebak dari label.
        self._edit_to_key: dict[QLineEdit, str] = {}

        # Baris "Tambah Metadata" yang belum di-Save: list of (key_edit, value_edit).
        # Key-nya diketik bebas oleh user, makanya perlu widget terpisah,
        # bukan QLabel statis seperti field bawaan.
        self._new_rows: list[tuple[QLineEdit, QLineEdit]] = []

        self._deleted_keys: set[str] = set()
        self._selected_edit: QLineEdit | None = None

    # ------------------------------------------------------------------
    def load_metadata(self, metadata: Metadata) -> None:
        """Kompatibel dengan pemanggil lama: tampilkan field satu Metadata.

        Dipakai juga secara internal oleh load_for_files() untuk kasus satu
        file terpilih.
        """
        dummy = AudioFile(path="")
        dummy.metadata = metadata
        self.load_for_files([dummy])

    def load_for_files(self, audio_files: list[AudioFile]) -> None:
        """Bangun ulang form berdasarkan field dinamis dari file terpilih."""
        self._clear_form()
        self._field_views = build_field_views(audio_files)

        for view in self._field_views:
            edit = _FocusTrackingLineEdit(self._on_field_focused)
            edit.setText(view.value)
            if not view.editable:
                edit.setReadOnly(True)
                edit.setToolTip(
                    "Nilai berbeda antar track terpilih -- tidak bisa diedit. "
                    "Jika disimpan tanpa diubah, tiap track tetap memakai nilainya masing-masing."
                )
            else:
                self._edits[view.key] = edit
            self._edit_to_key[edit] = view.key
            self._form.addRow(f"{view.label}:", edit)

    def add_empty_field(self) -> None:
        """Tambah baris kosong baru di bawah field terakhir: satu field buat
        nama tag (diketik bebas user), satu field buat nilainya. Baru
        benar-benar jadi tag kalau keduanya terisi & dialog di-Save.
        """
        key_edit = _FocusTrackingLineEdit(self._on_field_focused)
        key_edit.setPlaceholderText("Tag baru")

        value_edit = _FocusTrackingLineEdit(self._on_field_focused)
        value_edit.setPlaceholderText("Nilai")

        self._new_rows.append((key_edit, value_edit))
        self._form.addRow(key_edit, value_edit)
        key_edit.setFocus()

    def delete_selected_field(self) -> bool:
        """Hapus field yang terakhir dapat fokus (diklik user). Return True
        kalau ada yang berhasil dihapus, False kalau belum ada field yang
        dipilih (user belum klik field mana pun).

        - Field baru (belum di-Save, dari add_empty_field) -> dibuang
          begitu saja dari form, tidak perlu ditandai apa-apa.
        - Field bawaan file (baik editable maupun read-only) -> baris
          dibuang dari form DAN key-nya ditandai di _deleted_keys, supaya
          saat Save tag itu benar-benar dihapus dari file (bukan cuma
          hilang dari tampilan form).
        """
        if self._selected_edit is None:
            return False

        # Kasus 1: field baru yang belum di-Save.
        for key_edit, value_edit in list(self._new_rows):
            if self._selected_edit in (key_edit, value_edit):
                self._form.removeRow(key_edit)
                self._new_rows.remove((key_edit, value_edit))
                self._selected_edit = None
                return True

        # Kasus 2: field bawaan file (editable atau read-only).
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
        """Kembalikan Metadata dari field yang BISA diedit (nilainya sama
        di semua file terpilih) DITAMBAH field baru yang diisi lengkap
        (key & value keduanya terisi) lewat Tambah Metadata. Field yang
        berbeda antar track (read-only) sengaja TIDAK disertakan supaya
        tidak menimpa nilai asli masing-masing track saat di-merge.
        """
        values = {name: edit.text().strip() or None for name, edit in self._edits.items()}
        for key_edit, value_edit in self._new_rows:
            key = key_edit.text().strip()
            value = value_edit.text().strip()
            if key and value:
                values[key] = value
        return Metadata.from_dict({k: v for k, v in values.items() if v is not None})

    def get_deleted_keys(self) -> set[str]:
        """Key tag yang eksplisit dihapus user lewat tombol Hapus Metadata
        (field bawaan file, bukan field baru yang belum sempat di-Save).
        """
        return set(self._deleted_keys)

    def apply_template(self, template_metadata: Metadata) -> None:
        """Terapkan template di atas nilai form saat ini (hanya field yang
        BISA diedit dan terisi di template yang menimpa nilai form). Field
        read-only (beda antar track) tidak disentuh -- belum didukung.
        """
        template_data = template_metadata.to_dict()
        for key, edit in self._edits.items():
            if key in template_data:
                edit.setText(str(template_data[key]))
