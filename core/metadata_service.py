"""Service untuk membaca & menyiapkan operasi tulis metadata + cover art.

Baca metadata: langsung via FFprobeRunner (sinkron, cepat, cocok dipanggil
saat file baru ditambahkan ke batch list).

Tulis metadata / cover art: service ini TIDAK menjalankan FFmpeg sendiri.
Ia hanya menyiapkan Job (lihat core.models.job) yang nanti dieksekusi oleh
JobManager, supaya penulisan tetap async & progress-nya bisa dilaporkan
seperti operasi lain. Ini menjaga satu jalur eksekusi FFmpeg saja.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.models.audio_file import AudioFile
from core.models.job import Job, OperationType
from core.models.metadata import Metadata
from ffmpeg.command_builder import build as build_command
from ffmpeg.ffmpeg_runner import FFmpegRunner
from ffmpeg.ffprobe_runner import FFprobeRunner

# Tag ffprobe (huruf kecil) yang sudah punya field khusus di Metadata dan
# karenanya TIDAK diduplikasi ke Metadata.extra saat membaca. Semua tag lain
# yang ditemukan pada file (mis. isrc, publisher, encoder, lyrics-eng, dst)
# otomatis masuk ke Metadata.extra lewat Metadata.from_dict, supaya "Edit
# Metadata" bisa menampilkan seluruh tag yang benar-benar dimiliki file,
# bukan cuma daftar field tetap.
_CONSUMED_TAG_KEYS = {
    "title", "artist", "album", "album_artist", "genre",
    "date", "year", "track", "disc", "comment", "composer",
}


class MetadataService:
    def __init__(self, ffprobe_runner: FFprobeRunner, ffmpeg_runner: Optional[FFmpegRunner] = None):
        self._ffprobe = ffprobe_runner
        self._ffmpeg = ffmpeg_runner

    def read_metadata(self, audio_file: AudioFile) -> AudioFile:
        """Isi audio_file.metadata dan duration_seconds dari hasil ffprobe.

        Mengembalikan objek AudioFile yang sama (dimodifikasi in-place)
        agar mudah dipakai langsung oleh caller.
        """
        result = self._ffprobe.probe(audio_file.path)
        if not result.success:
            audio_file.error_message = result.error_message
            return audio_file

        audio_file.duration_seconds = result.duration_seconds
        audio_file.bitrate_kbps = result.bit_rate_kbps
        audio_file.sample_rate_hz = result.sample_rate_hz
        audio_file.codec = result.audio_codec_name
        audio_file.file_size_bytes = result.size_bytes

        tags = {k.lower(): v for k, v in result.tags.items()}
        data = {
            "title": tags.get("title"),
            "artist": tags.get("artist"),
            "album": tags.get("album"),
            "album_artist": tags.get("album_artist"),
            "genre": tags.get("genre"),
            "year": tags.get("date") or tags.get("year"),
            "track_number": tags.get("track"),
            "disc_number": tags.get("disc"),
            "comment": tags.get("comment"),
            "composer": tags.get("composer"),
        }
        # Tag lain di luar field yang sudah dikenal (mis. isrc, publisher,
        # encoder, lyrics-eng) ikut disertakan apa adanya -- Metadata.from_dict
        # akan menaruhnya di Metadata.extra karena bukan nama field dataclass.
        for key, value in tags.items():
            if key in _CONSUMED_TAG_KEYS:
                continue
            data[key] = value

        metadata = Metadata.from_dict(data)
        if result.has_cover_art:
            metadata.cover_art_path = "<embedded>"

        audio_file.metadata = metadata
        return audio_file

    @staticmethod
    def default_output_path(
        audio_file: AudioFile, output_dir: str, suffix: str, extension: Optional[str] = None
    ) -> str:
        """Tentukan path output default: <output_dir atau folder asal>/<stem><suffix><ext>.

        `extension` opsional -- kalau diisi (mis. dari
        ConversionSettings.file_extension()), dipakai menggantikan ekstensi
        file sumber. Ini dibutuhkan karena konversi format sekarang bisa
        mengubah ekstensi (mis. .flac -> .mp3), bukan cuma mempertahankan
        ekstensi asli seperti sebelumnya.
        """
        source = Path(audio_file.path)
        target_dir = Path(output_dir) if output_dir else source.parent
        final_extension = extension if extension is not None else source.suffix
        return str(target_dir / f"{source.stem}{suffix}{final_extension}")

    def extract_cover_art_sync(self, audio_file: AudioFile, output_dir: str) -> Optional[str]:
        """Ekstrak cover art tertanam ke file gambar, untuk keperluan PREVIEW.

        Berjalan sinkron (blocking) -- lihat catatan trade-off di
        gui/dialogs/metadata_editor_dialog.py. Mengembalikan None jika
        file tidak punya cover art atau ffmpeg_runner belum diset.
        """
        if self._ffmpeg is None:
            return None
        if audio_file.metadata.cover_art_path != "<embedded>":
            return None

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        output_path = str(Path(output_dir) / f"{Path(audio_file.path).stem}_cover.jpg")

        job = Job(
            audio_file=audio_file,
            operation=OperationType.EXTRACT_COVER,
            output_path=output_path,
        )
        args = build_command(job)
        result = self._ffmpeg.run(args)
        return output_path if result.success else None
