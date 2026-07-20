from core.models.audio_file import AudioFile
from core.models.conversion_settings import ConversionSettings, OutputFormat
from core.models.job import Job, OperationType
from ffmpeg.command_builder import build


def test_flac_settings_always_include_soxr_and_preserve_streams():
    settings = ConversionSettings(output_format=OutputFormat.FLAC)
    params = settings.to_job_params()
    assert params["use_soxr"] is True
    assert params["preserve_streams"] is True
    assert params["codec"] == "flac"
    assert "flac_compression_level" in params
    assert "bitrate_kbps" not in params


def test_wav_settings_include_soxr_and_sample_fmt_but_no_compression_level():
    settings = ConversionSettings(output_format=OutputFormat.WAV, bit_depth=24)
    params = settings.to_job_params()
    assert params["use_soxr"] is True
    assert params["preserve_streams"] is True
    assert params["sample_fmt"] == "s32"
    assert params["codec"] == "pcm_s24le"
    assert "flac_compression_level" not in params  # WAV tidak punya opsi ini
    assert "bitrate_kbps" not in params


def test_mp3_settings_use_bitrate_and_have_no_soxr():
    settings = ConversionSettings(output_format=OutputFormat.MP3, bitrate_kbps=256)
    params = settings.to_job_params()
    assert params["bitrate_kbps"] == 256
    assert params["codec"] == "libmp3lame"
    assert "use_soxr" not in params
    assert "preserve_streams" not in params
    assert "sample_fmt" not in params


def test_alac_settings_have_no_bitrate_and_no_soxr():
    settings = ConversionSettings(output_format=OutputFormat.ALAC)
    params = settings.to_job_params()
    assert "bitrate_kbps" not in params
    assert "use_soxr" not in params
    assert params["codec"] == "alac"


def test_wav_codec_depends_on_bit_depth():
    settings = ConversionSettings(output_format=OutputFormat.WAV, bit_depth=24)
    assert settings.codec_name() == "pcm_s24le"

    settings16 = ConversionSettings(output_format=OutputFormat.WAV, bit_depth=16)
    assert settings16.codec_name() == "pcm_s16le"


def test_command_builder_flac_matches_given_spec_order():
    audio_file = AudioFile(path="input.wav")
    settings = ConversionSettings(
        output_format=OutputFormat.FLAC,
        sample_rate_hz=96000,
        bit_depth=24,
        soxr_precision=28,
        flac_compression_level=8,
    )
    job = Job(
        audio_file=audio_file,
        operation=OperationType.CONVERT,
        params=settings.to_job_params(),
        output_path="output.flac",
    )
    args = build(job)

    # -map 0 -map_metadata 0 -c:v copy harus ada (preserve_streams)
    assert "-map" in args
    assert args[args.index("-map") + 1] == "0"
    assert "-map_metadata" in args
    assert "-c:v" in args and "copy" in args

    # -af aresample=resampler=soxr:precision=28
    af_value = args[args.index("-af") + 1]
    assert "resampler=soxr" in af_value
    assert "precision=28" in af_value

    # -sample_fmt s32 (24-bit -> s32 container)
    assert "-sample_fmt" in args
    assert args[args.index("-sample_fmt") + 1] == "s32"

    assert "-ar" in args and "96000" in args
    assert "-c:a" in args and "flac" in args
    assert "-compression_level" in args and "8" in args

    # Tidak ada -b:a sama sekali untuk FLAC
    assert "-b:a" not in args


def test_command_builder_wav_has_no_compression_level():
    audio_file = AudioFile(path="input.wav")
    settings = ConversionSettings(output_format=OutputFormat.WAV, bit_depth=16)
    job = Job(
        audio_file=audio_file,
        operation=OperationType.CONVERT,
        params=settings.to_job_params(),
        output_path="output.wav",
    )
    args = build(job)
    assert "-compression_level" not in args
    assert "-c:a" in args and "pcm_s16le" in args
    assert "-b:a" not in args


def test_command_builder_bitrate_kbps_formats_as_kbps_string():
    audio_file = AudioFile(path="input.wav")
    settings = ConversionSettings(output_format=OutputFormat.MP3, bitrate_kbps=256)
    job = Job(
        audio_file=audio_file,
        operation=OperationType.CONVERT,
        params=settings.to_job_params(),
        output_path="output.mp3",
    )
    args = build(job)
    assert "-b:a" in args
    assert "256k" in args
    # MP3 tidak boleh punya -map/-af soxr/-sample_fmt sama sekali
    assert "-map" not in args
    assert "-af" not in args
    assert "-sample_fmt" not in args


def test_command_builder_legacy_bitrate_string_still_works():
    audio_file = AudioFile(path="input.wav")
    job = Job(
        audio_file=audio_file,
        operation=OperationType.CONVERT,
        params={"bitrate": "192k"},
        output_path="output.mp3",
    )
    args = build(job)
    assert "-b:a" in args
    assert "192k" in args
