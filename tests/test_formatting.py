from __future__ import annotations

import os
from pathlib import Path

from textual.widgets import DirectoryTree

from .helpers import _editor, _file_app, _press, _temporary_env


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _formatter_bin(tmp: Path) -> Path:
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "ruff",
        """#!/bin/sh
if [ "$1" = "format" ]; then
  cat >/dev/null
  printf 'value = {"b": 1}\\n'
  exit 0
fi
exit 2
""",
    )
    _write_executable(
        bin_dir / "prettier",
        """#!/bin/sh
plugin=
case "$1" in
--plugin=*)
  plugin=xml
  shift
  ;;
esac
if [ "$1" = "--file-info" ]; then
  case "$2" in
    *.xml)
      if [ "$plugin" = "xml" ]; then
        printf '{ "ignored": false, "inferredParser": "xml" }\\n'
      else
        printf '{ "ignored": false, "inferredParser": null }\\n'
      fi
      ;;
    *.json|*.js) printf '{ "ignored": false, "inferredParser": "json" }\\n' ;;
    *) printf '{ "ignored": false, "inferredParser": null }\\n' ;;
  esac
  exit 0
fi
if [ "$1" = "--stdin-filepath" ]; then
  if echo "$2" | grep -q 'fail'; then
    printf 'formatter exploded\\n' >&2
    exit 2
  fi
  cat >/dev/null
  if [ "$plugin" = "xml" ]; then
    printf '<root>\\n  <child />\\n</root>\\n'
    exit 0
  fi
  printf '{ "a": 1 }\\n'
  exit 0
fi
exit 2
""",
    )
    _write_executable(
        bin_dir / "taplo",
        """#!/bin/sh
if [ "$1" = "format" ]; then
  cat >/dev/null
  printf 'name = "riched"\\n'
  exit 0
fi
exit 2
""",
    )
    return bin_dir


def _missing_xml_plugin_bin(tmp: Path) -> Path:
    bin_dir = _formatter_bin(tmp)
    _write_executable(
        bin_dir / "prettier",
        """#!/bin/sh
case "$1" in
--plugin=*)
  printf "Cannot find package '@prettier/plugin-xml'\\n" >&2
  exit 1
  ;;
esac
exit 2
""",
    )
    return bin_dir


