from ffmpeg.ffprobe_runner import ProbeResult

_SAMPLE_RAW = {
    "format": {
        "duration": "180.5",
        "bit_rate": "192000",
        "size": "4321000",
        "tags": {"title": "Judul", "artist": "Artis"},
    },
    "streams": [
        {"codec_type": "audio", "codec_name": "flac", "sample_rate": "44100"},
    ],
}

def test_sample_rate_hz_parsed_from_audio_stream():
    result = ProbeResult(success=True, raw=_SAMPLE_RAW)
    assert result.sample_rate_hz == 44100

def test_sample_rate_hz_none_when_no_audio_stream():
    result = ProbeResult(success=True, raw={"format": {}, "streams": []})
    assert result.sample_rate_hz is None

def test_bit_rate_kbps_and_codec_and_size():
    result = ProbeResult(success=True, raw=_SAMPLE_RAW)
    assert result.bit_rate_kbps == 192
    assert result.audio_codec_name == "flac"
    assert result.size_bytes == 4321000
