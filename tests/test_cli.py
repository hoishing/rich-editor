from __future__ import annotations

import subprocess
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path


async def test_version_flag_prints_current_version() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from riched.cli import main; raise SystemExit(main())",
            "--version",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"riched {version('riched')}\n", result.stdout
    assert result.stderr == "", result.stderr


async def test_version_flag_rejects_filename() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from riched.cli import main; raise SystemExit(main())",
            "--version",
            "notes.txt",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, result.stdout
    assert result.stdout == "", result.stdout
    assert "riched --version does not take arguments" in result.stderr, result.stderr


async def test_no_filename_opens_current_folder() -> None:
    script = """
from pathlib import Path
from riched import cli

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
    tmp = Path(tempfile.mkdtemp(prefix="riched-cli-"))
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp,
    )
    cwd = tmp.resolve()
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{cwd}|{cwd}\n", result.stdout
    assert result.stderr == "", result.stderr
