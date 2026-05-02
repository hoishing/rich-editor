from __future__ import annotations

import argparse
from importlib.metadata import version
from pathlib import Path

from .app import RichedApp
from .keybindings import build_bindings


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="rich", description="A minimal Textual TUI text editor."
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show the version and exit",
    )
    parser.add_argument(
        "filename",
        nargs="?",
        help="File or folder to open; defaults to the current folder",
    )
    args = parser.parse_args()

    if args.version:
        if args.filename is not None:
            parser.error("rich --version does not take arguments")
        print(f"rich {version('rich-editor')}")
        return 0

    path = Path.cwd() if args.filename is None else Path(args.filename).expanduser()
    root = path if path.is_dir() else path.parent

    class ConfiguredRichEditorApp(RichedApp):
        BINDINGS = build_bindings()

    ConfiguredRichEditorApp(path, root).run()
    return 0
