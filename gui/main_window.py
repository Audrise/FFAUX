"""
MainWindow HANYA bertugas: merakit widget, meneruskan aksi user ke backend
(core/*), dan memperbarui widget berdasarkan sinyal dari JobManager.
Tidak ada logika FFmpeg/parsing/metadata yang ditulis di file ini.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QMainWindow, QMenu, QMessageBox, QSplitter, QVBoxLayout, QWidget
from PySide6.QtGui import QShortcut, QKeySequence, QAction
from PySide6.QtCore import Qt

from core.config_service import ConfigService
from core.filename_parser import FilenameParser
from core.job_manager import JobManager
from core.metadata_service import MetadataService
from core.models.audio_file import AudioFile, FileStatus
from core.models.conversion_settings import ConversionSettings
from core.models.job import Job, OperationType
from core.models.metadata import Metadata
from core.template_service import TemplateService
from ffmpeg.ffprobe_runner import FFprobeRunner
from gui.dialogs.conversion_settings_dialog import ConversionSettingsDialog
from gui.dialogs.metadata_editor_dialog import MetadataEditorDialog
from gui.dialogs.settings_dialog import SettingsDialog
from gui.widgets.track_table import TrackTable
from gui.widgets.log_viewer import LogViewer
from gui.widgets.progress_panel import ProgressPanel
from utils.file_utils import collect_audio_files
from utils.logger import get_logger

logger = get_logger("gui.main_window")


class MainWindow(QMainWindow):
    def __init__(
        self,
        config_service: ConfigService,
        job_manager: JobManager,
        metadata_service: MetadataService,
        template_service: TemplateService,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("AudriseFFTool")
        self.resize(1200, 600)

        self._config_service = config_service
        self._job_manager = job_manager
        self._metadata_service = metadata_service
        self._template_service = template_service
        self._filename_parser = FilenameParser()

        self._audio_files: dict[str, AudioFile] = {}
        self._conversion_settings = ConversionSettings()

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        # =========================
        # File
        # =========================
        file_menu = menu_bar.addMenu("&File")

        self._open_action = QAction("Tambah File...", self)
        self._open_action.setShortcut(QKeySequence.StandardKey.Open)
        self._open_action.triggered.connect(self._on_add_files_clicked)
        file_menu.addAction(self._open_action)

        self._delete_action = QAction("Hapus File", self)
        self._delete_action.setShortcut("Ctrl+W")
        self._delete_action.triggered.connect(self._on_delete_selected_file)
        file_menu.addAction(self._delete_action)

        file_menu.addSeparator()

        self._conversion_settings_action = QAction("Pengaturan Konversi...", self)
        self._conversion_settings_action.setShortcut("Ctrl+Shift+P")
        self._conversion_settings_action.triggered.connect(self._on_conversion_settings_clicked)
        file_menu.addAction(self._conversion_settings_action)

        self._process_action = QAction("Convert", self)
        self._process_action.setShortcut("Ctrl+R")
        self._process_action.triggered.connect(self._on_process_clicked)
        file_menu.addAction(self._process_action)

        self._cancel_action = QAction("Batalkan Semua   ", self)
        self._cancel_action.setShortcut("Ctrl+Shift+C")
        self._cancel_action.setEnabled(False)
        self._cancel_action.triggered.connect(self._on_cancel_clicked)
        file_menu.addAction(self._cancel_action)

        file_menu.addSeparator()

        exit_action = QAction("Keluar", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)


        # =========================
        # Edit
        # =========================
        edit_menu = menu_bar.addMenu("&Edit")

        self._edit_metadata_action = QAction("Edit Metadata Terpilih...", self)
        self._edit_metadata_action.setShortcut("Ctrl+E")
        self._edit_metadata_action.triggered.connect(
            self._on_edit_metadata_clicked
        )
        edit_menu.addAction(self._edit_metadata_action)

        self._settings_action = QAction("Pengaturan...", self)
        self._settings_action.setShortcut("Ctrl+,")
        self._settings_action.triggered.connect(
            self._on_settings_clicked
        )
        edit_menu.addAction(self._settings_action)


        # =========================
        # View
        # =========================
        view_menu = menu_bar.addMenu("&View")

        self._toggle_log_action = QAction("Tampilkan Log Output", self)
        self._toggle_log_action.setCheckable(True)
        self._toggle_log_action.setChecked(False)
        self._toggle_log_action.triggered.connect(
            self._on_toggle_log
        )
        view_menu.addAction(self._toggle_log_action)


        # =========================
        # Help
        # =========================
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("Tentang AudriseFFTool", self)
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

        self._progress_panel = ProgressPanel()
        root_layout.addWidget(self._progress_panel)

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
        menu.addAction("Tambah File...", self._on_add_files_clicked)

        edit_metadata_action = menu.addAction("Edit Metadata Terpilih...", self._on_edit_metadata_clicked)
        convert_action = menu.addAction("Convert Audio Terpilih...", self._on_process_clicked)
        delete_action = menu.addAction("Hapus", self._on_delete_selected_file)
        menu.addAction(self._toggle_log_action)
        menu.addSeparator()
        menu.addAction("Keluar", self.close)

        for action in (edit_metadata_action, convert_action, delete_action):
            action.setEnabled(has_selection)

        menu.exec(self._track_table.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    # Aksi user
    # ------------------------------------------------------------------
    def _on_add_files_clicked(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Pilih audio", "", "Audio Files (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.wma *.opus)"
        )
        if paths:
            self._on_files_added(collect_audio_files(paths))

    def _on_files_added(self, paths: list[str]) -> None:
        for path in paths:
            audio_file = AudioFile(path=path)
            self._metadata_service.read_metadata(audio_file)
            self._audio_files[audio_file.id] = audio_file
            self._track_table.add_file(audio_file)
        logger.info("Menambahkan %d file ke batch", len(paths))

    def _on_conversion_settings_clicked(self) -> None:
        """Pre-set nilai default ConversionSettings lewat menu File.

        Ini OPSIONAL, cuma buat prefill -- dialog yang sama tetap akan
        SELALU muncul lagi tiap kali Convert ditekan (lihat
        _on_process_clicked), jadi ini bukan cara untuk "skip" dialog.
        """
        dialog = ConversionSettingsDialog(self._conversion_settings, self)
        if dialog.exec():
            self._conversion_settings = dialog.get_settings()
            logger.info(
                "Pengaturan konversi default diperbarui: format=%s, sample_rate=%s Hz",
                self._conversion_settings.output_format.value,
                self._conversion_settings.sample_rate_hz,
            )

    def _on_process_clicked(self) -> None:
        if not self._audio_files:
            QMessageBox.information(self, "Kosong", "Tambahkan audio terlebih dahulu.")
            return

        # Jika ada baris yang dipilih, proses hanya yang terpilih (mendukung
        # multi-select). Jika tidak ada seleksi, proses seluruh batch.
        selected_ids = self._track_table.selected_row_ids()
        target_ids = selected_ids if selected_ids else list(self._audio_files.keys())
        pending_ids = [
            file_id
            for file_id in target_ids
            if self._audio_files.get(file_id) is not None
            and self._audio_files[file_id].status != FileStatus.DONE
        ]
        if not pending_ids:
            return

        dialog = ConversionSettingsDialog(self._conversion_settings, self)
        if not dialog.exec():
            return

        settings = dialog.get_settings()
        self._conversion_settings = settings  # jadi default prefill berikutnya

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

        self._progress_panel.reset(total=len(jobs))
        self._process_action.setEnabled(False)
        self._cancel_action.setEnabled(True)
        self._job_manager.enqueue_many(jobs)

    def _on_cancel_clicked(self) -> None:
        self._job_manager.cancel_all()

    def _on_delete_selected_file(self) -> None:
        audio_file_ids = self._track_table.selected_row_ids()

        if not audio_file_ids:
            QMessageBox.information(self, "Pilih File", "Pilih file yang ingin dihapus terlebih dahulu.")
            return

        removed_ids = self._track_table.remove_selected_rows()
        for audio_file_id in removed_ids:
            audio_file = self._audio_files.pop(audio_file_id, None)
            if audio_file:
                logger.info("Menghapus track: %s", audio_file.filename)

    def _on_edit_metadata_clicked(self) -> None:
        audio_file_ids = self._track_table.selected_row_ids()
        if not audio_file_ids:
            QMessageBox.information(self, "Pilih file", "Pilih file di daftar terlebih dahulu.")
            return

        audio_files = [self._audio_files[fid] for fid in audio_file_ids if fid in self._audio_files]
        if not audio_files:
            return

        # Satu dialog untuk SEMUA file terpilih sekaligus (bukan lagi
        # berurutan satu per satu). Field yang nilainya sama di semua file
        # bisa diedit dan berlaku untuk semua file terpilih; field yang
        # beda antar track ditampilkan digabung & read-only, lihat
        # core/metadata_field_merger.py serta docstring MetadataEditorDialog.
        self._edit_files_metadata(audio_files)

    def _edit_files_metadata(self, audio_files: list[AudioFile]) -> None:
        """Buka dialog edit metadata untuk satu atau banyak file sekaligus."""
        dialog = MetadataEditorDialog(audio_files, self._metadata_service, self._template_service, self)
        if not dialog.exec():
            return

        new_metadata, cover_path, cover_changed, deleted_keys = dialog.get_result()
        config = self._config_service.config

        for audio_file in audio_files:
            # merge() hanya menimpa field yang non-None di new_metadata --
            # field yang berbeda antar track (read-only, tidak disertakan
            # dialog.get_result()) otomatis mempertahankan nilai asli
            # masing-masing file.
            audio_file.metadata = audio_file.metadata.merge(new_metadata)

            # Field yang dihapus user (tombol Hapus Metadata Terpilih) --
            # dibuang juga dari objek in-memory supaya konsisten kalau
            # dialog dibuka lagi, SELAIN dikirim eksplisit ke Job di bawah
            # (job.params["deleted_metadata_keys"]) supaya ffmpeg beneran
            # meng-clear tag itu di file output lewat "-metadata key=".
            for key in deleted_keys:
                if key in Metadata.__dataclass_fields__:
                    setattr(audio_file.metadata, key, None)
                else:
                    audio_file.metadata.extra.pop(key, None)

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

            if cover_changed and cover_path:
                # BUGFIX: sebelumnya di sini cuma ada logger.info() tanpa
                # benar-benar membuat job SET_COVER -- makanya cover baru
                # yang dipilih user tidak pernah kepasang ke file output.
                # Sekarang job SET_COVER benar-benar dibuat & di-enqueue.
                #
                # Catatan: job ini jalan di atas file SUMBER asli (bukan
                # output _tagged dari job metadata di atas), karena
                # JobManager belum mendukung chaining job (output job A
                # jadi input job B) -- lihat extensibility point yang
                # sudah dicatat di README. Jadi kalau field metadata DAN
                # cover sama-sama diubah, hasilnya jadi 2 file terpisah
                # (_tagged dan _cover), bukan 1 file gabungan. Ini
                # trade-off yang sengaja diterima dulu demi cover art
                # benar-benar bisa dipasang (yang sebelumnya malah sama
                # sekali tidak jalan).
                cover_output_path = self._metadata_service.default_output_path(
                    audio_file, config.output_directory, "_cover"
                )
                cover_job = Job(
                    audio_file=audio_file,
                    operation=OperationType.SET_COVER,
                    params={"cover_path": cover_path},
                    output_path=cover_output_path,
                )
                self._job_manager.enqueue(cover_job)

            logger.info("Menerapkan metadata untuk %s", audio_file.filename)

        job_count = len(audio_files) + (len(audio_files) if cover_changed and cover_path else 0)
        self._progress_panel.reset(total=job_count)

    def _on_settings_clicked(self) -> None:
        dialog = SettingsDialog(self._config_service, self)
        if dialog.exec():
            self._job_manager.set_ffmpeg_path(self._config_service.get("ffmpeg_path"))
            self._job_manager.set_max_parallel_jobs(self._config_service.get("max_parallel_jobs"))

    # ------------------------------------------------------------------
    # Reaksi terhadap sinyal JobManager
    # ------------------------------------------------------------------
    def _on_job_started(self, job_id: str) -> None:
        # job_id di sini adalah Job.id; kita perlu audio_file.id untuk update baris.
        # Karena satu job = satu audio_file pada MVP ini, keduanya kita samakan
        # lewat lookup balik di JobManager bila perlu. Untuk kesederhanaan,
        # TrackTable di-update lewat audio_file.id yang disimpan di job.audio_file.
        job = self._job_manager.get_job(job_id)
        if job:
            self._track_table.update_status(job.audio_file.id, FileStatus.RUNNING)

    def _on_job_progress(self, job_id: str, percent: float) -> None:
        job = self._job_manager.get_job(job_id)
        if job:
            self._track_table.update_progress(job.audio_file.id, percent)
        self._progress_panel.update_job_progress(job_id, percent)

    def _on_job_finished(self, job_id: str, success: bool, message: str) -> None:
        job = self._job_manager.get_job(job_id)
        if job:
            status = FileStatus.DONE if success else FileStatus.FAILED
            self._track_table.update_status(job.audio_file.id, status)
            self._track_table.update_progress(job.audio_file.id, 100 if success else job.audio_file.progress)
        self._progress_panel.mark_job_done()

    def _on_toggle_log(self, checked: bool) -> None:
        self._log_viewer.setVisible(checked)

    def _on_batch_finished(self) -> None:
        self._process_action.setEnabled(True)
        self._cancel_action.setEnabled(False)
        logger.info("Batch selesai")

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About",
            """
            <h3>AudriseFFTool</h3>

            <p>
                A graphical user interface for audio processing built with
                <b>Python3</b>, <b>PySide6</b>, and <b>FFmpeg/FFprobe</b>,
                providing an intuitive wrapper for common audio processing tasks.
            </p>

            <p>
                GitHub:
                <a href="https://github.com/Audrise" target="_blank">Audrise</a>
            </p>

            <p>
                <b>Copyright © 2026 Audrise</b><br>
                Licensed under the GNU General Public License v3.0 (GPL-3.0).
            </p>
            """,
        )
