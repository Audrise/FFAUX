"""
# A pure subprocess wrapper for running FFmpeg.

This module is intentionally designed to have no dependency on Qt whatsoever,
relying only on Python's built-in `subprocess` module. This allows it to be
tested using `unittest.mock.patch("subprocess.Popen")` without requiring a
`QApplication`.
"""
from __future__ import annotations

import sys
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
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def run(
        self,
        args: list[str],
        on_line: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        extra_args: Optional[list[str]] = None,
    ) -> RunResult:

        # Run `ffmpeg <extra_args> <args>`.
        # args: Built CLI arguments; on_line: stdout/stderr callback.
        # cancel_event: Stops the process when set.
        # extra_args: Global arguments inserted before `args`.

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
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=_windows_no_console_flag(),
            )
        except FileNotFoundError as exc:
            return RunResult(
                success=False,
                return_code=None,
                error_message=f"No FFmpeg found at '{self.ffmpeg_path}': {exc}",
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
                    error_message="Cancelled by the user.",
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
    # Take the last few lines as an error summary to display to the user.
    tail = output_lines[-max_lines:] if output_lines else []
    return "\n".join(tail) or "FFmpeg failed without output."

def _windows_no_console_flag() -> int:
    # Prevent a black console window from flashing on Windows every time
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
