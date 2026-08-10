from core.config_service import AppConfig, ConfigService

def test_load_creates_default_when_missing(tmp_path):
    config_path = tmp_path / "config.json"
    service = ConfigService(config_path)

    config = service.load()

    assert isinstance(config, AppConfig)
    assert config_path.exists()

def test_set_and_save_persists(tmp_path):
    config_path = tmp_path / "config.json"
    service = ConfigService(config_path)
    service.load()

    service.set("max_parallel_jobs", 4)
    service.save()

    service2 = ConfigService(config_path)
    loaded = service2.load()
    assert loaded.max_parallel_jobs == 4

def test_set_unknown_key_raises(tmp_path):
    service = ConfigService(tmp_path / "config.json")
    service.load()

    try:
        service.set("not_a_real_key", 123)
        assert False, "Should be raise KeyError"
    except KeyError:
        pass

def test_restore_session_on_launch_defaults_true(tmp_path):
    service = ConfigService(tmp_path / "config.json")
    config = service.load()
    assert config.restore_session_on_launch is True

def test_restore_session_on_launch_persists(tmp_path):
    config_path = tmp_path / "config.json"
    service = ConfigService(config_path)
    service.load()

    service.set("restore_session_on_launch", False)
    service.save()

    service2 = ConfigService(config_path)
    loaded = service2.load()
    assert loaded.restore_session_on_launch is False