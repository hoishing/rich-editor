from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from textual.binding import Binding
import yaml

CONFIG_PATH = Path("~/.config/riched/keybindings.yaml").expanduser()
LEGACY_CONFIG_PATH = Path("~/.config/riched/keybindings.json").expanduser()


def load_binding_spec() -> dict[str, Any]:
    text = resources.files("riched").joinpath("bindings.yaml").read_text()
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("bindings.yaml must contain a mapping")
    return data


BINDING_SPEC = load_binding_spec()
APP_COMMANDS = BINDING_SPEC["app"]["commands"]
COMMANDS: list[tuple[str, str, str]] = [
    (item["name"], item["description"], item["key"]) for item in APP_COMMANDS
]
DEFAULT_BINDINGS: dict[str, str] = {name: key for name, _, key in COMMANDS}
COMMAND_DESCRIPTIONS: dict[str, str] = {name: desc for name, desc, _ in COMMANDS}


def _load_user_mapping(path: Path) -> dict[str, str] | None:
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    result: dict[str, str] = {}
    for name, key in data.items():
        if name in DEFAULT_BINDINGS and isinstance(key, str) and key.strip():
            result[name] = key
    return result


def _load_legacy_json_mapping(path: Path) -> dict[str, str] | None:
    try:
        data = json.loads(path.read_text())
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    result: dict[str, str] = {}
    for name, key in data.items():
        if name in DEFAULT_BINDINGS and isinstance(key, str) and key.strip():
            result[name] = key
    return result


def load_bindings() -> dict[str, str]:
    mapping = dict(DEFAULT_BINDINGS)
    if CONFIG_PATH.exists():
        overrides = _load_user_mapping(CONFIG_PATH)
        if overrides is None:
            return mapping
        mapping.update(overrides)
        return mapping
    if not LEGACY_CONFIG_PATH.exists():
        return mapping
    overrides = _load_legacy_json_mapping(LEGACY_CONFIG_PATH)
    if overrides is None:
        return mapping
    mapping.update(overrides)
    save_bindings(mapping)
    return mapping


def save_bindings(mapping: dict[str, str]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ordered = {name: mapping.get(name, default) for name, _, default in COMMANDS}
    CONFIG_PATH.write_text(yaml.safe_dump(ordered, sort_keys=False))


def build_bindings(mapping: dict[str, str]) -> list[Binding]:
    # priority=True so configured shortcuts override TextArea built-ins.
    return [
        Binding(mapping.get(name, default), name, desc, priority=True)
        for name, desc, default in COMMANDS
    ]


def build_static_bindings(section: str) -> list[Binding]:
    items = BINDING_SPEC[section]
    return [
        Binding(
            item["key"],
            item["action"],
            item.get("description", ""),
            show=item.get("show", True),
        )
        for item in items
    ]


def build_screen_bindings(screen: str) -> list[Binding]:
    items = BINDING_SPEC["screens"][screen]
    return [
        Binding(
            item["key"],
            item["action"],
            item.get("description", ""),
            show=item.get("show", True),
        )
        for item in items
    ]


def key_capture_cancel_key() -> str:
    return BINDING_SPEC["key_capture"]["cancel_key"]
