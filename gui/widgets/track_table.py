"""
Tabel ini sekaligus menjadi drop area: file/folder audio bisa langsung
di-drag & drop ke tabel (menggantikan widget DropArea terpisah yang
sebelumnya ada). Mendukung multi-select untuk aksi Edit/Convert/Hapus.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QProgressBar, QTableWidget, QTableWidgetItem

from core.models.audio_file import AudioFile, FileStatus
from utils.file_utils import collect_audio_files, format_duration, format_file_size, format_sample_rate

_STATUS_LABELS = {
    FileStatus.PENDING: "Menunggu",
    FileStatus.QUEUED: "Dalam antrian",
    FileStatus.RUNNING: "Diproses",
    FileStatus.DONE: "Selesai",
    FileStatus.FAILED: "Gagal",
    FileStatus.CANCELLED: "Dibatalkan",
}

(
    _COL_TRACK, _COL_TITLE, _COL_ARTIST, _COL_ALBUM, _COL_YEAR, _COL_DURATION, _COL_SAMPLE_RATE,
    _COL_BITRATE, _COL_SIZE, _COL_CODEC, _COL_STATUS, _COL_PROGRESS,
) = range(12)

_HEADERS = [
    "Track No", "Title", "Artist", "Album", "Year", "Duration", "Sample Rate",
    "Bitrate", "File size", "Codec", "Status", "Progress",
]

_ID_ROLE = Qt.ItemDataRole.UserRole

class TrackTable(QTableWidget):
    """Tabel yang menyimpan audio_file_id sebagai data pada tiap baris
    (lewat Qt.ItemDataRole.UserRole di kolom Title), bukan lewat dict
    posisi statis -- supaya index tidak "basi" setelah baris dihapus
    atau diurutkan ulang. `_row_by_id` di-rebuild dari data ini setiap
    kali struktur baris berubah.
    """

    filesDropped = Signal(list)  # list[str] path file audio hasil drop

    def __init__(self, parent=None):
        super().__init__(0, len(_HEADERS), parent)
        self.setHorizontalHeaderLabels(_HEADERS)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)

        header = self.horizontalHeader()
        header.setHighlightSections(False)
        header.setFixedHeight(24)

        self.verticalHeader().setVisible(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setTabKeyNavigation(True)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setCurrentCell(-1, -1)
        self.setAcceptDrops(True)
        self._row_by_id: dict[str, int] = {}

        _DEFAULT_WIDTHS = {
            _COL_TRACK: 70,
            _COL_TITLE: 220,
            _COL_ARTIST: 120,
            _COL_ALBUM: 420,
            _COL_YEAR: 90,
            _COL_DURATION: 90,
            _COL_SAMPLE_RATE: 90,
            _COL_BITRATE: 90,
            _COL_SIZE: 90,
            _COL_CODEC: 90,
            _COL_STATUS: 90,
            _COL_PROGRESS: 115,
        }

        for col in range(len(_HEADERS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(col, _DEFAULT_WIDTHS.get(col, 100))

    # ------------------------------------------------------------------
    # Drag & drop langsung di tabel
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        raw_paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        audio_files = collect_audio_files(raw_paths)
        if audio_files:
            self.filesDropped.emit(audio_files)
        event.acceptProposedAction()

    # ------------------------------------------------------------------
    # Isi & baca data baris
    # ------------------------------------------------------------------
    def add_file(self, audio_file: AudioFile) -> None:
        row = self.rowCount()
        self.insertRow(row)

        meta = audio_file.metadata

        values = {
            _COL_TRACK: meta.track_number or "",
            _COL_TITLE: meta.title,
            _COL_ARTIST: meta.artist,
            _COL_ALBUM: meta.album or "",
            _COL_YEAR: meta.year or "unknown",
            _COL_DURATION: format_duration(audio_file.duration_seconds),
            _COL_SAMPLE_RATE: format_sample_rate(audio_file.sample_rate_hz),
            _COL_BITRATE: f"{audio_file.bitrate_kbps} kbps" if audio_file.bitrate_kbps else "-",
            _COL_SIZE: format_file_size(audio_file.file_size_bytes),
            _COL_CODEC: audio_file.codec or "-",
            _COL_STATUS: _STATUS_LABELS[audio_file.status],
        }
        for col, text in values.items():
            self.setItem(row, col, QTableWidgetItem(str(text)))

        # audio_file.id ditempel sebagai data pada item kolom Title, dipakai
        # untuk membangun ulang _row_by_id kapan pun struktur baris berubah.
        self.item(row, _COL_TITLE).setData(_ID_ROLE, audio_file.id)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFixedWidth(110)
        self.setCellWidget(row, _COL_PROGRESS, progress_bar)

        self._row_by_id[audio_file.id] = row

    def remove_ids(self, audio_file_ids: list[str]) -> None:
        """Hapus baris untuk sekumpulan audio_file_id sekaligus (multi-select)."""
        ids_to_remove = set(audio_file_ids)
        rows_to_remove = sorted(
            (row for file_id, row in self._row_by_id.items() if file_id in ids_to_remove),
            reverse=True,
        )
        for row in rows_to_remove:
            self.removeRow(row)
        self._rebuild_row_index()

    def remove_selected_rows(self) -> list[str]:
        """Hapus semua baris yang sedang terpilih. Mengembalikan id yang dihapus."""
        selected_ids = self.selected_row_ids()
        self.remove_ids(selected_ids)
        return selected_ids

    def _rebuild_row_index(self) -> None:
        self._row_by_id.clear()
        for row in range(self.rowCount()):
            item = self.item(row, _COL_TITLE)
            file_id = item.data(_ID_ROLE) if item else None
            if file_id:
                self._row_by_id[file_id] = row

    def update_status(self, audio_file_id: str, status: FileStatus) -> None:
        row = self._row_by_id.get(audio_file_id)
        if row is None:
            return
        item = self.item(row, _COL_STATUS)
        if item:
            item.setText(_STATUS_LABELS.get(status, status.value))

    def update_progress(self, audio_file_id: str, percent: float) -> None:
        row = self._row_by_id.get(audio_file_id)
        if row is None:
            return
        bar = self.cellWidget(row, _COL_PROGRESS)
        if isinstance(bar, QProgressBar):
            bar.setValue(int(round(percent)))

    def clear_all(self) -> None:
        self.setRowCount(0)
        self._row_by_id.clear()

    # ------------------------------------------------------------------
    # Seleksi
    # ------------------------------------------------------------------
    def selected_row_id(self) -> str | None:
        """Kembalikan id baris pertama yang terpilih (kompatibel dengan
        pemanggil lama yang hanya butuh satu file).
        """
        ids = self.selected_row_ids()
        return ids[0] if ids else None

    def selected_row_ids(self) -> list[str]:
        """Kembalikan semua audio_file_id yang sedang terpilih (multi-select)."""
        rows = sorted({index.row() for index in self.selectionModel().selectedRows()})
        ids = []
        for row in rows:
            item = self.item(row, _COL_TITLE)
            file_id = item.data(_ID_ROLE) if item else None
            if file_id:
                ids.append(file_id)
        return ids
