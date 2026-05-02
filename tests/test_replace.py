from __future__ import annotations

from textual.command import CommandPalette
from textual.widgets import Button, Checkbox, Footer, Input, Static

from .helpers import (
    _directory_app,
    _editor,
    _file_app,
    _footer_labels,
    _key_help_rows,
    _press,
)
from riched.screens import ReplaceScreen


async def _open_replace(app, pilot) -> ReplaceScreen:
    app.action_replace()
    await pilot.pause()
    assert isinstance(app.screen, ReplaceScreen)
    return app.screen


def _set_terms(
    screen: ReplaceScreen,
    find: str,
    replace: str = "",
    *,
    regex: bool = False,
) -> None:
    screen.query_one("#replace-find", Input).value = find
    screen.query_one("#replace-with", Input).value = replace
    screen.query_one("#replace-regex", Checkbox).value = regex


def _status(screen: ReplaceScreen) -> str:
    return str(screen.query_one("#replace-status", Static).content)


async def test_ctrl_h_opens_replace_popup() -> None:
    _, _, app = _file_app("replace.txt", "one two one", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()

        await _press(pilot, "ctrl+h")

        assert isinstance(app.screen, ReplaceScreen)
        assert str(app.screen.query_one("#previous", Button).label) == "↑"
        assert str(app.screen.query_one("#next", Button).label) == "↓"
        assert app.screen.query_one("#replace-find", Input).has_focus


async def test_replace_warns_without_open_buffer() -> None:
    _, app = _directory_app()
    async with app.run_test() as pilot:
        await pilot.pause()

        await _press(pilot, "ctrl+h")

        assert not isinstance(app.screen, ReplaceScreen)


async def test_replace_footer_key_help_and_command_palette() -> None:
    _, _, app = _file_app(
        "replace.txt",
        "one",
        root_is_tmp=True,
        ghostty_conflicted_hotkey_triggers=set(),
    )
    async with app.run_test() as pilot:
        await pilot.pause()

        labels = _footer_labels(app.query_one(Footer))
        assert labels["Replace"] == "⌃H"

        app.action_show_keys_popup()
        await pilot.pause()
        assert ("⌃H", "Replace") in _key_help_rows(app)
        app.screen.dismiss(None)
        await pilot.pause()

        commands = {
            command.title: command for command in app.get_system_commands(app.screen)
        }
        assert "Replace" in commands
        commands["Replace"].callback()
        await pilot.pause()
        assert not CommandPalette.is_open(app)
        assert isinstance(app.screen, ReplaceScreen)


async def test_literal_replace_navigates_and_replaces_one_by_one() -> None:
    _, _, app = _file_app("replace.txt", "one two one", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = await _open_replace(app, pilot)
        _set_terms(screen, "one", "ONE")

        app.action_replace_next()
        assert _editor(app).selected_text == "one"
        assert _editor(app).selection.start == (0, 0)

        app.action_replace_next()
        assert _editor(app).selected_text == "one"
        assert _editor(app).selection.start == (0, 8)

        app.action_replace_next()
        assert _editor(app).selection.start == (0, 0)

        app.action_replace_previous()
        assert _editor(app).selection.start == (0, 8)

        app.action_replace_current()
        assert _editor(app).text == "one two ONE"
        assert _editor(app).selected_text == "one"
        assert _editor(app).selection.start == (0, 0)


async def test_replace_all_updates_buffer_and_marks_dirty() -> None:
    _, _, app = _file_app("replace.txt", "alpha beta alpha", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = await _open_replace(app, pilot)
        _set_terms(screen, "alpha", "omega")

        app.action_replace_all()

        assert _editor(app).text == "omega beta omega"
        assert app._is_dirty()
        assert _status(screen) == "Replaced 2 matches."


async def test_regex_replace_all_and_errors() -> None:
    _, _, app = _file_app("replace.txt", "item1 item2", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = await _open_replace(app, pilot)
        _set_terms(screen, r"item(\d)", r"thing-\1", regex=True)

        app.action_replace_all()

        assert _editor(app).text == "thing-1 thing-2"
        assert _status(screen) == "Replaced 2 matches."

        _set_terms(screen, "[", "x", regex=True)
        app.action_replace_next()
        assert _status(screen).startswith("Invalid regex:")

        _set_terms(screen, r"\b", "x", regex=True)
        app.action_replace_next()
        assert _status(screen) == "Find pattern must match at least one character."


async def test_backspace_still_deletes_text_in_editor() -> None:
    _, _, app = _file_app("replace.txt", "abc", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        editor.move_cursor((0, 3))

        await _press(pilot, "backspace")

        assert not isinstance(app.screen, ReplaceScreen)
        assert editor.text == "ab"
