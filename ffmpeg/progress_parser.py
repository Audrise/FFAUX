"""Parsing output real-time FFmpeg menjadi persentase progress.

FFmpeg dijalankan dengan flag `-progress pipe:1` sehingga ia menulis baris
key=value ke stdout, contoh:

    frame=120
    fps=25.00
    out_time_ms=4820000
    progress=continue
    ...
    progress=end

Modul ini murni parsing/kalkulasi, tanpa I/O -> mudah diuji dengan data
baris teks statis.
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
    """Stateful parser: akumulasi baris `key=value` menjadi ProgressState.

    FFmpeg menulis beberapa baris per "frame" progress, diakhiri baris
    `progress=continue` atau `progress=end`. Panggil `feed_line()` untuk
    tiap baris; parser mengembalikan ProgressState baru setiap kali sebuah
    blok selesai (yaitu saat bertemu baris `progress=...`).
    """

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
        """Hitung persentase 0-100, atau None jika durasi total tidak diketahui."""
        if not self.total_duration_seconds or self.total_duration_seconds <= 0:
            return None
        if state.is_done:
            return 100.0
        pct = (state.out_time_seconds / self.total_duration_seconds) * 100
        return max(0.0, min(100.0, pct))
