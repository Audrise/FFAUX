from unittest.mock import MagicMock

from core.metadata_service import MetadataService
from core.models.audio_file import AudioFile

def test_extract_cover_art_returns_none_without_ffmpeg_runner():
    service = MetadataService(ffprobe_runner=MagicMock())
    audio_file = AudioFile(path="song.mp3")
    audio_file.metadata.cover_art_path = "<embedded>"

    result = service.extract_cover_art_sync(audio_file, "/tmp/covers")
    assert result is None

def test_extract_cover_art_returns_none_when_no_embedded_cover():
    ffmpeg_runner = MagicMock()
    service = MetadataService(ffprobe_runner=MagicMock(), ffmpeg_runner=ffmpeg_runner)
    audio_file = AudioFile(path="song.mp3")  # cover_art_path still None

    result = service.extract_cover_art_sync(audio_file, "/tmp/covers")
    assert result is None
    ffmpeg_runner.run.assert_not_called()

def test_extract_cover_art_success(tmp_path):
    ffmpeg_runner = MagicMock()
    ffmpeg_runner.run.return_value = MagicMock(success=True)
    service = MetadataService(ffprobe_runner=MagicMock(), ffmpeg_runner=ffmpeg_runner)

    audio_file = AudioFile(path="song.mp3")
    audio_file.metadata.cover_art_path = "<embedded>"

    result = service.extract_cover_art_sync(audio_file, str(tmp_path))
    assert result is not None
    assert result.endswith("_cover.jpg")
    ffmpeg_runner.run.assert_called_once()
