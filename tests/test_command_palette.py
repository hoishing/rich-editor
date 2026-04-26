from __future__ import annotations

from .helpers import _fresh_env, _make_app


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
