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

from rich_editor import syntax as syntax_mod  # noqa: E402
from rich_editor.app import RichedApp  # noqa: E402
from rich_editor.keybindings import (  # noqa: E402
    COMMANDS,
    DEFAULT_BINDINGS,
    build_bindings,
)
from rich_editor.screens import (  # noqa: E402
    CreateFileScreen,
    QuitConfirmationScreen,
    ReplaceScreen,
    TrashPathConfirmationScreen,
    UnsavedChangesScreen,
)

mod = SimpleNamespace(
    COMMANDS=COMMANDS,
    DEFAULT_BINDINGS=DEFAULT_BINDINGS,
    RichedApp=RichedApp,
    CreateFileScreen=CreateFileScreen,
    QuitConfirmationScreen=QuitConfirmationScreen,
    ReplaceScreen=ReplaceScreen,
    TrashPathConfirmationScreen=TrashPathConfirmationScreen,
    UnsavedChangesScreen=UnsavedChangesScreen,
    build_bindings=build_bindings,
)


def _fresh_env() -> tuple[Path, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="rich_editor-e2e-"))
    cfg = tmp / "config.yaml"
    syntax_mod.reset_ts_registration()
    return tmp, cfg


def _make_app(
    path: Path,
    root: Path | None = None,
    markdown_preview_hotkey_conflicted: bool | None = None,
    ghostty_conflicted_hotkey_triggers: set[str] | None = None,
    wezterm_conflicted_hotkey_triggers: set[str] | None = None,
    in_ghostty: bool | None = None,
    in_wezterm: bool | None = None,
    **init_kwargs,
):
    cls = type(
        "ConfiguredRichEditorApp",
        (mod.RichedApp,),
        {"BINDINGS": mod.build_bindings()},
    )
    app = cls(path, root or path.parent, **init_kwargs)
    # Preserve original auto-detection when not overridden, but ensure
    # WezTerm outside detection does not pollute tests that explicitly
    # configure Ghostty. Tests that pass ghostty params expect generic
    # display ("⌘⇧V") even when the runner is inside WezTerm.
    if in_ghostty is not None:
        app._in_ghostty = in_ghostty
    if in_wezterm is not None:
        app._in_wezterm = in_wezterm
    if ghostty_conflicted_hotkey_triggers is not None:
        app._ghostty_conflicted_hotkey_triggers = ghostty_conflicted_hotkey_triggers
        # When Ghostty is explicitly configured, assume WezTerm not relevant
        # unless explicitly provided, to keep footer tests stable in WezTerm env.
        if wezterm_conflicted_hotkey_triggers is None and in_wezterm is None:
            app._in_wezterm = False
            app._wezterm_conflicted_hotkey_triggers = set()
    if wezterm_conflicted_hotkey_triggers is not None:
        app._wezterm_conflicted_hotkey_triggers = wezterm_conflicted_hotkey_triggers
        if ghostty_conflicted_hotkey_triggers is None and in_ghostty is None:
            # When WezTerm explicitly configured but Ghostty not, keep Ghostty empty
            pass
    # Recompute combined if either was overridden
    if (
        ghostty_conflicted_hotkey_triggers is not None
        or wezterm_conflicted_hotkey_triggers is not None
        or in_ghostty is not None
        or in_wezterm is not None
    ):
        app._conflicted_hotkey_triggers = (
            app._ghostty_conflicted_hotkey_triggers
            | app._wezterm_conflicted_hotkey_triggers
        )
    if markdown_preview_hotkey_conflicted is not None:
        conflicts = set(app._ghostty_conflicted_hotkey_triggers)
        if markdown_preview_hotkey_conflicted:
            conflicts.add("super+shift+v")
        else:
            conflicts.discard("super+shift+v")
        app._ghostty_conflicted_hotkey_triggers = conflicts
        app._conflicted_hotkey_triggers = conflicts | getattr(
            app, "_wezterm_conflicted_hotkey_triggers", set()
        )
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
