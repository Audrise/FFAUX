"""
# Discord Rich Presence integration

Wraps the pypresence library so the rest of the app never has to deal
with Discord IPC directly, and NEVER blocks the Qt GUI thread while
doing so all work (connecting, updating, clearing, closing) happens
on a single dedicated background thread via a simple work queue.

Design notes:
Create an "application" at https://discord.com/developers/applications
"""
from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Optional

from utils.logger import get_logger

logger = get_logger("core.discord_presence_service")

try:
    from pypresence import Presence
    _PYPRESENCE_AVAILABLE = True

except ImportError:
    Presence = None  # type: ignore[assignment]
    _PYPRESENCE_AVAILABLE = False

@dataclass
class PresenceState:
    # Rich Presence update; fields mirror `pypresence`'s `Presence.update()` kwargs.
    details: Optional[str] = None
    state: Optional[str] = None
    large_image: Optional[str] = None
    large_text: Optional[str] = None
    small_image: Optional[str] = None
    small_text: Optional[str] = None
    start_timestamp: Optional[int] = None

_STOP = object()  # sentinel put on the queue to end the worker thread

class DiscordPresenceService:
    # Example usage see (test_discord_presence_service.py)
    def __init__(self, client_id: str):
        self._client_id = client_id
        self._queue: "queue.Queue[object]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._connected = False

    @property
    def is_available(self) -> bool:
        # True if pypresence is installed AND a client_id is configured.
        return _PYPRESENCE_AVAILABLE and bool(self._client_id)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        if not self.is_available:
            logger.warning("Discord presence disabled (pypresence not installed or client_id not configured)")
            return
        if self._thread is not None:
            return  # already started

        self._thread = threading.Thread(target=self._run, daemon=True, name="discord-presence")
        self._thread.start()

    def update(self, state: PresenceState) -> None:
        if not self.is_available:
            return
        self._queue.put(state)

    def clear(self) -> None:
        if not self.is_available:
            return
        self._queue.put(None)  # None on the queue means clear_presence()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._queue.put(_STOP)
        self._thread.join(timeout=2)
        self._thread = None

    def _run(self) -> None:
        # Worker thread: handles queued updates in order
        # Keeps pypresence calls off the GUI thread
        rpc = Presence(self._client_id)
        try:
            rpc.connect()
            self._connected = True
            logger.info("Discord presence connected")

        except Exception as exc:
            logger.warning(exc) # Could not find Discord installed and running on this machine.
            self._connected = False
            self._drain_queue_quietly()
            return

        while True:
            item = self._queue.get()
            if item is _STOP:
                break
            try:
                if item is None:
                    rpc.clear()
                else:
                    rpc.update(
                        details=item.details,
                        state=item.state,
                        large_image=item.large_image,
                        large_text=item.large_text,
                        small_image=item.small_image,
                        small_text=item.small_text,
                        start=item.start_timestamp,
                    )

            except Exception as exc:
                logger.warning("Discord presence update failed: %s", exc)

        try:
            rpc.close()

        except Exception:
            pass
        self._connected = False

    def _drain_queue_quietly(self) -> None:
        # Keep processing the queue if connect() fails so stop() doesn't hang
        while True:
            item = self._queue.get()
            if item is _STOP:
                return