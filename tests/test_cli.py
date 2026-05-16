from __future__ import annotations

import subprocess
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path


STUB_APP_SCRIPT = """
from rich_editor import cli

captured = {}

class StubApp:
    def __init__(self, path, root):
        captured["path"] = path
        captured["root"] = root

    def run(self):
        print(f"{captured['path']}|{captured['root']}")

cli.RichedApp = StubApp
raise SystemExit(cli.main())
"""


def _run_cli(*args: str, cwd: Path | None = None, script: str | None = None):
    return subprocess.run(
        [
            sys.executable,
            "-c",
            script or "from rich_editor.cli import main; raise SystemExit(main())",
            *args,
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


async def test_version_flag_prints_current_version() -> None:
    result = _run_cli("--version")
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"riched {version('riched')}\n", result.stdout
    assert result.stderr == "", result.stderr


async def test_version_flag_rejects_filename() -> None:
    result = _run_cli("--version", "notes.txt")
    assert result.returncode == 2, result.stdout
    assert result.stdout == "", result.stdout
    assert "riched --version does not take arguments" in result.stderr, result.stderr


async def test_no_filename_opens_current_folder() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="rich_editor-cli-"))
    result = _run_cli(cwd=tmp, script=STUB_APP_SCRIPT)
    cwd = tmp.resolve()
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{cwd}|{cwd}\n", result.stdout
    assert result.stderr == "", result.stderr


async def test_filename_opens_containing_folder_as_root() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="rich_editor-cli-"))
    folder = tmp / "notes"
    folder.mkdir()
    f = folder / "today.txt"
    f.write_text("today")
    result = _run_cli(str(f), cwd=tmp, script=STUB_APP_SCRIPT)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{f}|{folder}\n", result.stdout
    assert result.stderr == "", result.stderr
