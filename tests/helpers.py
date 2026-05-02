from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from textual.widgets import Footer, TextArea

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from riched import syntax as syntax_mod  # noqa: E402
from riched.app import RichedApp  # noqa: E402
from riched.keybindings import (  # noqa: E402
    COMMANDS,
    DEFAULT_BINDINGS,
    build_bindings,
)
from riched.screens import (  # noqa: E402
    CreateFileScreen,
    QuitConfirmationScreen,
    ReplaceScreen,
    UnsavedChangesScreen,
)

mod = SimpleNamespace(
    COMMANDS=COMMANDS,
    DEFAULT_BINDINGS=DEFAULT_BINDINGS,
    RichedApp=RichedApp,
    CreateFileScreen=CreateFileScreen,
    QuitConfirmationScreen=QuitConfirmationScreen,
    ReplaceScreen=ReplaceScreen,
    UnsavedChangesScreen=UnsavedChangesScreen,
    build_bindings=build_bindings,
)


def _fresh_env() -> tuple[Path, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="riched-e2e-"))
    cfg = tmp / "config.yaml"
    syntax_mod.reset_ts_registration()
    return tmp, cfg


def _make_app(
    path: Path,
    root: Path | None = None,
    markdown_preview_hotkey_conflicted: bool | None = None,
    ghostty_conflicted_hotkey_triggers: set[str] | None = None,
):
    cls = type(
        "ConfiguredRichedApp",
        (mod.RichedApp,),
        {"BINDINGS": mod.build_bindings()},
    )
    app = cls(path, root or path.parent)
    if ghostty_conflicted_hotkey_triggers is not None:
        app._ghostty_conflicted_hotkey_triggers = ghostty_conflicted_hotkey_triggers
    if markdown_preview_hotkey_conflicted is not None:
        conflicts = set(app._ghostty_conflicted_hotkey_triggers)
        if markdown_preview_hotkey_conflicted:
            conflicts.add("super+shift+v")
        else:
            conflicts.discard("super+shift+v")
        app._ghostty_conflicted_hotkey_triggers = conflicts
    return app


def _file_app(
    name: str = "test.txt",
    content: str = "",
    *,
    root_is_tmp: bool = False,
    **app_kwargs,
) -> tuple[Path, Path, RichedApp]:
    tmp, _ = _fresh_env()
    path = tmp / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    root = tmp if root_is_tmp else app_kwargs.pop("root", None)
    return tmp, path, _make_app(path, root=root, **app_kwargs)


def _directory_app(**app_kwargs) -> tuple[Path, RichedApp]:
    tmp, _ = _fresh_env()
    return tmp, _make_app(tmp, root=tmp, **app_kwargs)


def _editor(app) -> TextArea:
    return app.query_one("#editor", TextArea)


def _select(editor: TextArea, start: tuple[int, int], end: tuple[int, int]) -> None:
    editor.selection = type(editor.selection)(start, end)


async def _press(pilot, key: str) -> None:
    await pilot.press(key)
    await pilot.pause()


async def _press_many(pilot, *keys: str) -> None:
    for key in keys:
        await _press(pilot, key)


def _footer_labels(footer: Footer) -> dict[str, str]:
    return {
        child.description: child.key_display
        for child in footer.children
        if hasattr(child, "key_display")
    }


def _key_help_rows(app) -> list[tuple[str, str]]:
    return [
        (row.children[0].content, row.children[1].content)
        for row in app.screen.query(".binding-row")
    ]


@contextmanager
def _temporary_env(**updates: str | None) -> Iterator[None]:
    originals = {name: os.environ.get(name) for name in updates}
    try:
        for name, value in updates.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in originals.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
