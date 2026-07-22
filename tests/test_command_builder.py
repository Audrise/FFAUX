from core.models.audio_file import AudioFile
from core.models.job import Job, OperationType
from ffmpeg.command_builder import build

def test_build_convert_basic():
    audio_file = AudioFile(path="input.wav")
    job = Job(
        audio_file=audio_file,
        operation=OperationType.CONVERT,
        params={"bitrate": "192k", "codec": "libmp3lame"},
        output_path="output.mp3",
    )
    args = build(job)
    assert args[:3] == ["-y", "-i", "input.wav"]
    assert "-b:a" in args and "192k" in args
    assert "-c:a" in args and "libmp3lame" in args
    assert args[-1] == "output.mp3"

def test_build_requires_output_path():
    audio_file = AudioFile(path="input.wav")
    job = Job(audio_file=audio_file, operation=OperationType.CONVERT, params={})
    try:
        build(job)
        assert False, "Seharusnya raise ValueError"
    except ValueError:
        pass

def test_build_apply_metadata():
    audio_file = AudioFile(path="input.mp3")
    audio_file.metadata.title = "Judul Lagu"
    audio_file.metadata.artist = "Artis"
    job = Job(
        audio_file=audio_file,
        operation=OperationType.APPLY_METADATA,
        output_path="output.mp3",
    )
    args = build(job)
    assert "-metadata" in args
    assert "title=Judul Lagu" in args
    assert "artist=Artis" in args

def test_build_apply_metadata_with_deleted_keys():
    audio_file = AudioFile(path="input.mp3")
    audio_file.metadata.title = "Judul Lagu"
    audio_file.metadata.artist = "Artis"
    job = Job(
        audio_file=audio_file,
        operation=OperationType.APPLY_METADATA,
        params={"deleted_metadata_keys": ["comment", "isrc"]},
        output_path="output.mp3",
    )
    args = build(job)

    assert "comment=" in args
    assert "isrc=" in args
    assert "title=Judul Lagu" in args

def test_build_apply_metadata_deleted_key_overrides_existing_value():
    """Kalau key yang dihapus KEBETULAN masih ada nilainya di
    audio_file.metadata (mis. belum sempat di-clear di memori), baris
    penghapusan (-metadata key=) harus tetap MENANG karena ditaruh
    belakangan -- FFmpeg pakai definisi -metadata terakhir untuk key sama.
    """
    audio_file = AudioFile(path="input.mp3")
    audio_file.metadata.comment = "Komentar lama"
    job = Job(
        audio_file=audio_file,
        operation=OperationType.APPLY_METADATA,
        params={"deleted_metadata_keys": ["comment"]},
        output_path="output.mp3",
    )
    args = build(job)

    comment_indices = [i for i, a in enumerate(args) if a.startswith("comment=")]
    assert comment_indices, "harus ada argumen comment="
    assert args[comment_indices[-1]] == "comment="
