"""
# MainWindow is solely responsible for:

assembling widgets, forwarding user actions to the backend
(core/*), and updating widgets based on signals from JobManager.
No FFmpeg, parsing, or metadata logic is implemented in this file.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMainWindow, QMenu, QMessageBox, QSplitter, QVBoxLayout, QWidget
from PySide6.QtGui import QShortcut, QKeySequence, QAction
from PySide6.QtCore import Qt, QThreadPool

from core.discord_presence_service import DiscordPresenceService, PresenceState
from core.config_service import ConfigService
from core.filename_parser import FilenameParser
from core.job_manager import JobManager
from core.metadata_probe_worker import MetadataProbeWorker
from core.metadata_service import MetadataService
from core.models.audio_file import AudioFile, FileStatus
from core.models.conversion_settings import ConversionSettings, OutputFormat
from core.models.job import Job, OperationType
from core.models.metadata import Metadata
from core.template_service import TemplateService

from gui.dialogs.conversion_progress_dialog import ConversionProgressDialog
from gui.dialogs.conversion_settings_dialog import ConversionSettingsDialog
from gui.dialogs.metadata_editor_dialog import MetadataEditorDialog
from gui.dialogs.settings_dialog import SettingsDialog

from gui.widgets.log_viewer import LogViewer
from gui.widgets.track_table import TrackTable

from utils.file_utils import collect_audio_files
from utils.logger import get_logger

logger = get_logger("gui.main_window")

_DISCORD_LARGE_IMAGE = "app_logo"

class MainWindow(QMainWindow):
    def __init__(
        self,
        config_service: ConfigService,
        job_manager: JobManager,
        metadata_service: MetadataService,
        template_service: TemplateService,
        discord_presence_service: DiscordPresenceService | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("FFTool v1.0.0")
        self.resize(1200, 600)

        self._config_service = config_service
        self._job_manager = job_manager
        self._metadata_service = metadata_service
        self._template_service = template_service
        self._filename_parser = FilenameParser()
        self._discord_presence = discord_presence_service or DiscordPresenceService(client_id="")
        self._audio_files: dict[str, AudioFile] = {}

        self._metadata_pool = QThreadPool()
        self._metadata_pool.setMaxThreadCount(self._config_service.config.max_metadata_probe_threads)
        self._add_batch_total = 0
        self._add_batch_pending = 0
        self._add_batch_show_message = True

        self._undo_stack: list[tuple[str, list[AudioFile]]] = []
        self._redo_stack: list[tuple[str, list[AudioFile]]] = []
        self._conversion_settings = self._make_default_conversion_settings()
        self._batch_convert_total = 0
        self._batch_convert_success = 0
        self._conversion_progress_dialog: ConversionProgressDialog | None = None

        self._build_ui()
        self._connect_signals()

        saved_widths = self._config_service.config.track_table_column_widths
        if saved_widths:
            self._track_table.apply_column_widths(saved_widths)

        hidden_columns = self._config_service.config.track_table_hidden_columns
        if hidden_columns:
            self._track_table.apply_hidden_columns(hidden_columns)

        column_order = self._config_service.config.track_table_column_order
        if column_order is not None:
            self._track_table.apply_column_order(column_order)

        # Always save; only LOAD is conditional.
        if self._config_service.config.restore_session_on_launch:
            session_paths = self._config_service.config.session_paths
            if session_paths:
                self._on_files_added(session_paths, show_completion_message=False)

        self._discord_presence.update(PresenceState(state="Managing audio library", large_image=_DISCORD_LARGE_IMAGE))

    def _update_file_dependent_actions(self) -> None:
        self._process_action.setEnabled(bool(self._audio_files))

    def closeEvent(self, event) -> None:
        # Drop QUEUED metadata probes so closing doesn't wait;
        # running workers finish on their own and auto-delete.
        self._metadata_pool.clear()

        # Save window state so the next launch can restore it. (see main.py)
        config = self._config_service.config
        config.window_maximized = self.isMaximized()

        if not self.isMaximized():
            config.window_width = self.width()
            config.window_height = self.height()
            config.window_x = self.x()
            config.window_y = self.y()

        config.track_table_column_widths = self._track_table.column_widths()
        config.track_table_hidden_columns = self._track_table.hidden_columns()
        config.track_table_column_order = self._track_table.column_order()
        config.session_paths = [audio_file.path for audio_file in self._audio_files.values()]
        self._config_service.save()
        self._discord_presence.stop()
        super().closeEvent(event)

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        # File
        file_menu = menu_bar.addMenu("&File")
        self._open_action = QAction("Add File...", self)
        self._open_action.setShortcut(QKeySequence.StandardKey.Open)
        self._open_action.triggered.connect(self._on_add_files_clicked)
        file_menu.addAction(self._open_action)

        self._add_folder_action = QAction("Add Folder...", self)
        self._add_folder_action.setShortcut("Ctrl+Shift+O")
        self._add_folder_action.triggered.connect(self._on_add_folder_clicked)
        file_menu.addAction(self._add_folder_action)

        self._delete_action = QAction("Delete File", self)
        self._delete_action.setShortcut("Ctrl+W")
        self._delete_action.triggered.connect(self._on_delete_selected_file)
        file_menu.addAction(self._delete_action)

        file_menu.addSeparator()

        self._conversion_settings_action = QAction("Convert Settings...", self)
        self._conversion_settings_action.setShortcut("Ctrl+Shift+P")
        self._conversion_settings_action.triggered.connect(self._on_conversion_settings_clicked)
        file_menu.addAction(self._conversion_settings_action)

        self._process_action = QAction("Convert Selected Audio...", self)
        self._process_action.setShortcut("Ctrl+R")
        self._process_action.setEnabled(False)
        self._process_action.triggered.connect(self._on_process_clicked)
        file_menu.addAction(self._process_action)

        self._cancel_action = QAction("Cancel All", self)
        self._cancel_action.setShortcut("Ctrl+Shift+C")
        self._cancel_action.triggered.connect(self._on_cancel_clicked)
        file_menu.addAction(self._cancel_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit
        edit_menu = menu_bar.addMenu("&Edit")
        self._undo_action = QAction("Undo", self)
        self._undo_action.setShortcut("Ctrl+Z")
        self._undo_action.setEnabled(False)
        self._undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(self._undo_action)

        self._redo_action = QAction("Redo", self)
        self._redo_action.setShortcut("Ctrl+Y")
        self._redo_action.setEnabled(False)
        self._redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(self._redo_action)
        edit_menu.addSeparator()

        sort_menu = edit_menu.addMenu("Sort By")
        self._sort_track_no_action = QAction("Track No", self)
        self._sort_track_no_action.triggered.connect(lambda: self._track_table.sort_by("track_no"))
        sort_menu.addAction(self._sort_track_no_action)

        self._sort_filename_action = QAction("Title", self)
        self._sort_filename_action.triggered.connect(lambda: self._track_table.sort_by("title"))
        sort_menu.addAction(self._sort_filename_action)

        self._sort_artist_action = QAction("Artist", self)
        self._sort_artist_action.triggered.connect(lambda: self._track_table.sort_by("artist"))
        sort_menu.addAction(self._sort_artist_action)

        self._sort_album_action = QAction("Album", self)
        self._sort_album_action.triggered.connect(lambda: self._track_table.sort_by("album"))
        sort_menu.addAction(self._sort_album_action)

        self._edit_metadata_action = QAction("Edit Selected Metadata...", self)
        self._edit_metadata_action.setShortcut("Ctrl+E")
        self._edit_metadata_action.triggered.connect(self._on_edit_metadata_clicked)
        edit_menu.addAction(self._edit_metadata_action)

        self._settings_action = QAction("Settings...", self)
        self._settings_action.setShortcut("Ctrl+,")
        self._settings_action.triggered.connect(self._on_settings_clicked)
        edit_menu.addAction(self._settings_action)

        # View
        view_menu = menu_bar.addMenu("&View")
        self._toggle_log_action = QAction("Show Output Log", self)
        self._toggle_log_action.setShortcut("Ctrl+/")
        self._toggle_log_action.setCheckable(True)
        self._toggle_log_action.setChecked(False)
        self._toggle_log_action.triggered.connect(self._on_toggle_log)
        view_menu.addAction(self._toggle_log_action)

        view_menu.addSeparator()
        self._reset_columns_action = QAction("Reset Column Widths", self)
        self._reset_columns_action.setShortcut("Ctrl+>")
        self._reset_columns_action.triggered.connect(self._on_reset_column_widths_clicked)
        view_menu.addAction(self._reset_columns_action)

        # Help
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("About FFTool", self)
        about_action.setShortcut("Ctrl+H")
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _build_ui(self) -> None:
        self._build_menu_bar()

        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)

        self._splitter = QSplitter(Qt.Orientation.Vertical)

        self._track_table = TrackTable()
        self._log_viewer = LogViewer()
        self._log_viewer.hide()

        self._splitter.addWidget(self._track_table)
        self._splitter.addWidget(self._log_viewer)

        self._splitter.setStretchFactor(0, 2)
        self._splitter.setStretchFactor(1, 1)

        root_layout.addWidget(self._splitter, stretch=1)

    def _connect_signals(self) -> None:
        self._track_table.cellDoubleClicked.connect(lambda *_: self._on_edit_metadata_clicked())
        self._track_table.filesDropped.connect(self._on_files_added)

        self._track_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._track_table.customContextMenuRequested.connect(self._on_track_table_context_menu)

        self._select_all_shortcut = QShortcut(QKeySequence.StandardKey.SelectAll, self)
        self._select_all_shortcut.activated.connect(self._track_table.selectAll)

        self._delete_key_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        self._delete_key_shortcut.activated.connect(self._on_delete_selected_file)

        self._deselect_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._deselect_shortcut.activated.connect(self._track_table.clearSelection)

        jm = self._job_manager
        jm.jobStarted.connect(self._on_job_started)
        jm.jobProgress.connect(self._on_job_progress)
        jm.jobLog.connect(self._log_viewer.append_line)
        jm.jobFinished.connect(self._on_job_finished)
        jm.batchFinished.connect(self._on_batch_finished)

    def _on_track_table_context_menu(self, pos) -> None:
        has_selection = bool(self._track_table.selected_row_ids())
        menu = QMenu(self)

        add_file_action = menu.addAction(
            "Add File...",
            self._on_add_files_clicked
        )
        add_file_action.setShortcut("Ctrl+O")

        add_folder_action = menu.addAction(
            "Add Folder...",
            self._on_add_folder_clicked
        )
        add_folder_action.setShortcut("Ctrl+Shift+O")

        edit_metadata_action = menu.addAction(
            "Edit Metadata...",
            self._on_edit_metadata_clicked
        )
        edit_metadata_action.setShortcut("Ctrl+E")

        convert_action = menu.addAction(
            "Convert Selected Audio...",
            self._on_process_clicked
        )
        convert_action.setShortcut("Ctrl+R")

        delete_action = menu.addAction(
            "Delete",
            self._on_delete_selected_file
        )
        delete_action.setShortcut("Ctrl+W")

        menu.addSeparator()
        menu.addAction(self._toggle_log_action)
        menu.addAction(self._reset_columns_action)
        menu.addSeparator()

        exit_action = menu.addAction(
            "Exit", self.close
        )
        exit_action.setShortcut("Ctrl+Q")

        for action in (edit_metadata_action, convert_action, delete_action):
            action.setEnabled(has_selection)

        menu.exec(self._track_table.viewport().mapToGlobal(pos))

    # User Action
    def _make_default_conversion_settings(self) -> ConversionSettings:
        config = self._config_service.config
        return ConversionSettings(
            output_format=OutputFormat(config.default_output_format),
            sample_rate_hz=config.default_sample_rate_hz,
            bit_depth=config.default_bit_depth,
            bitrate_kbps=config.default_bitrate_kbps,
            use_soxr=config.default_use_soxr,
            soxr_precision=config.default_soxr_precision,
            flac_compression_level=config.default_flac_compression_level,
        )

    def _on_add_files_clicked(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select audio", "", "Audio Files (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.wma *.opus)"
        )
        if paths:
            self._on_files_added(collect_audio_files(paths))

    def _on_add_folder_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if not folder:
            return

        found = collect_audio_files([folder])
        if not found:
            QMessageBox.information(
                self, "No Audio Files", "No supported audio files were found in that folder."
            )
            return

        self._on_files_added(found)

    def _on_files_added(self, paths: list[str], show_completion_message: bool = True) -> None:
        # Add the row with placeholder metadata; ffprobe fills it in asynchronously.
        # Keeps the UI responsive when adding/restoring many files.
        added_files: list[AudioFile] = []
        self._add_batch_show_message = show_completion_message
        for path in paths:
            audio_file = AudioFile(path=path)
            self._audio_files[audio_file.id] = audio_file
            self._track_table.add_file(audio_file)
            added_files.append(audio_file)

            worker = MetadataProbeWorker(audio_file.id, path, self._metadata_service)
            worker.signals.finished.connect(self._on_metadata_ready)
            self._add_batch_total += 1
            self._add_batch_pending += 1
            self._metadata_pool.start(worker)

        logger.info("Adding %d files to the batch", len(paths))
        self._update_file_dependent_actions()

        if added_files:
            self._undo_stack.append(("add", added_files))
            self._redo_stack.clear()
            self._update_undo_redo_actions()

    def _on_metadata_ready(self, probed_audio_file: AudioFile, target_id: str) -> None:
        # Probe completed, so decrement even if the file was removed.
        self._add_batch_pending -= 1

        audio_file = self._audio_files.get(target_id)
        if audio_file is not None:
            audio_file.metadata = probed_audio_file.metadata
            audio_file.duration_seconds = probed_audio_file.duration_seconds
            audio_file.bitrate_kbps = probed_audio_file.bitrate_kbps
            audio_file.sample_rate_hz = probed_audio_file.sample_rate_hz
            audio_file.codec = probed_audio_file.codec
            audio_file.file_size_bytes = probed_audio_file.file_size_bytes
            audio_file.error_message = probed_audio_file.error_message

            self._track_table.update_metadata(target_id, audio_file)

        if self._add_batch_pending <= 0 and self._add_batch_total > 0:
            if self._add_batch_show_message:
                QMessageBox.information(
                    self,
                    "Files Added",
                    f"Successfully added {self._add_batch_total} file(s) to the batch.",
                )
            self._add_batch_total = 0
            self._add_batch_pending = 0

    def _on_conversion_settings_clicked(self) -> None:
        # Optional prefill only; the dialog is always shown again when Convert is clicked. This does not skip the dialog.
        dialog = ConversionSettingsDialog(self._conversion_settings, default_output_dir=self._config_service.config.output_directory, parent=self)
        if dialog.exec():
            self._conversion_settings = dialog.get_settings()
            logger.info(
                "Updated default convert settings: format=%s, sample_rate=%s Hz",
                self._conversion_settings.output_format.value,
                self._conversion_settings.sample_rate_hz,
            )

    def _on_process_clicked(self) -> None:
        if not self._audio_files:
            QMessageBox.information(self, "Empty", "Please add audio files first.")
            return

        # Convert selected files (including DONE); skip DONE only for full-library conversion.
        selected_ids = self._track_table.selected_row_ids()
        if selected_ids:
            pending_ids = [
                file_id for file_id in selected_ids if self._audio_files.get(file_id) is not None
            ]
        else:
            pending_ids = [
                file_id
                for file_id in self._audio_files.keys()
                if self._audio_files[file_id].status != FileStatus.DONE
            ]

        if not pending_ids:
            return

        missing_files = [
            self._audio_files[file_id]
            for file_id in pending_ids
            if not Path(self._audio_files[file_id].path).is_file()
        ]
        if missing_files:
            for audio_file in missing_files:
                audio_file.mark_failed("File not found/invalid")
                self._track_table.update_status(audio_file.id, FileStatus.FAILED)

            names = "\n".join(f"- {audio_file.filename}" for audio_file in missing_files[:10])
            if len(missing_files) > 10:
                names += f"\n... and {len(missing_files) - 10} more"

            QMessageBox.warning(
                self,
                "File Not Found/Invalid",
                "Processing cannot continue because the following file(s) "
                f"no longer exist on this device:\n\n{names}\n\n"
                "Please remove them from the list or restore the files, then try again.",
            )
            return

        dialog = ConversionSettingsDialog(self._conversion_settings, default_output_dir=self._config_service.config.output_directory, parent=self)
        if not dialog.exec():
            return

        settings = dialog.get_settings()
        self._conversion_settings = settings  # The next prefill as default

        config = self._config_service.config
        output_dir = settings.custom_output_dir or config.output_directory

        jobs: list[Job] = []
        for audio_file_id in pending_ids:
            audio_file = self._audio_files[audio_file_id]
            output_path = self._metadata_service.default_output_path(
                audio_file,
                output_dir,
                config.output_suffix,
                extension=settings.file_extension(),
                custom_suffix=settings.custom_output_suffix,
            )

            job = Job(
                audio_file=audio_file,
                operation=OperationType.CONVERT,
                params=settings.to_job_params(),
                output_path=output_path,
            )
            jobs.append(job)

        if not jobs:
            return

        self._conversion_progress_dialog = ConversionProgressDialog(jobs, parent=self)
        self._conversion_progress_dialog.cancelRequested.connect(self._on_cancel_clicked)
        self._conversion_progress_dialog.show()

        self._process_action.setEnabled(False)
        self._cancel_action.setEnabled(True)
        self._batch_convert_total = len(jobs)
        self._batch_convert_success = 0
        self._discord_presence.update(
            PresenceState(
                details="Converting audio...",
                state=f"{len(jobs)} file(s)",
                large_image=_DISCORD_LARGE_IMAGE,
            )
        )
        self._job_manager.enqueue_many(jobs)

    def _on_cancel_clicked(self) -> None:
        self._job_manager.cancel_all()

    def _on_delete_selected_file(self) -> None:
        audio_file_ids = self._track_table.selected_row_ids()
        if not audio_file_ids:
            QMessageBox.information(self, "Select Files", "Please select files to remove first.")
            return

        removed_ids = self._track_table.remove_selected_rows()
        removed_files: list[AudioFile] = []
        for audio_file_id in removed_ids:
            audio_file = self._audio_files.pop(audio_file_id, None)
            if audio_file:
                removed_files.append(audio_file)

        if removed_files:
            self._undo_stack.append(("delete", removed_files))
            logger.info("Deleted %d tracks", len(removed_files))
            self._redo_stack.clear()
            self._update_undo_redo_actions()

    def _on_edit_metadata_clicked(self) -> None:
        audio_file_ids = self._track_table.selected_row_ids()
        if not audio_file_ids:
            QMessageBox.information(self, "Select Files", "Please select files from the list first.")
            return

        audio_files = [self._audio_files[fid] for fid in audio_file_ids if fid in self._audio_files]
        if not audio_files:
            return

        self._edit_files_metadata(audio_files)

    def _on_undo(self) -> None:
        if not self._undo_stack:
            return
        kind, audio_files = self._undo_stack.pop()
        if kind == "add":
            self._track_table.remove_ids([af.id for af in audio_files])
            for af in audio_files:
                self._audio_files.pop(af.id, None)
        else:  # "delete"
            for af in audio_files:
                self._audio_files[af.id] = af
                self._track_table.add_file(af)
        self._redo_stack.append((kind, audio_files))
        self._update_undo_redo_actions()

    def _on_redo(self) -> None:
        if not self._redo_stack:
            return
        kind, audio_files = self._redo_stack.pop()
        if kind == "add":
            for af in audio_files:
                self._audio_files[af.id] = af
                self._track_table.add_file(af)
        else:  # "delete"
            self._track_table.remove_ids([af.id for af in audio_files])
            for af in audio_files:
                self._audio_files.pop(af.id, None)
        self._undo_stack.append((kind, audio_files))
        self._update_undo_redo_actions()

    def _update_undo_redo_actions(self) -> None:
        self._undo_action.setEnabled(bool(self._undo_stack))
        self._redo_action.setEnabled(bool(self._redo_stack))

    def _edit_files_metadata(self, audio_files: list[AudioFile]) -> None:
        if len(audio_files) == 1:
            details = f"Editing {audio_files[0].filename} metadata"
        else:
            details = f"Editing {len(audio_files)} audio metadata"
        self._discord_presence.update(PresenceState(details=details, large_image=_DISCORD_LARGE_IMAGE))

        dialog = MetadataEditorDialog(audio_files, self._metadata_service, self._template_service, self)
        if not dialog.exec():
            self._discord_presence.update(
                PresenceState(state="Managing audio files", large_image=_DISCORD_LARGE_IMAGE)
            )
            return

        new_metadata, cover_path, cover_changed, deleted_keys, metadata_changed = dialog.get_result()
        config = self._config_service.config
        has_metadata_changes = metadata_changed or bool(deleted_keys)
        job_count = 0

        for audio_file in audio_files:
            audio_file.metadata = audio_file.metadata.merge(new_metadata)

            for key in deleted_keys:
                if key in Metadata.__dataclass_fields__:
                    setattr(audio_file.metadata, key, None)

                else:
                    audio_file.metadata.extra.pop(key, None)

            if cover_changed and cover_path:
                cover_output_path = self._metadata_service.default_output_path(
                    audio_file, config.output_directory, "_changed_cover_art"
                )

                cover_job = Job(
                    audio_file=audio_file,
                    operation=OperationType.SET_COVER,
                    params={
                        "cover_path": cover_path,
                        "deleted_metadata_keys": list(deleted_keys),
                    },
                    output_path=cover_output_path,
                )

                self._job_manager.enqueue(cover_job)
                job_count += 1

            elif has_metadata_changes:
                output_path = self._metadata_service.default_output_path(
                    audio_file, config.output_directory, "_tagged"
                )

                metadata_job = Job(
                    audio_file=audio_file,
                    operation=OperationType.APPLY_METADATA,
                    params={"deleted_metadata_keys": list(deleted_keys)} if deleted_keys else {},
                    output_path=output_path,
                )

                self._job_manager.enqueue(metadata_job)
                job_count += 1

            logger.info("Applying metadata to %s", audio_file.filename)

        if job_count == 0:
            self._discord_presence.update(
                PresenceState(state="Managing audio files", large_image=_DISCORD_LARGE_IMAGE)
            )

    def _on_settings_clicked(self) -> None:
        dialog = SettingsDialog(
            self._config_service,
            self,
            on_reset_table_layout=self._track_table.reset_layout,
        )
        if dialog.exec():
            self._job_manager.set_ffmpeg_path(self._config_service.get("ffmpeg_path"))
            self._job_manager.set_max_parallel_jobs(self._config_service.get("max_parallel_jobs"))
            self._metadata_pool.setMaxThreadCount(self._config_service.get("max_metadata_probe_threads"))

            # Apply live; start()/stop() are safe to call unconditionally.
            if self._config_service.config.enable_discord_presence:
                self._discord_presence.start()
                self._discord_presence.update(
                    PresenceState(state="Managing audio library", large_image=_DISCORD_LARGE_IMAGE)
                )
            else:
                self._discord_presence.stop()

    def _on_job_started(self, job_id: str) -> None:
    # job_id is Job.id; use job.audio_file.id to update the row.
    # One job maps to one audio_file in this MVP.
        job = self._job_manager.get_job(job_id)
        if job:
            self._track_table.update_status(job.audio_file.id, FileStatus.RUNNING)

            if job.operation == OperationType.CONVERT and self._conversion_progress_dialog is not None:
                source_name = job.audio_file.filename
                target_name = Path(job.output_path).name
                self._conversion_progress_dialog.set_current_file(source_name, target_name)

    def _on_job_progress(self, job_id: str, percent: float) -> None:
        job = self._job_manager.get_job(job_id)
        if job:
            self._track_table.update_progress(job.audio_file.id, percent)
            if job.operation == OperationType.CONVERT and self._conversion_progress_dialog is not None:
                self._conversion_progress_dialog.update_job_progress(job_id, percent)

    def _on_job_finished(self, job_id: str, success: bool, message: str) -> None:
        job = self._job_manager.get_job(job_id)
        if job:
            status = FileStatus.DONE if success else FileStatus.FAILED
            self._track_table.update_status(job.audio_file.id, status)
            self._track_table.update_progress(job.audio_file.id, 100 if success else job.audio_file.progress)
            if job.operation == OperationType.CONVERT:
                if success:
                    self._batch_convert_success += 1
                if self._conversion_progress_dialog is not None:
                    self._conversion_progress_dialog.mark_job_done()

    def _on_toggle_log(self, checked: bool) -> None:
        self._log_viewer.setVisible(checked)

    def _on_reset_column_widths_clicked(self) -> None:
        self._track_table.reset_column_widths()

    def _on_batch_finished(self) -> None:
        self._process_action.setEnabled(True)
        self._cancel_action.setEnabled(False)
        self._conversion_progress_dialog = None
        self._discord_presence.update(
            PresenceState(state="Managing audio library", large_image=_DISCORD_LARGE_IMAGE)
        )
        logger.info("Batch finished")

        if self._batch_convert_total > 0:
            self._batch_convert_total = 0
            self._batch_convert_success = 0

    def _on_about(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("About")
        box.setIcon(QMessageBox.Icon.NoIcon)
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText("""
            <div style="font-size: 10pt;">

                <h3>FFTool v1.0.0 [x64]</h3>

                <p>
                    A graphical audio processing application built with
                    <b>Python 3</b>, <b>PySide6</b>, and <b>FFmpeg/FFprobe</b>,
                    providing a simple and intuitive interface for common
                    audio processing tasks.
                </p>

                <p>
                    <b>© 2026 Audrise. All rights reserved.
                </p>

                <p>
                    License:
                    <a href="LICENSE">GNU General Public License v3.0</a><br>

                    Third-party licenses:
                    <a href="THIRD_PARTY_LICENSES.html">View licenses</a><br>

                    Source code:
                    <a href="https://github.com/Audrise/FFTool">GitHub Repository</a>
                </p>

            </div>
        """)
        box.exec()