async def test_format_document_uses_ruff_for_python_aliases() -> None:
    for key in ("alt+shift+f", "shift+alt+f"):
        tmp, path, app = _file_app("format.py", "value={\"b\":1}")
        bin_dir = _formatter_bin(tmp)
        with _temporary_env(PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"):
            async with app.run_test() as pilot:
                await pilot.pause()
                editor = _editor(app)
                await _press(pilot, key)
                assert editor.text == 'value = {"b": 1}\n', (key, repr(editor.text))
                assert path.read_text() == 'value={"b":1}'


async def test_format_document_refocuses_editor_so_cmd_z_undoes() -> None:
    tmp, _, app = _file_app("format.py", "value={\"b\":1}")
    bin_dir = _formatter_bin(tmp)
    with _temporary_env(PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"):
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            _ = app.query_one("#file-tree", DirectoryTree).focus()
            await pilot.pause()

            await _press(pilot, "alt+shift+f")
            await pilot.pause()

            assert app.focused is editor
            assert editor.text == 'value = {"b": 1}\n'

            await _press(pilot, "cmd+z")
            assert editor.text == 'value={"b":1}'


async def test_format_document_uses_prettier_for_supported_files() -> None:
    tmp, path, app = _file_app("format.json", '{"a":1}')
    bin_dir = _formatter_bin(tmp)
    with _temporary_env(PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"):
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            await _press(pilot, "alt+shift+f")
            assert editor.text == '{ "a": 1 }\n'
            assert path.read_text() == '{"a":1}'


async def test_format_document_uses_taplo_for_toml() -> None:
    tmp, path, app = _file_app("config.toml", 'name="riched"')
    bin_dir = _formatter_bin(tmp)
    with _temporary_env(PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"):
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            await _press(pilot, "alt+shift+f")
            assert editor.text == 'name = "riched"\n'
            assert path.read_text() == 'name="riched"'


async def test_format_document_uses_prettier_xml_plugin_for_xml() -> None:
    tmp, path, app = _file_app("document.xml", "<root><child/></root>")
    bin_dir = _formatter_bin(tmp)
    with _temporary_env(PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"):
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            await _press(pilot, "alt+shift+f")
            assert editor.text == "<root>\n  <child />\n</root>\n"
            assert path.read_text() == "<root><child/></root>"


async def test_format_document_unsupported_file_notifies_without_change() -> None:
    tmp, _, app = _file_app("notes.txt", "plain text")
    bin_dir = _formatter_bin(tmp)
    notifications: list[tuple[str, str | None]] = []
    app.notify = lambda message, **kwargs: notifications.append(
        (str(message), kwargs.get("severity"))
    )
    with _temporary_env(PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"):
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            await _press(pilot, "alt+shift+f")
            assert editor.text == "plain text"
            assert notifications == [
                ("Formatting is not supported for this file type.", "warning")
            ]


async def test_format_document_missing_formatter_notifies_without_change() -> None:
    tmp, _, app = _file_app("format.py", "value={\"b\":1}")
    empty_bin = tmp / "empty-bin"
    empty_bin.mkdir()
    notifications: list[tuple[str, str | None]] = []
    app.notify = lambda message, **kwargs: notifications.append(
        (str(message), kwargs.get("severity"))
    )
    with _temporary_env(PATH=str(empty_bin)):
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            await _press(pilot, "alt+shift+f")
            assert editor.text == 'value={"b":1}'
            assert notifications == [
                (
                    "`ruff` is required for formatting. Install it and ensure it is on PATH.",
                    "warning",
                )
            ]


async def test_format_document_missing_taplo_notifies_without_change() -> None:
    tmp, _, app = _file_app("config.toml", 'name="riched"')
    empty_bin = tmp / "empty-bin"
    empty_bin.mkdir()
    notifications: list[tuple[str, str | None]] = []
    app.notify = lambda message, **kwargs: notifications.append(
        (str(message), kwargs.get("severity"))
    )
    with _temporary_env(PATH=str(empty_bin)):
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            await _press(pilot, "alt+shift+f")
            assert editor.text == 'name="riched"'
            assert notifications == [
                (
                    "`taplo` is required for formatting. Install it and ensure it is on PATH.",
                    "warning",
                )
            ]


async def test_format_document_missing_xml_plugin_notifies_without_change() -> None:
    tmp, _, app = _file_app("document.xml", "<root><child/></root>")
    bin_dir = _missing_xml_plugin_bin(tmp)
    notifications: list[tuple[str, str | None]] = []
    app.notify = lambda message, **kwargs: notifications.append(
        (str(message), kwargs.get("severity"))
    )
    with _temporary_env(PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"):
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            await _press(pilot, "alt+shift+f")
            assert editor.text == "<root><child/></root>"
            assert notifications == [
                (
                    "`@prettier/plugin-xml` is required for formatting. "
                    "Install it and ensure Prettier can load it.",
                    "warning",
                )
            ]


async def test_format_document_formatter_failure_notifies_without_change() -> None:
    tmp, _, app = _file_app("format-fail.js", "const value={a:1}")
    bin_dir = _formatter_bin(tmp)
    notifications: list[tuple[str, str | None]] = []
    app.notify = lambda message, **kwargs: notifications.append(
        (str(message), kwargs.get("severity"))
    )
    with _temporary_env(PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"):
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            await _press(pilot, "alt+shift+f")
            assert editor.text == "const value={a:1}"
            assert notifications == [
                ("Prettier failed: formatter exploded", "error")
            ]
