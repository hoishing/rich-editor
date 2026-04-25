from __future__ import annotations

import argparse
from pathlib import Path

from .app import RichedApp
from .keybindings import build_bindings, load_bindings


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="riched", description="A minimal Textual TUI text editor."
    )
    parser.add_argument("filename", help="File to open (created on save if missing)")
    args = parser.parse_args()

    path = Path(args.filename).expanduser()
    root = path if path.is_dir() else Path.cwd()
    bindings_map = load_bindings()

    class ConfiguredRichedApp(RichedApp):
        BINDINGS = build_bindings(bindings_map)

    ConfiguredRichedApp(path, bindings_map, root).run()
    return 0
