from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from os import environ
from pathlib import Path
from shutil import which
from subprocess import PIPE, CompletedProcess, run
from typing import Any, Callable, Mapping

from textual.binding import Binding
from textual.keys import format_key
import yaml

GHOSTTY_CONFIG_TIMEOUT_SECONDS = 1.0
KEY_MODIFIER_SYMBOLS = {
    "cmd": "⌘",
    "super": "⌘",
    "ctrl": "⌃",
    "control": "⌃",
    "alt": "⌥",
    "option": "⌥",
    "shift": "⇧",
}
KEY_MODIFIER_ORDER = {
    "ctrl": 0,
    "control": 0,
    "super": 1,
    "cmd": 1,
    "alt": 2,
    "option": 2,
    "shift": 3,
}


@dataclass(frozen=True)
class KeyBindingHelpGroup:
    title: str
    rows: tuple[tuple[str, str, bool], ...]


def load_binding_spec() -> dict[str, Any]:
    text = resources.files("rich_editor").joinpath("bindings.yaml").read_text()
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("bindings.yaml must contain a mapping")
    return data


BINDING_SPEC = load_binding_spec()
APP_COMMANDS = BINDING_SPEC["app"]["commands"]
APP_COMMAND_BY_NAME: dict[str, dict[str, Any]] = {
    item["name"]: item for item in APP_COMMANDS
}
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
    return _build_item_bindings(BINDING_SPEC[section])


def build_screen_bindings(screen: str) -> list[Binding]:
    return _build_item_bindings(BINDING_SPEC["screens"][screen])


def _build_item_bindings(items: list[dict[str, Any]]) -> list[Binding]:
    return [
        Binding(
            item["key"],
            item["action"],
            item.get("description", ""),
            show=item.get("show", True),
        )
        for item in items
    ]


def binding_help_groups(
    conflicted_triggers: set[str] | None = None,
) -> list[KeyBindingHelpGroup]:
    conflicted_triggers = conflicted_triggers or set()
    groups: list[KeyBindingHelpGroup] = []

    categorized_app_items = [
        item
        for item in BINDING_SPEC["editor"]
        if item.get("help", True) and item.get("category") == "App"
    ]
    app_rows = tuple(
        (
            _help_display_key(item),
            item.get("description") or item["name"],
            _help_conflicted(item, conflicted_triggers),
        )
        for item in [*BINDING_SPEC["app"]["commands"], *categorized_app_items]
    )
    groups.append(KeyBindingHelpGroup("App", app_rows))

    editor_rows = tuple(
        (
            _help_display_key(item),
            item.get("description") or item["action"],
            _help_conflicted(item, conflicted_triggers),
        )
        for item in BINDING_SPEC["editor"]
        if item.get("help", True) and item.get("category") != "App"
    )
    groups.append(KeyBindingHelpGroup("Editor", editor_rows))

    for screen, items in BINDING_SPEC["screens"].items():
        rows = tuple(
            (
                _help_display_key(item),
                item.get("description") or item["action"],
                False,
            )
            for item in items
        )
        groups.append(KeyBindingHelpGroup(f"Screens / {screen}", rows))

    return groups


def app_binding_display_key(
    action: str,
    key: str,
    *,
    conflicted_triggers: set[str] | None = None,
    in_ghostty: bool = False,
    in_wezterm: bool = False,
) -> str:
    conflicted_triggers = conflicted_triggers or set()
    item = _app_command_or_none(action)
    if item is None:
        return display_key(key)
    for display_key_candidate in _item_display_keys(
        item, in_ghostty=in_ghostty, in_wezterm=in_wezterm
    ):
        display = display_key(display_key_candidate)
        if not _display_key_conflicted(display, conflicted_triggers):
            return display
    return ""


def _help_conflicted(
    item: dict[str, Any],
    conflicted_triggers: set[str],
) -> bool:
    return any(
        _display_key_conflicted(display_key(key), conflicted_triggers)
        for key in _item_display_keys(item)
    )


def _help_display_key(item: dict[str, Any]) -> str:
    return " / ".join(
        display_key_with_symbols(display_key(key))
        for key in _item_display_keys(item)
    )


def _item_display_keys(
    item: dict[str, Any], *, in_ghostty: bool = False, in_wezterm: bool = False
) -> list[str]:
    if in_ghostty:
        ghostty_display_keys = item.get("ghostty_display_keys")
        if isinstance(ghostty_display_keys, list):
            return [str(key) for key in ghostty_display_keys]
    if in_wezterm:
        wezterm_display_keys = item.get("wezterm_display_keys")
        if isinstance(wezterm_display_keys, list):
            return [str(key) for key in wezterm_display_keys]
    display_keys = item.get("display_keys")
    if isinstance(display_keys, list):
        return [str(key) for key in display_keys]
    return [str(item.get("preferred_key") or item["key"])]


def _display_key_conflicted(key: str, conflicted_triggers: set[str]) -> bool:
    return bool(_hotkey_conflict_triggers(key) & conflicted_triggers)


def _app_command_or_none(action: str) -> dict[str, Any] | None:
    return APP_COMMAND_BY_NAME.get(action)


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


def display_key_with_symbols(key: str) -> str:
    parts = key.split("+")
    if len(parts) == 1:
        return _display_base_key(parts[0])
    modifiers = "".join(KEY_MODIFIER_SYMBOLS.get(part, part) for part in parts[:-1])
    return f"{modifiers}{_display_base_key(parts[-1])}"


def _display_base_key(key: str) -> str:
    if key == "enter":
        return "Enter"
    base_key = format_key(key)
    if len(base_key) == 1:
        return base_key.upper()
    return base_key.title()


