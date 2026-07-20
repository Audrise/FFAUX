from ffmpeg.progress_parser import ProgressParser


def test_feed_line_accumulates_and_emits_on_progress_key():
    parser = ProgressParser(total_duration_seconds=100.0)

    assert parser.feed_line("frame=10") is None
    assert parser.feed_line("out_time_ms=50000000") is None
    state = parser.feed_line("progress=continue")

    assert state is not None
    assert state.out_time_seconds == 50.0
    assert state.is_done is False


def test_percent_calculation():
    parser = ProgressParser(total_duration_seconds=200.0)
    parser.feed_line("out_time_ms=100000000")
    state = parser.feed_line("progress=continue")

    percent = parser.percent(state)
    assert percent == 50.0


def test_percent_none_when_duration_unknown():
    parser = ProgressParser(total_duration_seconds=None)
    parser.feed_line("out_time_ms=1000000")
    state = parser.feed_line("progress=continue")

    assert parser.percent(state) is None


def test_progress_end_gives_100_percent():
    parser = ProgressParser(total_duration_seconds=60.0)
    parser.feed_line("out_time_ms=59000000")
    state = parser.feed_line("progress=end")

    assert state.is_done is True
    assert parser.percent(state) == 100.0
