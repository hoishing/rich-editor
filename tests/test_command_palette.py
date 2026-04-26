from __future__ import annotations

from textual.command import CommandPalette

from .helpers import _fresh_env, _make_app
from riched.screens import KeysHelpScreen


async def test_command_palette_button_is_hidden() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "palette.txt"
    f.write_text("palette")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        header_icon = app.query_one("HeaderIcon")
        assert header_icon.styles.display == "none"
        assert header_icon.region.width == 0


async def test_command_palette_omits_maximize() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "palette.txt"
    f.write_text("palette")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        titles = {command.title for command in app.get_system_commands(app.screen)}
        assert "Maximize" not in titles
        assert "Quit" in titles


async def test_command_palette_includes_show_key_bindings() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "palette.txt"
    f.write_text("palette")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        commands = {
            command.title: command
            for command in app.get_system_commands(app.screen)
        }
        assert "Show key bindings" in commands
        commands["Show key bindings"].callback()
        await pilot.pause()
        assert isinstance(app.screen, KeysHelpScreen)


async def test_f1_opens_command_palette() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "palette.txt"
    f.write_text("palette")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("f1")
        await pilot.pause()
        assert CommandPalette.is_open(app)


async def test_ctrl_p_does_not_open_command_palette() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "palette.txt"
    f.write_text("palette")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+p")
        await pilot.pause()
        assert not CommandPalette.is_open(app)
