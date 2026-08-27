"""
# Parse FFmpeg's real-time output to calculate progress percentage.
#
FFmpeg writes key=value lines to stdout when run with -progress pipe:1,
for example:
    frame=120
    fps=25.00
    out_time_ms=4820000
    progress=continue
    ...
    progress=end
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass
class ProgressState:
    out_time_seconds: float = 0.0
    speed: Optional[str] = None
    is_done: bool = False

class ProgressParser:
    # Stateful parser: accumulates `key=value` lines into a `ProgressState`.
    def __init__(self, total_duration_seconds: Optional[float] = None):
        self.total_duration_seconds = total_duration_seconds
        self._pending: dict[str, str] = {}

    def feed_line(self, line: str) -> Optional[ProgressState]:
        line = line.strip()
        if not line or "=" not in line:
            return None

        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        self._pending[key] = value

        if key != "progress":
            return None

        state = self._build_state(value == "end")
        self._pending = {}
        return state

    def _build_state(self, is_done: bool) -> ProgressState:
        out_time_ms = self._pending.get("out_time_ms")
        out_time_seconds = 0.0
        if out_time_ms is not None:
            try:
                out_time_seconds = max(0, int(out_time_ms)) / 1_000_000
            except ValueError:
                out_time_seconds = 0.0

        return ProgressState(
            out_time_seconds=out_time_seconds,
            speed=self._pending.get("speed"),
            is_done=is_done,
        )

    def percent(self, state: ProgressState) -> Optional[float]:
        # Calculate the percentage (0–100), or return None if the total duration is unknown.
        if not self.total_duration_seconds or self.total_duration_seconds <= 0:
            return None
        if state.is_done:
            return 100.0
        pct = (state.out_time_seconds / self.total_duration_seconds) * 100
        return max(0.0, min(100.0, pct))
