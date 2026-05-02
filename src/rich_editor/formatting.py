from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Callable

FORMAT_TIMEOUT_SECONDS = 10.0
PYTHON_SUFFIXES = {".py", ".pyi"}
TOML_SUFFIXES = {".toml"}
XML_SUFFIXES = {".xml"}
PRETTIER_XML_PLUGIN = "@prettier/plugin-xml"
PRETTIER_XML_PLUGIN_ENTRYPOINT = Path(
    "@prettier/plugin-xml/src/plugin.js"
)


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
    if suffix in TOML_SUFFIXES:
        return _format_with_taplo(path, text, run_command, find_binary)
    if suffix in XML_SUFFIXES:
        return _format_with_prettier_xml(path, text, run_command, find_binary)
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


def _format_with_taplo(
    path: Path,
    text: str,
    run_command: RunCommand,
    find_binary: FindBinary,
) -> FormatResult:
    taplo = find_binary("taplo")
    if taplo is None:
        return FormatResult(missing_tool="taplo")
    return _run_formatter(
        [taplo, "format", "--stdin-filepath", str(path), "-"],
        text,
        run_command,
    )


def _format_with_prettier_xml(
    path: Path,
    text: str,
    run_command: RunCommand,
    find_binary: FindBinary,
) -> FormatResult:
    prettier = find_binary("prettier")
    if prettier is None:
        return FormatResult(missing_tool="prettier")

    plugin_arg = f"--plugin={_prettier_xml_plugin_path(prettier)}"
    file_info = _prettier_file_info(prettier, path, run_command, plugin_arg)
    if file_info is False:
        return FormatResult(unsupported=True)
    if isinstance(file_info, FormatResult):
        return file_info

    return _run_formatter(
        [prettier, plugin_arg, "--stdin-filepath", str(path)],
        text,
        run_command,
        missing_tool=PRETTIER_XML_PLUGIN,
    )


def _prettier_file_info(
    prettier: str,
    path: Path,
    run_command: RunCommand,
    plugin_arg: str | None = None,
) -> bool | FormatResult:
    command = [prettier]
    if plugin_arg is not None:
        command.append(plugin_arg)
    command.extend(["--file-info", str(path)])
    try:
        result = run_command(
            command,
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
        if plugin_arg is not None and _missing_node_package(
            result,
            PRETTIER_XML_PLUGIN,
        ):
            return FormatResult(missing_tool=PRETTIER_XML_PLUGIN)
        message = _command_error_message("Prettier", result)
        return FormatResult(error=message)

    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError:
        return FormatResult(error="Prettier returned invalid file info.")

    return bool(info.get("inferredParser")) and not bool(info.get("ignored"))


def _prettier_xml_plugin_path(prettier: str) -> str:
    for directory in _node_module_roots(prettier):
        plugin = directory / PRETTIER_XML_PLUGIN_ENTRYPOINT
        if plugin.exists():
            return os.fspath(plugin)
    return PRETTIER_XML_PLUGIN


def _node_module_roots(prettier: str) -> list[Path]:
    roots: list[Path] = []
    cwd_root = Path.cwd() / "node_modules"
    roots.append(cwd_root)

    try:
        resolved_prettier = Path(prettier).resolve()
    except OSError:
        resolved_prettier = Path(prettier)
    for parent in resolved_prettier.parents:
        if parent.name == "node_modules":
            roots.append(parent)
            break

    bun_global = Path.home() / ".bun/install/global/node_modules"
    roots.append(bun_global)
    return list(dict.fromkeys(roots))


def _run_formatter(
    command: list[str],
    text: str,
    run_command: RunCommand,
    *,
    missing_tool: str | None = None,
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
        if missing_tool is not None and _missing_node_package(result, missing_tool):
            return FormatResult(missing_tool=missing_tool)
        return FormatResult(error=_command_error_message(tool, result))
    return FormatResult(text=result.stdout)


def _command_error_message(tool: str, result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or result.stdout).strip()
    if not detail:
        detail = f"exit code {result.returncode}"
    return f"{tool} failed: {detail}"


def _missing_node_package(
    result: subprocess.CompletedProcess[str],
    package: str,
) -> bool:
    detail = f"{result.stderr}\n{result.stdout}"
    return package in detail and (
        "Cannot find package" in detail
        or "Cannot find module" in detail
        or "MODULE_NOT_FOUND" in detail
    )
