from __future__ import annotations

import json
from pathlib import Path

from textual.binding import Binding

# (action_name, description, default_key)
COMMANDS: list[tuple[str, str, str]] = [
    ("save", "Save", "ctrl+s"),
    ("quit_check", "Quit", "ctrl+q"),
    ("open_file_menu", "File menu", "f10"),
    ("open_keybindings", "Keybindings", "ctrl+k"),
]
DEFAULT_BINDINGS: dict[str, str] = {name: key for name, _, key in COMMANDS}
COMMAND_DESCRIPTIONS: dict[str, str] = {name: desc for name, desc, _ in COMMANDS}
CONFIG_PATH = Path("~/.config/riched/keybindings.json").expanduser()


def load_bindings() -> dict[str, str]:
    mapping = dict(DEFAULT_BINDINGS)
    if not CONFIG_PATH.exists():
        return mapping
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except Exception:
        return mapping
    if not isinstance(data, dict):
        return mapping
    for name, key in data.items():
        if name in DEFAULT_BINDINGS and isinstance(key, str) and key.strip():
            mapping[name] = key
    return mapping


def save_bindings(mapping: dict[str, str]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ordered = {name: mapping.get(name, default) for name, _, default in COMMANDS}
    CONFIG_PATH.write_text(json.dumps(ordered, indent=2) + "\n")


def build_bindings(mapping: dict[str, str]) -> list[Binding]:
    # priority=True so configured shortcuts override TextArea built-ins.
    return [
        Binding(mapping.get(name, default), name, desc, priority=True)
        for name, desc, default in COMMANDS
    ]

