from __future__ import annotations

import argparse
from importlib.metadata import version
from pathlib import Path

from .app import RichedApp
from .keybindings import build_bindings


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="riched", description="A minimal Textual TUI text editor."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('riched')}",
    )
    parser.add_argument("filename", help="File to open (created on save if missing)")
    args = parser.parse_args()

    path = Path(args.filename).expanduser()
    root = path if path.is_dir() else Path.cwd()

    class ConfiguredRichedApp(RichedApp):
        BINDINGS = build_bindings()

    ConfiguredRichedApp(path, root).run()
    return 0
