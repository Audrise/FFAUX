"""
# Service for reading and preparing metadata + cover art write operations.

Read metadata: directly via FFprobeRunner (synchronous, fast, suitable for calls
when new files are added to the batch list).

Write metadata / cover art: this service does NOT execute FFmpeg itself.
It merely prepares a Job (see core.models.job) to be executed later by the
JobManager, ensuring the write operation remains asynchronous and its progress
can be reported just like other operations. This maintains a single FFmpeg
execution path.
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

"""ffprobe tags (lowercase) that already have dedicated fields in Metadata and
are therefore NOT duplicated into Metadata.extra during reading. All other
tags found in the file (e.g., isrc, publisher, encoder, lyrics-eng, etc.)
are automatically added to Metadata.extra via Metadata.from_dict, so that
"Edit Metadata" can display all tags actually present in the file,
rather than just a list of fixed fields.
"""
_CONSUMED_TAG_KEYS = {
    "title", "artist", "album", "album_artist", "genre",
    "date", "year", "track", "disc", "comment", "composer",
}

class MetadataService:
    def __init__(self, ffprobe_runner: FFprobeRunner, ffmpeg_runner: Optional[FFmpegRunner] = None):
        self._ffprobe = ffprobe_runner
        self._ffmpeg = ffmpeg_runner

    def read_metadata(self, audio_file: AudioFile) -> AudioFile:
        """Populate `audio_file.metadata` and `duration_seconds` from the `ffprobe` output.
        Returns the same `AudioFile` object (modified in-place)
        for convenient direct use by the caller.
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

        # Metadata.from_dict will place it in Metadata.extra because it is not a dataclass field name.
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
        """
        Determine the default output path: <output_dir or source folder>/<stem><suffix><ext>.

        `extension` is optional—if provided (e.g., from
        ConversionSettings.file_extension()), it replaces the source file
        extension. This is necessary because format conversion can now
        change the extension (e.g., .flac -> .mp3), rather than simply
        preserving the original extension as before.
        """
        source = Path(audio_file.path)
        target_dir = Path(output_dir) if output_dir else source.parent
        final_extension = extension if extension is not None else source.suffix
        return str(target_dir / f"{source.stem}{suffix}{final_extension}")

    def extract_cover_art_sync(self, audio_file: AudioFile, output_dir: str) -> Optional[str]:
        """
        Extracts embedded cover art to an image file for PREVIEW purposes.

        Runs synchronously (blocking) — see trade-off notes in
        gui/dialogs/metadata_editor_dialog.py. Returns None if
        the file has no cover art or ffmpeg_runner is not set.
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
