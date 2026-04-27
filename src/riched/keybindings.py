from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from os import environ
from pathlib import Path
from shutil import which
from subprocess import PIPE, CompletedProcess, run
from typing import Any, Callable, Mapping

from textual.binding import Binding
import yaml

GHOSTTY_MARKDOWN_PREVIEW_TRIGGER = "super+shift+v"
GHOSTTY_CONFIG_TIMEOUT_SECONDS = 1.0


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
        (_app_help_display_key(item), item.get("description") or item["name"])
        for item in BINDING_SPEC["app"]["commands"]
    )
    groups.append(KeyBindingHelpGroup("App", app_rows))

    editor_rows = tuple(
        (_display_key(item["key"]), item.get("description") or item["action"])
        for item in BINDING_SPEC["editor"]
        if item.get("help", True)
    )
    groups.append(KeyBindingHelpGroup("Editor", editor_rows))

    for screen, items in BINDING_SPEC["screens"].items():
        rows = tuple(
            (_display_key(item["key"]), item.get("description") or item["action"])
            for item in items
        )
        groups.append(KeyBindingHelpGroup(f"Screens / {screen}", rows))

    return groups


def _display_key(key: str) -> str:
    return display_key(key)


def app_binding_display_key(action: str, key: str, *, prefer_fallback: bool) -> str:
    item = _app_command_or_none(action)
    if item is None:
        return display_key(key)
    if prefer_fallback and item.get("fallback_key"):
        return display_key(item["fallback_key"])
    return display_key(item.get("preferred_key") or key)


def _app_help_display_key(item: dict[str, Any]) -> str:
    preferred = item.get("preferred_key")
    fallback = item.get("fallback_key")
    if preferred and fallback:
        return f"{display_key(preferred)} / {display_key(fallback)}"
    return display_key(item["key"])


def _app_command_or_none(action: str) -> dict[str, Any] | None:
    for item in APP_COMMANDS:
        if item["name"] == action:
            return item
    return None


def display_key(key: str) -> str:
    keys = [part.strip() for part in key.split(",") if part.strip()]
    if not keys:
        return key

    without_super = [candidate for candidate in keys if "super" not in candidate]
    candidates = without_super or keys

    def score(candidate: str) -> tuple[int, int, int]:
        parts = candidate.split("+")
        has_cmd = "cmd" in parts
        preferred_cmd_order = not (
            "cmd" in parts
            and "shift" in parts
            and parts.index("shift") < parts.index("cmd")
        )
        preferred_alt_order = not (
            "alt" in parts
            and "shift" in parts
            and parts.index("shift") < parts.index("alt")
        )
        return (
            0 if has_cmd else 1,
            0 if preferred_cmd_order else 1,
            0 if preferred_alt_order else 1,
        )

    return min(candidates, key=score)


def ghostty_markdown_preview_hotkey_conflicted(
    env: Mapping[str, str] | None = None,
    run_command: Callable[..., CompletedProcess[str]] = run,
    find_binary: Callable[[str], str | None] = which,
) -> bool:
    env = environ if env is None else env
    if env.get("TERM_PROGRAM") != "ghostty" and env.get("TERM") != "xterm-ghostty":
        return True

    ghostty = _ghostty_binary(find_binary)
    if ghostty is None:
        return True

    try:
        result = run_command(
            [ghostty, "+show-config"],
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            timeout=GHOSTTY_CONFIG_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception:
        return True
    if result.returncode != 0:
        return True
    return _ghostty_config_has_conflict(result.stdout)


def _ghostty_binary(find_binary: Callable[[str], str | None]) -> str | None:
    app_binary = Path("/Applications/Ghostty.app/Contents/MacOS/ghostty")
    if app_binary.exists():
        return str(app_binary)
    return find_binary("ghostty")


def _ghostty_config_has_conflict(config: str) -> bool:
    saw_keybind = False
    for raw_line in config.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith("keybind"):
            continue
        saw_keybind = True
        key, _, value = line.partition("=")
        if key.strip() != "keybind":
            continue
        trigger, _, action = value.partition("=")
        if trigger.strip() != GHOSTTY_MARKDOWN_PREVIEW_TRIGGER:
            continue
        return action.strip() != "unbind"
    return True if not saw_keybind else False
