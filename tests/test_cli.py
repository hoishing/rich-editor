from __future__ import annotations

import subprocess
import sys
from importlib.metadata import version


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
