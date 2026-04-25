from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml

SETTINGS_FILENAME = "settings.yaml"


def config_dir() -> Path:
    if sys.platform == "darwin":
        return Path("~/Library/Application Support/riched").expanduser()
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home).expanduser() / "riched"
    return Path("~/.config/riched").expanduser()


def settings_path() -> Path:
    return config_dir() / SETTINGS_FILENAME


def load_settings() -> dict[str, Any]:
    path = settings_path()
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def load_theme() -> str | None:
    theme = load_settings().get("theme")
    return theme if isinstance(theme, str) and theme else None


def save_theme(theme: str) -> None:
    path = settings_path()
    settings = load_settings()
    settings["theme"] = theme
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(settings, sort_keys=False))
