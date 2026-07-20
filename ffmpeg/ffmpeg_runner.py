"""Wrapper subprocess murni untuk menjalankan FFmpeg.

Modul ini SENGAJA tidak bergantung pada Qt sama sekali, hanya pada
`subprocess` bawaan Python. Ini yang membuatnya bisa diuji dengan
`unittest.mock.patch("subprocess.Popen")` tanpa perlu QApplication.

Komunikasi progress/log ke pemanggil dilakukan lewat callback biasa
(bukan sinyal Qt) -> pemanggil (FFmpegWorker di layer Qt) yang nanti
menerjemahkan callback ini menjadi emit sinyal.
"""
from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class RunResult:
    success: bool
    return_code: Optional[int]
    output_lines: list[str] = field(default_factory=list)
    error_message: Optional[str] = None
    cancelled: bool = False


class FFmpegRunner:
    """Menjalankan satu proses FFmpeg dan streaming outputnya baris demi baris."""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def run(
        self,
        args: list[str],
        on_line: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        extra_args: Optional[list[str]] = None,
    ) -> RunResult:
        """Jalankan `ffmpeg <extra_args> <args>`.

        Args:
            args: argumen CLI hasil dari command_builder.build().
            on_line: callback dipanggil untuk tiap baris stdout/stderr.
            cancel_event: jika di-set, proses akan di-terminate.
            extra_args: argumen global tambahan (mis. ["-progress", "pipe:1",
                "-nostats"]), disisipkan sebelum `args`.
        """
        full_args = [self.ffmpeg_path]
        if extra_args:
            full_args += extra_args
        full_args += args

        output_lines: list[str] = []

        try:
            process = subprocess.Popen(
                full_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                creationflags=_windows_no_console_flag(),
            )
        except FileNotFoundError as exc:
            return RunResult(
                success=False,
                return_code=None,
                error_message=f"FFmpeg tidak ditemukan di '{self.ffmpeg_path}': {exc}",
            )
        except OSError as exc:
            return RunResult(success=False, return_code=None, error_message=str(exc))

        assert process.stdout is not None
        for line in process.stdout:
            output_lines.append(line.rstrip("\n"))
            if on_line:
                on_line(line.rstrip("\n"))

            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                process.wait(timeout=5)
                return RunResult(
                    success=False,
                    return_code=process.returncode,
                    output_lines=output_lines,
                    cancelled=True,
                    error_message="Dibatalkan oleh pengguna",
                )

        return_code = process.wait()
        success = return_code == 0
        return RunResult(
            success=success,
            return_code=return_code,
            output_lines=output_lines,
            error_message=None if success else _last_error_hint(output_lines),
        )


def _last_error_hint(output_lines: list[str], max_lines: int = 5) -> str:
    """Ambil beberapa baris terakhir sebagai ringkasan error untuk ditampilkan user."""
    tail = output_lines[-max_lines:] if output_lines else []
    return "\n".join(tail) or "FFmpeg gagal tanpa output."


def _windows_no_console_flag() -> int:
    """Cegah munculnya jendela console hitam saat FFmpeg dijalankan di Windows."""
    import sys

    if sys.platform == "win32":
        return subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return 0
