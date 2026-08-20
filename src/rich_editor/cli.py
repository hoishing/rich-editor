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
        action="store_true",
        help="Show the version and exit",
    )
    parser.add_argument(
        "--sidebar",
        action="store_true",
        default=True,
        help="Open sidebar at startup (default)",
    )
    parser.add_argument(
        "--edit",
        action="store_true",
        help="Open markdown files in edit mode instead of preview",
    )
    parser.add_argument(
        "filename",
        nargs="?",
        help="File or folder to open; defaults to the current folder",
    )
    args = parser.parse_args()

    if args.version:
        if args.filename is not None:
            parser.error("riched --version does not take arguments")
        print(f"riched {version('riched')}")
        return 0

    path = Path.cwd() if args.filename is None else Path(args.filename).expanduser()
    root = path if path.is_dir() else path.parent

    class ConfiguredRichEditorApp(RichedApp):
        BINDINGS = build_bindings()

    ConfiguredRichEditorApp(
        path, root, show_sidebar=args.sidebar, edit_mode=args.edit
    ).run()
    return 0
