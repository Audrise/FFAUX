from core.filename_parser import FilenameParser


def test_parse_simple_pattern():
    parser = FilenameParser()
    metadata = parser.parse("Coldplay - Yellow.mp3", "{artist} - {title}")

    assert metadata is not None
    assert metadata.artist == "Coldplay"
    assert metadata.title == "Yellow"


def test_parse_pattern_no_match_returns_none():
    parser = FilenameParser()
    metadata = parser.parse("random_file_name.mp3", "{artist} - {title}")
    assert metadata is None


def test_parse_pattern_with_track_number():
    parser = FilenameParser()
    metadata = parser.parse(
        "03. Coldplay - Parachutes - Yellow.mp3",
        "{track_number}. {artist} - {album} - {title}",
    )
    assert metadata is not None
    assert metadata.track_number == "03"
    assert metadata.artist == "Coldplay"
    assert metadata.album == "Parachutes"
    assert metadata.title == "Yellow"
