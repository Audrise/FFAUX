import core.discord_presence_service as dps
from core.discord_presence_service import DiscordPresenceService, PresenceState

class _FakePresence:
    """Stand-in for pypresence.Presence -- records calls instead of
    actually talking to Discord, so this test can run without Discord
    (or pypresence) installed/running.
    """

    def __init__(self, client_id):
        self.client_id = client_id
        self.calls = []

    def connect(self):
        self.calls.append(("connect",))

    def update(self, **kwargs):
        self.calls.append(("update", kwargs))

    def clear(self):
        self.calls.append(("clear",))

    def close(self):
        self.calls.append(("close",))

class _FailingPresence(_FakePresence):
    def connect(self):
        raise ConnectionError("Discord is not running")

def _patch_presence(monkeypatch, fake_cls):
    monkeypatch.setattr(dps, "_PYPRESENCE_AVAILABLE", True)
    monkeypatch.setattr(dps, "Presence", fake_cls)

def test_is_available_false_without_client_id():
    service = DiscordPresenceService(client_id="")
    assert service.is_available is False
    # Should be a silent no-op, not an error.
    service.start()
    service.update(PresenceState(details="hello"))
    service.clear()
    service.stop()
    assert service.is_connected is False

def test_is_available_false_without_pypresence_installed(monkeypatch):
    monkeypatch.setattr(dps, "_PYPRESENCE_AVAILABLE", False)
    service = DiscordPresenceService(client_id="123456789012345678")
    assert service.is_available is False

def test_connect_update_clear_stop_sequence(monkeypatch):
    instances = []

    def factory(client_id):
        fake = _FakePresence(client_id)
        instances.append(fake)
        return fake

    _patch_presence(monkeypatch, factory)

    service = DiscordPresenceService(client_id="123456789012345678")
    service.start()
    service.update(PresenceState(details="Converting audio...", state="3 files"))
    service.clear()
    service.stop()

    assert service.is_connected is False  # stopped -> disconnected again
    assert len(instances) == 1
    fake = instances[0]
    call_names = [c[0] for c in fake.calls]
    assert call_names == ["connect", "update", "clear", "close"]

    _, update_kwargs = fake.calls[1]
    assert update_kwargs["details"] == "Converting audio..."
    assert update_kwargs["state"] == "3 files"

def test_connect_failure_does_not_hang_or_raise(monkeypatch):
    _patch_presence(monkeypatch, _FailingPresence)

    service = DiscordPresenceService(client_id="123456789012345678")
    service.start()
    service.update(PresenceState(details="should be dropped silently"))
    service.stop()  # must return promptly, not hang forever

    assert service.is_connected is False

def test_double_start_does_not_spawn_second_thread(monkeypatch):
    _patch_presence(monkeypatch, _FakePresence)

    service = DiscordPresenceService(client_id="123456789012345678")
    service.start()
    first_thread = service._thread
    service.start()  # should be a no-op
    assert service._thread is first_thread
    service.stop()