def running_in_ghostty(env: Mapping[str, str] | None = None) -> bool:
    env = environ if env is None else env
    return env.get("TERM_PROGRAM") == "ghostty" or env.get("TERM") == "xterm-ghostty"


def running_in_wezterm(env: Mapping[str, str] | None = None) -> bool:
    env = environ if env is None else env
    return env.get("TERM_PROGRAM") == "WezTerm"


def ghostty_conflicted_hotkey_triggers(
    env: Mapping[str, str] | None = None,
    run_command: Callable[..., CompletedProcess[str]] = run,
    find_binary: Callable[[str], str | None] = which,
) -> set[str]:
    triggers = _ghostty_conflict_triggers()
    env = environ if env is None else env
    if not running_in_ghostty(env):
        return set(triggers)

    ghostty = _ghostty_binary(find_binary)
    if ghostty is None:
        return set(triggers)

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
        return set(triggers)
    if result.returncode != 0:
        return set(triggers)
    conflicted_triggers = _ghostty_config_conflicted_triggers(
        result.stdout,
        triggers,
    )
    return conflicted_triggers


def ghostty_markdown_preview_hotkey_conflicted(
    env: Mapping[str, str] | None = None,
    run_command: Callable[..., CompletedProcess[str]] = run,
    find_binary: Callable[[str], str | None] = which,
) -> bool:
    return "super+shift+v" in ghostty_conflicted_hotkey_triggers(
        env,
        run_command,
        find_binary,
    )


def _ghostty_binary(find_binary: Callable[[str], str | None]) -> str | None:
    app_binary = Path("/Applications/Ghostty.app/Contents/MacOS/ghostty")
    if app_binary.exists():
        return str(app_binary)
    return find_binary("ghostty")


def _ghostty_conflict_triggers() -> set[str]:
    triggers: set[str] = set()
    for item in [*APP_COMMANDS, *BINDING_SPEC["editor"]]:
        preferred_key = item.get("preferred_key")
        if not preferred_key:
            continue
        for candidate in preferred_key.split(","):
            triggers.update(_hotkey_conflict_triggers(candidate.strip()))
    return triggers


def _hotkey_conflict_triggers(key: str) -> set[str]:
    parts = key.split("+")
    if "cmd" in parts:
        return {
            _canonical_hotkey_trigger(
                "+".join("super" if part == "cmd" else part for part in parts)
            )
        }
    if "super" in parts or "alt" in parts or "ctrl" in parts or "control" in parts:
        return {_canonical_hotkey_trigger(key)}
    return set()


def _canonical_hotkey_trigger(key: str) -> str:
    parts = key.split("+")
    modifiers = [part for part in parts[:-1] if part in KEY_MODIFIER_ORDER]
    base_parts = [part for part in parts if part not in KEY_MODIFIER_ORDER]
    ordered_modifiers = sorted(modifiers, key=lambda part: KEY_MODIFIER_ORDER[part])
    return "+".join([*ordered_modifiers, *base_parts])


def _ghostty_config_conflicted_triggers(
    config: str,
    triggers: set[str],
) -> set[str]:
    saw_keybind = False
    conflicted_triggers: set[str] = set()
    for raw_line in config.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith("keybind"):
            continue
        saw_keybind = True
        key, _, value = line.partition("=")
        if key.strip() != "keybind":
            continue
        trigger, _, action = value.partition("=")
        trigger = _canonical_hotkey_trigger(trigger.strip())
        if trigger not in triggers:
            continue
        if action.strip() != "unbind":
            conflicted_triggers.add(trigger)
    return set(triggers) if not saw_keybind else conflicted_triggers


def _ghostty_config_has_conflict(config: str) -> bool:
    return bool(
        _ghostty_config_conflicted_triggers(
            config,
            {"super+shift+v"},
        )
    )


WEZTERM_CONFIG_TIMEOUT_SECONDS = 1.0


def wezterm_conflicted_hotkey_triggers(
    env: Mapping[str, str] | None = None,
    run_command: Callable[..., CompletedProcess[str]] = run,
    find_binary: Callable[[str], str | None] = which,
) -> set[str]:
    env = environ if env is None else env
    if not running_in_wezterm(env):
        return set()
    wezterm = find_binary("wezterm")
    if wezterm is None:
        # WezTerm default binds Ctrl+Shift+V to Paste, so assume conflict
        # when we cannot inspect the config.
        return {"ctrl+shift+v"}
    try:
        result = run_command(
            [wezterm, "show-keys"],
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            timeout=WEZTERM_CONFIG_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception:
        return {"ctrl+shift+v"}
    if result.returncode != 0:
        return {"ctrl+shift+v"}
    if "PasteFrom" not in result.stdout:
        return set()
    # If show-keys still lists Ctrl+Shift+V -> Paste, it is intercepted.
    conflicted: set[str] = set()
    for line in result.stdout.splitlines():
        if "PasteFrom" not in line:
            continue
        # WezTerm show-keys lines contain e.g. "CTRL                 V" or "SHIFT | CTRL         V"
        # Any Paste binding involving V with CTRL+SHIFT implies conflict.
        if "CTRL" in line and "V" in line:
            if "SHIFT" in line or line.strip().startswith("CTRL"):
                conflicted.add("ctrl+shift+v")
                break
    return conflicted


def wezterm_markdown_preview_hotkey_conflicted(
    env: Mapping[str, str] | None = None,
    run_command: Callable[..., CompletedProcess[str]] = run,
    find_binary: Callable[[str], str | None] = which,
) -> bool:
    return "ctrl+shift+v" in wezterm_conflicted_hotkey_triggers(
        env, run_command, find_binary
    )
