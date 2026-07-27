"""
# This table also serves as a drop area:

audio files/folders can be directly dragged and dropped onto the table.
It supports multi-selection for Edit/Convert/Delete actions.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QProgressBar, QTableWidget, QTableWidgetItem

from core.models.audio_file import AudioFile, FileStatus
from utils.file_utils import collect_audio_files, format_duration, format_file_size, format_sample_rate

_STATUS_LABELS = {
    FileStatus.PENDING: "Pending",
    FileStatus.QUEUED: "Queued",
    FileStatus.RUNNING: "Processing",
    FileStatus.DONE: "Completed",
    FileStatus.FAILED: "Failed",
    FileStatus.CANCELLED: "Cancelled",
}

(
    _COL_TRACK, _COL_TITLE, _COL_ARTIST, _COL_ALBUM, _COL_YEAR, _COL_DURATION, _COL_SAMPLE_RATE,
    _COL_BITRATE, _COL_SIZE, _COL_CODEC, _COL_STATUS, _COL_PROGRESS,
) = range(12)

_HEADERS = [
    "Track No", "Title", "Artist", "Album", "Year", "Duration", "Sample Rate",
    "Bitrate", "File size", "Codec", "Status", "Progress",
]

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

_ID_ROLE = Qt.ItemDataRole.UserRole

class TrackTable(QTableWidget):
    """Table storing audio_file_id as data in each row
    (via Qt.ItemDataRole.UserRole in the Title column), rather than in a dict
    static position. so the index doesn't become "stale" after a row is deleted
    or reordered. `_row_by_id` is rebuilt from this data whenever
    the row structure changes.
    """

    filesDropped = Signal(list)  # list[str] path of dropped audio files

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

        for col in range(len(_HEADERS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(col, _DEFAULT_WIDTHS.get(col, 100))
        self.reset_column_widths()

    # Persist column widths (see MainWindow.closeEvent).
    def column_widths(self) -> list[int]:
        header = self.horizontalHeader()
        return [header.sectionSize(col) for col in range(self.columnCount())]

    def apply_column_widths(self, widths: list[int]) -> None:
        header = self.horizontalHeader()
        for col, width in enumerate(widths):
            if col >= self.columnCount():
                break
            if width > 0:
                header.resizeSection(col, width)

    def reset_column_widths(self) -> None:
        header = self.horizontalHeader()
        for col in range(len(_HEADERS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(col, _DEFAULT_WIDTHS.get(col, 100))

    # Drag and drop directly within the table.
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

    # Fill & read row data
    def add_file(self, audio_file: AudioFile) -> None:
        row = self.rowCount()
        self.insertRow(row)

        meta = audio_file.metadata

        values = {
            _COL_TRACK: meta.track_number or "",
            _COL_TITLE: meta.title,
            _COL_ARTIST: meta.artist,
            _COL_ALBUM: meta.album or "",
            _COL_YEAR: meta.year or "",
            _COL_DURATION: format_duration(audio_file.duration_seconds),
            _COL_SAMPLE_RATE: format_sample_rate(audio_file.sample_rate_hz),
            _COL_BITRATE: f"{audio_file.bitrate_kbps} kbps" if audio_file.bitrate_kbps else "-",
            _COL_SIZE: format_file_size(audio_file.file_size_bytes),
            _COL_CODEC: audio_file.codec or "-",
            _COL_STATUS: _STATUS_LABELS[audio_file.status],
        }
        for col, text in values.items():
            self.setItem(row, col, QTableWidgetItem(str(text)))

        # audio_file.id is stored as data in the Title column item; it is used
        # to rebuild _row_by_id whenever the row structure changes.
        self.item(row, _COL_TITLE).setData(_ID_ROLE, audio_file.id)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFixedWidth(110)
        self.setCellWidget(row, _COL_PROGRESS, progress_bar)

        self._row_by_id[audio_file.id] = row

    def remove_ids(self, audio_file_ids: list[str]) -> None:
        # Delete rows for a set of audio_file_ids at once (multi-select)
        ids_to_remove = set(audio_file_ids)
        rows_to_remove = sorted(
            (row for file_id, row in self._row_by_id.items() if file_id in ids_to_remove),
            reverse=True,
        )
        for row in rows_to_remove:
            self.removeRow(row)
        self._rebuild_row_index()

    def remove_selected_rows(self) -> list[str]:
        # Delete all currently selected rows. Returns the IDs of the deleted rows.
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

    # Selection
    def selected_row_id(self) -> str | None:
        # Return the ID of the first selected row (compatible with legacy callers that only require a single file).
        ids = self.selected_row_ids()
        return ids[0] if ids else None

    def selected_row_ids(self) -> list[str]:
        # Return all currently selected audio_file_ids (multi-select).
        rows = sorted({index.row() for index in self.selectionModel().selectedRows()})
        ids = []
        for row in rows:
            item = self.item(row, _COL_TITLE)
            file_id = item.data(_ID_ROLE) if item else None
            if file_id:
                ids.append(file_id)
        return ids
