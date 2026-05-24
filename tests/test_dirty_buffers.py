from __future__ import annotations

from textual.widgets import Button, DirectoryTree

from .helpers import _editor, _file_app, _press, mod


def _dirty_app(name: str):
    return _file_app(name, "orig")[1:]


async def _make_dirty(app, pilot, text: str = "changed") -> None:
    _editor(app).load_text(text)
    await pilot.pause()


async def _open_quit_modal(app, pilot) -> None:
    app._show_sidebar()
    app._sidebar().focus()
    await pilot.pause()
    await _press(pilot, "escape")


async def _open_dirty_quit_modal(app, pilot) -> None:
    await _make_dirty(app, pilot)
    await _open_quit_modal(app, pilot)
    assert isinstance(app.screen, mod.UnsavedChangesScreen)


async def test_ctrl_q_does_not_quit() -> None:
    _, f, app = _file_app("clean.txt", "foo")
    async with app.run_test() as pilot:
        await pilot.pause()
        await _press(pilot, "ctrl+q")
        assert app.path == f, app.path
        assert list(app.query("#editor"))


async def test_quit_dirty_shows_modal_then_cancel() -> None:
    f, app = _dirty_app("dirty.txt")
    async with app.run_test() as pilot:
        await pilot.pause()
        await _open_dirty_quit_modal(app, pilot)
        await pilot.click("#cancel")
        await pilot.pause()
        assert not isinstance(app.screen, mod.UnsavedChangesScreen)
    assert f.read_text() == "orig"  # never overwritten


async def test_quit_dirty_save_writes_and_exits() -> None:
    f, app = _dirty_app("save.txt")
    async with app.run_test() as pilot:
        await pilot.pause()
        await _make_dirty(app, pilot, "new content")
        await _open_quit_modal(app, pilot)
        assert isinstance(app.screen, mod.UnsavedChangesScreen)
        await pilot.click("#save")
        await pilot.pause()
    assert f.read_text() == "new content"


async def test_quit_dirty_discard_keeps_file() -> None:
    f, app = _dirty_app("discard.txt")
    async with app.run_test() as pilot:
        await pilot.pause()
        await _open_dirty_quit_modal(app, pilot)
        await pilot.click("#discard")
        await pilot.pause()
    assert f.read_text() == "orig"


async def test_editor_escape_visible_sidebar_does_nothing() -> None:
    _, f, app = _file_app("editor-escape-visible.txt", "foo", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._show_sidebar()
        await pilot.pause()
        await _press(pilot, "escape")
        assert app.path == f, app.path
        assert list(app.query("#editor"))


async def test_editor_escape_hidden_sidebar_clean_shows_quit_confirmation() -> None:
    _, f, app = _file_app("editor-escape-clean.txt", "foo", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _press(pilot, "escape")
        assert isinstance(app.screen, mod.QuitConfirmationScreen)


async def test_editor_escape_hidden_sidebar_dirty_shows_unsaved_changes() -> None:
    _, f, app = _file_app("editor-escape-dirty.txt", "orig", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _make_dirty(app, pilot)
        await _press(pilot, "escape")
        assert isinstance(app.screen, mod.UnsavedChangesScreen)


async def test_sidebar_escape_clean_shows_quit_confirmation_then_cancel() -> None:
    _, f, app = _file_app("tree-escape-clean.txt", "foo", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _open_quit_modal(app, pilot)
        assert isinstance(app.screen, mod.QuitConfirmationScreen)
        await pilot.click("#cancel")
        await pilot.pause()
        assert not isinstance(app.screen, mod.QuitConfirmationScreen)
        assert app.path == f, app.path


async def test_sidebar_escape_clean_quit_exits() -> None:
    _, _, app = _file_app("tree-escape-quit.txt", "foo", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _open_quit_modal(app, pilot)
        assert isinstance(app.screen, mod.QuitConfirmationScreen)
        await pilot.click("#quit")
        await pilot.pause()


async def test_sidebar_escape_dirty_shows_unsaved_changes() -> None:
    _, f, app = _file_app("tree-escape-dirty.txt", "orig", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _open_dirty_quit_modal(app, pilot)
        await pilot.click("#cancel")
        await pilot.pause()
        assert not isinstance(app.screen, mod.UnsavedChangesScreen)
    assert f.read_text() == "orig"


async def test_ctrl_w_does_not_close_buffer() -> None:
    _, f, app = _file_app("clean-close.txt", "foo bar")
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        editor.move_cursor((0, 7))
        await pilot.pause()
        await _press(pilot, "ctrl+w")
        assert app.path == f, app.path
        assert list(app.query("#editor"))


async def test_close_buffer_dirty_shows_wide_modal_then_cancel() -> None:
    f, app = _dirty_app("dirty-close.txt")
    async with app.run_test() as pilot:
        await pilot.pause()
        await _make_dirty(app, pilot)
        app.action_close_buffer()
        await pilot.pause()
        assert isinstance(app.screen, mod.UnsavedChangesScreen)
        dialog = app.screen.query_one("#dialog")
        buttons = list(app.screen.query("Button"))
        assert dialog.region.width >= 64, dialog.region
        assert buttons, "expected confirmation buttons"
        assert all(
            button.region.x + button.region.width <= dialog.region.x + dialog.region.width
            for button in buttons
        ), [(button.id, button.region) for button in buttons]
        await pilot.click("#cancel")
        await pilot.pause()
        assert not isinstance(app.screen, mod.UnsavedChangesScreen)
        assert app.path == f, app.path
        assert _editor(app).text == "changed"
    assert f.read_text() == "orig"


async def test_close_buffer_dirty_space_discard_enters_no_buffer_state() -> None:
    f, app = _dirty_app("dirty-discard-close.txt")
    async with app.run_test() as pilot:
        await pilot.pause()
        await _make_dirty(app, pilot)
        app.action_close_buffer()
        await pilot.pause()
        assert isinstance(app.screen, mod.UnsavedChangesScreen)
        app.screen.query_one("#discard", Button).focus()
        await pilot.pause()
        await _press(pilot, "space")
        assert not isinstance(app.screen, mod.UnsavedChangesScreen)
        assert app.path is None, app.path
        assert not list(app.query("#editor"))
    assert f.read_text() == "orig"
