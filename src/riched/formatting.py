from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Callable

FORMAT_TIMEOUT_SECONDS = 10.0
PYTHON_SUFFIXES = {".py", ".pyi"}


@dataclass(frozen=True)
class FormatResult:
    text: str | None = None
    error: str | None = None
    unsupported: bool = False
    missing_tool: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and not self.unsupported and self.missing_tool is None


RunCommand = Callable[..., subprocess.CompletedProcess[str]]
FindBinary = Callable[[str], str | None]


def format_text(
    path: Path,
    text: str,
    *,
    run_command: RunCommand = subprocess.run,
    find_binary: FindBinary = which,
) -> FormatResult:
    suffix = path.suffix.lower()
    if suffix in PYTHON_SUFFIXES:
        return _format_with_ruff(path, text, run_command, find_binary)
    return _format_with_prettier(path, text, run_command, find_binary)


def _format_with_ruff(
    path: Path,
    text: str,
    run_command: RunCommand,
    find_binary: FindBinary,
) -> FormatResult:
    ruff = find_binary("ruff")
    if ruff is None:
        return FormatResult(missing_tool="ruff")
    return _run_formatter(
        [ruff, "format", "--stdin-filename", str(path), "-"],
        text,
        run_command,
    )


def _format_with_prettier(
    path: Path,
    text: str,
    run_command: RunCommand,
    find_binary: FindBinary,
) -> FormatResult:
    prettier = find_binary("prettier")
    if prettier is None:
        return FormatResult(missing_tool="prettier")

    file_info = _prettier_file_info(prettier, path, run_command)
    if file_info is False:
        return FormatResult(unsupported=True)
    if isinstance(file_info, FormatResult):
        return file_info

    return _run_formatter(
        [prettier, "--stdin-filepath", str(path)],
        text,
        run_command,
    )


def _prettier_file_info(
    prettier: str,
    path: Path,
    run_command: RunCommand,
) -> bool | FormatResult:
    try:
        result = run_command(
            [prettier, "--file-info", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=FORMAT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return FormatResult(error="Prettier timed out.")
    except Exception as exc:
        return FormatResult(error=f"Prettier failed: {exc}")

    if result.returncode != 0:
        message = _command_error_message("Prettier", result)
        return FormatResult(error=message)

    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError:
        return FormatResult(error="Prettier returned invalid file info.")

    return bool(info.get("inferredParser")) and not bool(info.get("ignored"))


def _run_formatter(
    command: list[str],
    text: str,
    run_command: RunCommand,
) -> FormatResult:
    tool = Path(command[0]).name.capitalize()
    try:
        result = run_command(
            command,
            input=text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=FORMAT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return FormatResult(error=f"{tool} timed out.")
    except Exception as exc:
        return FormatResult(error=f"{tool} failed: {exc}")

    if result.returncode != 0:
        return FormatResult(error=_command_error_message(tool, result))
    return FormatResult(text=result.stdout)


def _command_error_message(tool: str, result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or result.stdout).strip()
    if not detail:
        detail = f"exit code {result.returncode}"
    return f"{tool} failed: {detail}"
