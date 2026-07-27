"""
# Discord Rich Presence integration

Wraps the `pypresence` library so the rest of the app never has to deal
with Discord IPC directly, and NEVER blocks the Qt GUI thread while
doing so all work (connecting, updating, clearing, closing) happens
on a single dedicated background thread via a simple work queue.

Design notes:
- Create an application at https://discord.com/developers/applications
   (a plain "Application", not a bot) to get a client_id.
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

except ImportError:  # pypresence is an OPTIONAL dependency
    Presence = None  # type: ignore[assignment]
    _PYPRESENCE_AVAILABLE = False

@dataclass
class PresenceState:
    """One Rich Presence update. Field names mirror pypresence's
    `Presence.update()` kwargs on purpose so callers can reason about
    them directly (see pypresence docs / Discord's Rich Presence docs
    for what each one renders as).
    """
    details: Optional[str] = None
    state: Optional[str] = None
    large_image: Optional[str] = None
    large_text: Optional[str] = None
    small_image: Optional[str] = None
    small_text: Optional[str] = None
    start_timestamp: Optional[int] = None

_STOP = object()  # sentinel put on the queue to end the worker thread

class DiscordPresenceService:
    """Example Usage
    service = DiscordPresenceService(client_id=config.discord_client_id)
    service.start()
    service.update(PresenceState(details="Converting audio...", state="3 files"))
    ...
    service.stop()
    """

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
            logger.info(
                "Discord presence disabled (pypresence not installed or no client_id configured)"
            )
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
        self._queue.put(None)  # None on the queue means "clear_presence()"

    def stop(self) -> None:
        if self._thread is None:
            return
        self._queue.put(_STOP)
        self._thread.join(timeout=2)
        self._thread = None

    def _run(self) -> None:
        """Worker thread body: connect once, then process queued updates
        one at a time. Every pypresence call happens here, off the GUI
        thread. any failure just logs and leaves the service
        disconnected instead of raising into the caller.
        """
        rpc = Presence(self._client_id)
        try:
            rpc.connect()
            self._connected = True
            logger.info("Discord presence connected")

        except Exception as exc:
            logger.info("Discord presence not connected (Discord not running?): %s", exc)
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
                logger.info("Discord presence update failed: %s", exc)

        try:
            rpc.close()

        except Exception:
            pass
        self._connected = False

    def _drain_queue_quietly(self) -> None:
        """If connect() failed, still consume whatever gets queued
        afterwards (up to and including the stop sentinel) so stop()'s
        thread.join() doesn't hang waiting on a thread that's just
        sitting there not reading from the queue.
        """
        while True:
            item = self._queue.get()
            if item is _STOP:
                return