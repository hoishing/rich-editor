from __future__ import annotations

from inspect import isawaitable
from pathlib import Path
import shutil
from typing import Any

from textual.command import CommandPalette
from textual.widgets import DirectoryTree, MarkdownViewer, Static

from .helpers import _file_app, _key_help_rows, _press, mod
from rich_editor.screens import KeysHelpScreen


def _palette_app(**kwargs):
    return _file_app("palette.txt", "palette", **kwargs)[2]


def _system_commands(app) -> dict[str, object]:
    return {command.title: command for command in app.get_system_commands(app.screen)}


def _key_help_groups(app) -> dict[str, list[tuple[str, str]]]:
    return {
        group.children[0].content: [
            (row.children[0].content, row.children[1].content)
            for row in group.query(".binding-row")
        ]
        for group in app.screen.query(".binding-group")
    }


def _find_tree_node(node: Any, path: Path) -> Any:
    target = path.resolve(strict=False)
    data = getattr(node, "data", None)
    if data is not None and Path(data.path).resolve(strict=False) == target:
        return node
    for child in node.children:
        try:
            return _find_tree_node(child, path)
        except LookupError:
            pass
    raise LookupError(path)


async def _select_tree_path(pilot: Any, app: Any, path: Path) -> DirectoryTree:
    app._show_sidebar()
    tree = app.query_one("#sidebar", DirectoryTree)
    await tree.reload()
    await pilot.pause()
    tree.focus()
    tree.move_cursor(_find_tree_node(tree.root, path))
    await pilot.pause()
    return tree


def _stub_trash(app: Any) -> list[Path]:
    trashed: list[Path] = []

    def trash_path(path: Path) -> None:
        trashed.append(path)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    app._trash_path = trash_path
    return trashed


async def test_header_shows_refresh_button_instead_of_command_palette_icon() -> None:
    app = _palette_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        refresh_button = app.query_one("#refresh-button", Static)
        assert refresh_button.content == "↻"


async def test_command_palette_omits_maximize() -> None:
    app = _palette_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        titles = {command.title for command in app.get_system_commands(app.screen)}
        assert "Maximize" not in titles
        assert "Quit" in titles


async def test_command_palette_includes_show_key_bindings() -> None:
    app = _palette_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        commands = _system_commands(app)
        assert "Show key bindings" in commands
        commands["Show key bindings"].callback()
        await pilot.pause()
        assert isinstance(app.screen, KeysHelpScreen)


async def test_command_palette_includes_toggle_markdown_preview() -> None:
    _, _, app = _file_app(
        "README.md", "# Palette", root_is_tmp=True, edit_mode=True
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        commands = _system_commands(app)
        assert "Toggle Markdown preview" in commands

        result = commands["Toggle Markdown preview"].callback()
        if isawaitable(result):
            await result
        await pilot.pause()

        assert app.query_one("#markdown-preview", MarkdownViewer).document.source == (
            "# Palette"
        )


async def test_command_palette_includes_selected_sidebar_item_trash_command() -> None:
    tmp, _, app = _file_app("palette.txt", "palette", root_is_tmp=True)
    selected = tmp / "archive"
    selected.mkdir()
    (selected / "note.txt").write_text("note")
    trashed = _stub_trash(app)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select_tree_path(pilot, app, selected)
        commands = _system_commands(app)
        title = 'Move "archive" to Trash'
        assert title in commands

        result = commands[title].callback()
        if isawaitable(result):
            await result
        await pilot.pause()

        assert isinstance(app.screen, mod.TrashPathConfirmationScreen)
        assert trashed == []
        await pilot.click("#trash")
        await pilot.pause()
        assert trashed == [selected.resolve(strict=False)]
    assert not selected.exists()


async def test_command_palette_items_are_sorted_alphabetically() -> None:
    app = _palette_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        titles = [command.title for command in app.get_system_commands(app.screen)]
        assert titles == sorted(titles, key=str.casefold)


async def test_keys_help_includes_command_palette_binding() -> None:
    app = _palette_app(ghostty_conflicted_hotkey_triggers=set())
    async with app.run_test() as pilot:
        await pilot.pause()

        app.action_show_keys_popup()
        await pilot.pause()

        rows = _key_help_rows(app)
        assert ("F1", "Command palette") in rows
        assert ("⌘Enter", "Insert line below") in rows
        assert ("⌘⇧Enter", "Insert line above") in rows
        assert ("⌘]", "Indent line") in rows
        assert ("⌘[", "Outdent line") in rows
        assert ("⌥⇧F", "Format document") in rows
        assert not any(
            modifier in key.lower()
            for key, _ in rows
            for modifier in ("cmd", "ctrl", "control", "shift")
        )


async def test_keys_help_shows_format_document_under_app() -> None:
    app = _palette_app(ghostty_conflicted_hotkey_triggers=set())
    async with app.run_test() as pilot:
        await pilot.pause()

        app.action_show_keys_popup()
        await pilot.pause()

        groups = _key_help_groups(app)
        assert ("⌥⇧F", "Format document") in groups["App"]
        assert ("⌥⇧F", "Format document") not in groups["Editor"]


async def test_keys_help_warns_for_ghostty_conflicted_format_document() -> None:
    app = _palette_app(ghostty_conflicted_hotkey_triggers={"alt+shift+f"})
    async with app.run_test() as pilot:
        await pilot.pause()

        app.action_show_keys_popup()
        await pilot.pause()

        rows = _key_help_rows(app)
        assert ("⚠️ ⌥⇧F", "Format document") in rows


async def test_keys_help_warns_for_ghostty_conflicted_undo_redo() -> None:
    app = _palette_app(
        ghostty_conflicted_hotkey_triggers={"super+z", "super+shift+z"}
    )
    async with app.run_test() as pilot:
        await pilot.pause()

        app.action_show_keys_popup()
        await pilot.pause()

        rows = _key_help_rows(app)
        assert ("⚠️ ⌘Z", "Undo") in rows
        assert ("⚠️ ⌘⇧Z", "Redo") in rows


async def test_command_palette_opens_from_declared_keys() -> None:
    app = _palette_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await _press(pilot, "f1")
        assert CommandPalette.is_open(app)


async def test_command_palette_does_not_open_from_removed_cmd_shift_p_keys() -> None:
    for key in ("cmd+shift+p", "shift+cmd+p", "super+shift+p", "shift+super+p"):
        app = _palette_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await _press(pilot, key)
            assert not CommandPalette.is_open(app), key


async def test_ctrl_p_does_not_open_command_palette() -> None:
    app = _palette_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await _press(pilot, "ctrl+p")
        assert not CommandPalette.is_open(app)
