from unittest.mock import MagicMock, patch
from ffmpeg.ffmpeg_runner import FFmpegRunner

def _mock_process(lines: list[str], return_code: int = 0):
    process = MagicMock()
    process.stdout = iter([line + "\n" for line in lines])
    process.wait.return_value = return_code
    process.returncode = return_code
    return process

@patch("ffmpeg.ffmpeg_runner.subprocess.Popen")
def test_run_success_streams_lines(mock_popen):
    mock_popen.return_value = _mock_process(["frame=1", "frame=2"], return_code=0)

    runner = FFmpegRunner(ffmpeg_path="ffmpeg")
    seen_lines = []
    result = runner.run(["-i", "in.wav", "out.mp3"], on_line=seen_lines.append)

    assert result.success is True
    assert result.return_code == 0
    assert seen_lines == ["frame=1", "frame=2"]

@patch("ffmpeg.ffmpeg_runner.subprocess.Popen")
def test_run_failure_sets_error_message(mock_popen):
    mock_popen.return_value = _mock_process(["Error: bad codec"], return_code=1)

    runner = FFmpegRunner()
    result = runner.run(["-i", "in.wav", "out.mp3"])

    assert result.success is False
    assert "bad codec" in result.error_message

@patch("ffmpeg.ffmpeg_runner.subprocess.Popen", side_effect=FileNotFoundError("not found"))
def test_run_ffmpeg_missing(mock_popen):
    runner = FFmpegRunner(ffmpeg_path="ffmpeg_not_exist")
    result = runner.run(["-i", "in.wav", "out.mp3"])

    assert result.success is False
    assert "No FFmpeg found" in result.error_message

@patch("ffmpeg.ffmpeg_runner.subprocess.Popen")
def test_run_uses_utf8_with_replace_errors_to_avoid_unicodedecodeerror(mock_popen):
    # Regression test: ensure FFmpeg UTF-8 output doesn't crash under Windows cp1252.
    mock_popen.return_value = _mock_process(["frame=1"], return_code=0)

    runner = FFmpegRunner(ffmpeg_path="ffmpeg")
    runner.run(["-i", "in.flac", "out.mp3"])

    _, kwargs = mock_popen.call_args
    assert kwargs.get("encoding") == "utf-8"
    assert kwargs.get("errors") == "replace"