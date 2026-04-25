from __future__ import annotations

from importlib import resources
from dataclasses import dataclass
from typing import Any

from textual.binding import Binding
import yaml


@dataclass(frozen=True)
class KeyBindingHelpGroup:
    title: str
    rows: tuple[tuple[str, str], ...]


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


def build_bindings() -> list[Binding]:
    # priority=True so configured shortcuts override TextArea built-ins.
    return [
        Binding(default, name, desc, priority=True)
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


def binding_help_groups() -> list[KeyBindingHelpGroup]:
    groups: list[KeyBindingHelpGroup] = []

    app_rows = tuple(
        (item["key"], item.get("description") or item["name"])
        for item in BINDING_SPEC["app"]["commands"]
    )
    groups.append(KeyBindingHelpGroup("App", app_rows))

    editor_rows = tuple(
        (item["key"], item.get("description") or item["action"])
        for item in BINDING_SPEC["editor"]
    )
    groups.append(KeyBindingHelpGroup("Editor", editor_rows))

    for screen, items in BINDING_SPEC["screens"].items():
        rows = tuple(
            (item["key"], item.get("description") or item["action"])
            for item in items
        )
        groups.append(KeyBindingHelpGroup(f"Screens / {screen}", rows))

    return groups
