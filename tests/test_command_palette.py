from __future__ import annotations

from inspect import isawaitable

from textual.command import CommandPalette
from textual.widgets import MarkdownViewer

from .helpers import _file_app, _key_help_rows, _press
from riched.screens import KeysHelpScreen


def _palette_app(**kwargs):
    return _file_app("palette.txt", "palette", **kwargs)[2]


def _system_commands(app) -> dict[str, object]:
    return {command.title: command for command in app.get_system_commands(app.screen)}


async def test_command_palette_button_is_hidden() -> None:
    app = _palette_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        header_icon = app.query_one("HeaderIcon")
        assert header_icon.styles.display == "none"
        assert header_icon.region.width == 0


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
    _, _, app = _file_app("README.md", "# Palette", root_is_tmp=True)
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


async def test_command_palette_items_are_sorted_alphabetically() -> None:
    app = _palette_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        titles = [command.title for command in app.get_system_commands(app.screen)]
        assert titles == sorted(titles, key=str.casefold)


async def test_keys_help_includes_command_palette_binding() -> None:
    app = _palette_app(ghostty_app_hotkey_conflicts=set())
    async with app.run_test() as pilot:
        await pilot.pause()

        app.action_show_keys_popup()
        await pilot.pause()

        rows = _key_help_rows(app)
        assert ("⌘⇧P / F1", "Command palette") in rows
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


async def test_keys_help_warns_for_ghostty_conflicted_format_document() -> None:
    app = _palette_app(ghostty_app_hotkey_conflicts={"format_document"})
    async with app.run_test() as pilot:
        await pilot.pause()

        app.action_show_keys_popup()
        await pilot.pause()

        rows = _key_help_rows(app)
        assert ("⚠️ ⌥⇧F", "Format document") in rows


async def test_command_palette_opens_from_declared_keys() -> None:
    for key in ("f1", "cmd+shift+p", "super+shift+p"):
        app = _palette_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await _press(pilot, key)
            assert CommandPalette.is_open(app), key


async def test_ctrl_p_does_not_open_command_palette() -> None:
    app = _palette_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await _press(pilot, "ctrl+p")
        assert not CommandPalette.is_open(app)
