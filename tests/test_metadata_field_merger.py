from core.metadata_field_merger import build_field_views
from core.models.audio_file import AudioFile
from core.models.metadata import Metadata


def _file(path: str, **metadata_kwargs) -> AudioFile:
    af = AudioFile(path=path)
    af.metadata = Metadata(**metadata_kwargs)
    return af


def test_single_file_shows_all_its_tags_including_extra():
    af = _file(
        "a.mp3",
        title="Judul A",
        artist="Artis A",
        extra={"isrc": "US123", "publisher": "Label X"},
    )
    views = build_field_views([af])
    by_key = {v.key: v for v in views}

    assert by_key["title"].value == "Judul A"
    assert by_key["title"].editable is True
    assert "isrc" in by_key
    assert by_key["isrc"].value == "US123"
    assert by_key["isrc"].label == "Isrc"
    assert "publisher" in by_key


def test_only_fields_present_are_shown_not_fixed_list():
    af = _file("a.mp3", title="Judul A")
    views = build_field_views([af])
    keys = {v.key for v in views}
    # album/artist tidak diisi sama sekali -> tidak perlu tampil
    assert "album" not in keys
    assert "artist" not in keys
    assert keys == {"title"}


def test_same_value_across_selected_tracks_is_editable():
    tracks = [
        _file("a.mp3", album="Album 1"),
        _file("b.mp3", album="Album 1"),
    ]
    views = build_field_views(tracks)
    album_view = next(v for v in views if v.key == "album")
    assert album_view.editable is True
    assert album_view.value == "Album 1"


def test_differing_values_are_joined_and_read_only():
    tracks = [
        _file("a.mp3", album="Album 1", title="Lagu A"),
        _file("b.mp3", album="Album 1", title="Lagu B"),
        _file("c.mp3", album="Album 2", title="Lagu C"),
    ]
    views = build_field_views(tracks)
    by_key = {v.key: v for v in views}

    assert by_key["album"].editable is False
    assert by_key["album"].value == "Album 1 - Album 2"

    assert by_key["title"].editable is False
    assert by_key["title"].value == "Lagu A - Lagu B - Lagu C"


def test_known_fields_come_before_extra_fields_in_fixed_order():
    af = _file(
        "a.mp3",
        genre="Pop",
        title="Judul",
        extra={"isrc": "US123"},
    )
    views = build_field_views([af])
    keys = [v.key for v in views]
    assert keys.index("title") < keys.index("genre")
    assert keys.index("genre") < keys.index("isrc")


def test_empty_selection_returns_empty_list():
    assert build_field_views([]) == []


def test_can_still_edit_other_fields_when_album_differs():
    """Skenario persis yang diminta user: track a-c di Album 1, track d-f
    di Album 2 -- field Album otomatis read-only (beda), tapi field lain
    yang KEBETULAN sama (mis. genre, album_artist) tetap harus bisa
    diedit bareng, TIDAK ikut ke-lock cuma karena album beda.
    """
    tracks = [
        _file("a.mp3", album="Album 1", genre="Rock", album_artist="Band X"),
        _file("b.mp3", album="Album 1", genre="Rock", album_artist="Band X"),
        _file("c.mp3", album="Album 1", genre="Rock", album_artist="Band X"),
        _file("d.mp3", album="Album 2", genre="Rock", album_artist="Band X"),
        _file("e.mp3", album="Album 2", genre="Rock", album_artist="Band X"),
        _file("f.mp3", album="Album 2", genre="Rock", album_artist="Band X"),
    ]
    views = build_field_views(tracks)
    by_key = {v.key: v for v in views}

    assert by_key["album"].editable is False
    assert by_key["album"].value == "Album 1 - Album 2"

    # Genre & album_artist SAMA di semua track walau album-nya beda ->
    # tetap harus editable, tidak ikut ke-lock.
    assert by_key["genre"].editable is True
    assert by_key["genre"].value == "Rock"
    assert by_key["album_artist"].editable is True
    assert by_key["album_artist"].value == "Band X"
