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
        assert False, "It should raise a ValueError."
    except ValueError:
        pass

def test_build_apply_metadata():
    audio_file = AudioFile(path="input.mp3")
    audio_file.metadata.title = "Song Title"
    audio_file.metadata.artist = "Artist"
    job = Job(
        audio_file=audio_file,
        operation=OperationType.APPLY_METADATA,
        output_path="output.mp3",
    )
    args = build(job)
    assert "-metadata" in args
    assert "title=Song Title" in args
    assert "artist=Artist" in args

def test_build_apply_metadata_with_deleted_keys():
    audio_file = AudioFile(path="input.mp3")
    audio_file.metadata.title = "Song Title"
    audio_file.metadata.artist = "Artist"
    job = Job(
        audio_file=audio_file,
        operation=OperationType.APPLY_METADATA,
        params={"deleted_metadata_keys": ["comment", "isrc"]},
        output_path="output.mp3",
    )
    args = build(job)

    assert "comment=" in args
    assert "isrc=" in args
    assert "title=Song Title" in args

def test_build_apply_metadata_deleted_key_overrides_existing_value():
    """If the deleted key happens to still have a value in
    audio_file.metadata (e.g., it hasn't been cleared from memory yet), the
    deletion line (-metadata key=) must still WIN because it is placed
    later—FFmpeg uses the last -metadata definition for the same key.
    """
    audio_file = AudioFile(path="input.mp3")
    audio_file.metadata.comment = "Old Comment"
    job = Job(
        audio_file=audio_file,
        operation=OperationType.APPLY_METADATA,
        params={"deleted_metadata_keys": ["comment"]},
        output_path="output.mp3",
    )
    args = build(job)

    comment_indices = [i for i, a in enumerate(args) if a.startswith("comment=")]
    assert comment_indices, "A comment argument is required="
    assert args[comment_indices[-1]] == "comment="

def test_build_set_cover_writes_current_metadata_explicitly():
    """Regression test: SET_COVER used to rely on `-map_metadata 0`, which
    only copies whatever tags are already on disk in the source file. If a
    user changed metadata AND the cover in the same action, the SET_COVER
    job's output never contained the newly edited tag values. It must now
    write the current in-memory metadata explicitly, just like
    APPLY_METADATA does.
    """
    audio_file = AudioFile(path="input.flac")
    audio_file.metadata.title = "New Title"
    audio_file.metadata.artist = "New Artist"
    job = Job(
        audio_file=audio_file,
        operation=OperationType.SET_COVER,
        params={"cover_path": "cover.jpg"},
        output_path="output.flac",
    )
    args = build(job)
    assert "-metadata" in args
    assert "title=New Title" in args
    assert "artist=New Artist" in args
    assert "-map_metadata" not in args

def test_build_set_cover_applies_deleted_keys_too():
    audio_file = AudioFile(path="input.flac")
    audio_file.metadata.comment = "Old comment"
    job = Job(
        audio_file=audio_file,
        operation=OperationType.SET_COVER,
        params={"cover_path": "cover.jpg", "deleted_metadata_keys": ["comment"]},
        output_path="output.flac",
    )
    args = build(job)
    comment_indices = [i for i, a in enumerate(args) if a.startswith("comment=")]
    assert comment_indices, "A comment argument is required.="
    assert args[comment_indices[-1]] == "comment="