from core.metadata_service import MetadataService
from core.models.audio_file import AudioFile
from unittest.mock import MagicMock

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

def test_read_metadata_preserves_original_casing_for_extra_tags():
    """Regression test: extra/custom tag KEYS (e.g. ISRC, REPLAYGAIN_TRACK_GAIN)
    must keep their ORIGINAL casing from the file, not be forced to lowercase.
    """
    probe_result = MagicMock()
    probe_result.success = True
    probe_result.duration_seconds = 100.0
    probe_result.bit_rate_kbps = 320
    probe_result.sample_rate_hz = 44100
    probe_result.audio_codec_name = "flac"
    probe_result.size_bytes = 12345
    probe_result.tags = {
        "TITLE": "Patience (Live)",
        "ARTIST": "Guns N' Roses",
        "ISRC": "US123456789",
        "REPLAYGAIN_TRACK_GAIN": "-6.5 dB",
    }
    probe_result.has_cover_art = False

    ffprobe = MagicMock()
    ffprobe.probe.return_value = probe_result
    service = MetadataService(ffprobe_runner=ffprobe)
    audio_file = AudioFile(path="song.flac")

    service.read_metadata(audio_file)

    assert audio_file.metadata.title == "Patience (Live)"
    assert audio_file.metadata.artist == "Guns N' Roses"
    assert audio_file.metadata.extra == {
        "ISRC": "US123456789",
        "REPLAYGAIN_TRACK_GAIN": "-6.5 dB",
    }

def test_read_metadata_mixed_case_known_field_still_recognized():
    """A known field reported with unusual/mixed casing (e.g. "Album_Artist")
    must still be recognized via the case-insensitive lookup, not dropped or
    duplicated into .extra."""
    probe_result = MagicMock()
    probe_result.success = True
    probe_result.duration_seconds = 100.0
    probe_result.bit_rate_kbps = 320
    probe_result.sample_rate_hz = 44100
    probe_result.audio_codec_name = "mp3"
    probe_result.size_bytes = 12345
    probe_result.tags = {"Album_Artist": "Various Artists"}
    probe_result.has_cover_art = False

    ffprobe = MagicMock()
    ffprobe.probe.return_value = probe_result
    service = MetadataService(ffprobe_runner=ffprobe)
    audio_file = AudioFile(path="song.mp3")

    service.read_metadata(audio_file)

    assert audio_file.metadata.album_artist == "Various Artists"
    assert audio_file.metadata.extra == {}