"""
# This table also acts as a drop area:

audio files and folders can be dragged and dropped directly onto it.
Multiple items can be selected for Edit, Convert, or Delete actions.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QWheelEvent, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QHeaderView, QMenu, QProgressBar, QTableWidget,
    QTableWidgetItem, QHBoxLayout, QWidget
)

from core.models.audio_file import AudioFile, FileStatus
from utils.file_utils import (
    collect_audio_files, format_duration, format_file_size,
    format_bit_depth, format_sample_rate, format_bitrate
)
from utils.paths import icons_path

_STATUS_LABELS = {
    FileStatus.PENDING: "Pending",
    FileStatus.QUEUED: "Queued",
    FileStatus.RUNNING: "Processing",
    FileStatus.DONE: "Completed",
    FileStatus.FAILED: "Failed",
    FileStatus.CANCELLED: "Cancelled",
}

(
    _COL_FILE_NAME, _COL_TRACK, _COL_DISC, _COL_TITLE, _COL_ARTIST, _COL_ALBUM_ARTIST, _COL_ALBUM,
    _COL_YEAR, _COL_DURATION, _COL_BIT_DEPTH, _COL_SAMPLE_RATE, _COL_BITRATE, _COL_SIZE, _COL_CODEC,
    _COL_RATING, _COL_STATUS, _COL_PROGRESS,
) = range(17)

_HEADERS = [
    "File Name", "Track No", "Disc No", "Title", "Artist", "Album Artist", "Album",
    "Year", "Duration", "Bit Depth", "Sample Rate", "Bitrate", "File size", "Codec", "Rating",
    "Status", "Progress",
]

_DEFAULT_HIDDEN_COLUMNS = {
    _COL_FILE_NAME,
    _COL_RATING,
    _COL_DISC,
    _COL_ALBUM_ARTIST,
}

_DEFAULT_WIDTHS = {
    _COL_FILE_NAME: 240,
    _COL_TRACK: 65,
    _COL_DISC: 65,
    _COL_TITLE: 220,
    _COL_ARTIST: 120,
    _COL_ALBUM_ARTIST: 120,
    _COL_ALBUM: 420,
    _COL_YEAR: 90,
    _COL_DURATION: 85,
    _COL_BIT_DEPTH: 75,
    _COL_SAMPLE_RATE: 90,
    _COL_BITRATE: 90,
    _COL_SIZE: 90,
    _COL_CODEC: 90,
    _COL_RATING: 90,
    _COL_STATUS: 90,
    _COL_PROGRESS: 115,
}

_ID_ROLE = Qt.ItemDataRole.UserRole

_SORT_COLUMNS = {
    "track_no": _COL_TRACK,
    "disc_no": _COL_DISC,
    "title": _COL_TITLE,
    "artist": _COL_ARTIST,
    "album_artist": _COL_ALBUM_ARTIST,
    "album": _COL_ALBUM,
    "date": _COL_YEAR,
}

class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other: QTableWidgetItem) -> bool:
        try:
            return int(self.text()) < int(other.text())
        except (ValueError, TypeError):
            return super().__lt__(other)

class TrackTable(QTableWidget):
    filesDropped = Signal(list)  # list[str] path of dropped audio files

    def __init__(self, parent=None):
        super().__init__(0, len(_HEADERS), parent)
        self.setHorizontalHeaderLabels(_HEADERS)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self._ffaux_icons = icons_path()

        header = self.horizontalHeader()
        header.setHighlightSections(False)
        header.setFixedHeight(24)
        header.setSectionsMovable(True)
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._on_header_context_menu)

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

        for col in _DEFAULT_HIDDEN_COLUMNS:
            header.setSectionHidden(col, True)

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

    def reset_layout(self) -> None:
        # Reset column widths, visibility, and order to defaults in one call.
        header = self.horizontalHeader()

        for logical in range(self.columnCount()):
            current_visual = header.visualIndex(logical)
            if current_visual != logical:
                header.moveSection(current_visual, logical)

        # Visibility: only the columns hidden by default start hidden again.
        for col in range(self.columnCount()):
            header.setSectionHidden(col, col in _DEFAULT_HIDDEN_COLUMNS)

        self.reset_column_widths()

    def build_column_toggle_actions(self, parent) -> list[QAction]:
        header = self.horizontalHeader()
        actions: list[QAction] = []
        for col, label in enumerate(_HEADERS):
            action = QAction(label, parent)
            action.setCheckable(True)
            action.setChecked(not header.isSectionHidden(col))
            action.toggled.connect(lambda checked, c=col: self._set_column_visible(c, checked))
            actions.append(action)
        return actions

    def _on_header_context_menu(self, pos) -> None:
        header = self.horizontalHeader()
        menu = QMenu(self)
        columns_menu = menu.addMenu("Columns")
        columns_menu.setIcon(QIcon(str(self._ffaux_icons / "Columns.ico")))
        for action in self.build_column_toggle_actions(columns_menu):
            columns_menu.addAction(action)
        menu.exec(header.mapToGlobal(pos))

    def _set_column_visible(self, col: int, visible: bool) -> None:
        header = self.horizontalHeader()
        header.setSectionHidden(col, not visible)

        if visible:
            # Keep hidden sections slots by moving them to the far right.
            last_visual = header.count() - 1
            current_visual = header.visualIndex(col)
            if current_visual != last_visual:
                header.moveSection(current_visual, last_visual)

    # Save the current column order (see MainWindow.closeEvent).
    # The order contains logical column indices from left to right.
    def column_order(self) -> list[int]:
        header = self.horizontalHeader()
        return [header.logicalIndex(visual) for visual in range(header.count())]

    def apply_column_order(self, order: list[int]) -> None:
        header = self.horizontalHeader()
        for target_visual, logical in enumerate(order):
            if not (0 <= logical < self.columnCount()):
                continue
            current_visual = header.visualIndex(logical)
            if current_visual != target_visual:
                header.moveSection(current_visual, target_visual)

    # Persist hidden columns (see MainWindow.closeEvent).
    def hidden_columns(self) -> list[int]:
        header = self.horizontalHeader()
        return [col for col in range(self.columnCount()) if header.isSectionHidden(col)]

    def apply_hidden_columns(self, hidden_columns: list[int]) -> None:
        header = self.horizontalHeader()
        hidden_set = set(hidden_columns)
        for col in range(self.columnCount()):
            header.setSectionHidden(col, col in hidden_set)

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

    # Once vertical scrolling reaches the top or bottom, further scrolling moves horizontally.
    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.pixelDelta().y() or event.angleDelta().y()

        vbar = self.verticalScrollBar()
        hbar = self.horizontalScrollBar()

        if delta < 0:
            if vbar.value() >= vbar.maximum():
                if hbar.value() < hbar.maximum():
                    hbar.setValue(hbar.value() - delta)
                    event.accept()
                    return

        elif delta > 0:
            if vbar.value() >= vbar.maximum():
                if hbar.value() > hbar.minimum():
                    hbar.setValue(hbar.value() - delta)
                    event.accept()
                    return

        super().wheelEvent(event)

    # Fill & read row data
    def add_file(self, audio_file: AudioFile) -> None:
        row = self.rowCount()
        self.insertRow(row)

        meta = audio_file.metadata

        values = {
            _COL_FILE_NAME: audio_file.filename,
            _COL_TRACK: meta.track_number or "",
            _COL_DISC: meta.disc_number or "",
            _COL_TITLE: meta.title or audio_file.filename,
            _COL_ARTIST: meta.artist or "",
            _COL_ALBUM_ARTIST: meta.album_artist or "",
            _COL_ALBUM: meta.album or "",
            _COL_YEAR: meta.year or "",
            _COL_DURATION: format_duration(audio_file.duration_seconds),
            _COL_BIT_DEPTH: format_bit_depth(audio_file.bit_depth),
            _COL_SAMPLE_RATE: format_sample_rate(audio_file.sample_rate_hz),
            _COL_BITRATE: format_bitrate(audio_file.bitrate_kbps),
            _COL_SIZE: format_file_size(audio_file.file_size_bytes),
            _COL_CODEC: audio_file.codec or "-",
            _COL_RATING: meta.rating or "",
            _COL_STATUS: _STATUS_LABELS[audio_file.status],
        }
        for col, text in values.items():
            if col in (_COL_TRACK, _COL_DISC):
                item = NumericTableWidgetItem(str(text))
            else:
                item = QTableWidgetItem(str(text))

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, col, item)

        # audio_file.id is stored as data in the Title column item; it is used
        # to rebuild _row_by_id whenever the row structure changes.
        self.item(row, _COL_TITLE).setData(_ID_ROLE, audio_file.id)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        progress_container = QWidget()
        progress_container.setObjectName("progressContainer")
        progress_layout = QHBoxLayout(progress_container)
        progress_layout.setContentsMargins(4, 2, 4, 2)
        progress_layout.addWidget(progress_bar)
        progress_container.progress_bar = progress_bar
        self.setCellWidget(row, _COL_PROGRESS, progress_container)

        self._row_by_id[audio_file.id] = row

    def update_metadata(self, audio_file_id: str, audio_file: AudioFile) -> None:
        # Refresh only metadata-dependent columns after async ffprobe completes.
        row = self._row_by_id.get(audio_file_id)
        if row is None:
            return  # row was removed (e.g. user deleted it) before the probe finished

        meta = audio_file.metadata
        values = {
            _COL_FILE_NAME: audio_file.filename,
            _COL_TRACK: meta.track_number or "",
            _COL_TITLE: meta.title or audio_file.filename,
            _COL_ARTIST: meta.artist or "",
            _COL_ALBUM: meta.album or "",
            _COL_YEAR: meta.year or "",
            _COL_DURATION: format_duration(audio_file.duration_seconds),
            _COL_BIT_DEPTH: format_bit_depth(audio_file.bit_depth),
            _COL_SAMPLE_RATE: format_sample_rate(audio_file.sample_rate_hz),
            _COL_BITRATE: format_bitrate(audio_file.bitrate_kbps),
            _COL_SIZE: format_file_size(audio_file.file_size_bytes),
            _COL_CODEC: audio_file.codec or "-",
            _COL_RATING: meta.rating or "",
        }
        for col, text in values.items():
            item = self.item(row, col)

            if item is None:
                if col in (_COL_TRACK, _COL_DISC):
                    item = NumericTableWidgetItem(str(text))
                else:
                    item = QTableWidgetItem(str(text))

                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row, col, item)
            else:
                item.setText(str(text))

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
        # Delete all currently selected rows.
        # Returns the IDs of the deleted rows.
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
        container = self.cellWidget(row, _COL_PROGRESS)
        bar = getattr(container, "progress_bar", None)
        if isinstance(bar, QProgressBar):
            bar.setValue(int(round(percent)))

    def clear_all(self) -> None:
        self.setRowCount(0)
        self._row_by_id.clear()

    # Selection
    def selected_row_id(self) -> str | None:
        # Return the first selected row ID for legacy single-file callers.
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

    # Search (View > Show Search Bar / Ctrl+F, or right-click on the table).
    def filter_rows(self, query: str) -> None:
        query = query.strip().lower()
        search_cols = (_COL_FILE_NAME, _COL_TITLE, _COL_ARTIST, _COL_ALBUM, _COL_YEAR, _COL_CODEC)

        for row in range(self.rowCount()):
            if not query:
                self.setRowHidden(row, False)
                continue

            match = any(
                query in (self.item(row, col).text().lower() if self.item(row, col) else "")
                for col in search_cols
            )
            self.setRowHidden(row, not match)

    def sort_by(self, key: str, ascending: bool = True) -> None:
        # Sorting moves the table items, but not the setCellWidget() widgets.
        # Keep progress bars mapped by audio_file_id and re-attach them after sorting.
        col = _SORT_COLUMNS.get(key)
        if col is None:
            return

        progress_widgets: dict[str, QWidget] = {}
        for row in range(self.rowCount()):
            item = self.item(row, _COL_TITLE)
            file_id = item.data(_ID_ROLE) if item else None
            widget = self.cellWidget(row, _COL_PROGRESS)
            if file_id and widget is not None:
                progress_widgets[file_id] = widget

        order = Qt.SortOrder.AscendingOrder if ascending else Qt.SortOrder.DescendingOrder
        self.sortItems(col, order)

        for row in range(self.rowCount()):
            item = self.item(row, _COL_TITLE)
            file_id = item.data(_ID_ROLE) if item else None
            widget = progress_widgets.get(file_id) if file_id else None
            if widget is not None:
                self.setCellWidget(row, _COL_PROGRESS, widget)

        self._rebuild_row_index()