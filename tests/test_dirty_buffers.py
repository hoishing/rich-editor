from __future__ import annotations

from textual.widgets import Button, DirectoryTree, TextArea

from .helpers import _fresh_env, _make_app, mod

# ----------------------------------------------------------- quit + dirty ---


async def test_ctrl_q_does_not_quit() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "clean.txt"
    f.write_text("foo")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+q")
        await pilot.pause()
        assert app.path == f, app.path
        assert list(app.query("#editor"))


async def test_quit_dirty_shows_modal_then_cancel() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "dirty.txt"
    f.write_text("orig")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("changed")
        await pilot.pause()
        app.query_one("#file-tree", DirectoryTree).focus()
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, mod.UnsavedChangesScreen)
        await pilot.click("#cancel")
        await pilot.pause()
        assert not isinstance(app.screen, mod.UnsavedChangesScreen)
    assert f.read_text() == "orig"  # never overwritten


async def test_quit_dirty_save_writes_and_exits() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "save.txt"
    f.write_text("orig")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("new content")
        await pilot.pause()
        app.query_one("#file-tree", DirectoryTree).focus()
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, mod.UnsavedChangesScreen)
        await pilot.click("#save")
        await pilot.pause()
    assert f.read_text() == "new content"


async def test_quit_dirty_discard_keeps_file() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "discard.txt"
    f.write_text("orig")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("changed")
        await pilot.pause()
        app.query_one("#file-tree", DirectoryTree).focus()
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        await pilot.click("#discard")
        await pilot.pause()
    assert f.read_text() == "orig"


async def test_file_tree_escape_clean_shows_quit_confirmation_then_cancel() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "tree-escape-clean.txt"
    f.write_text("foo")
    app = _make_app(f, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#file-tree", DirectoryTree).focus()
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, mod.QuitConfirmationScreen)
        await pilot.click("#cancel")
        await pilot.pause()
        assert not isinstance(app.screen, mod.QuitConfirmationScreen)
        assert app.path == f, app.path


async def test_file_tree_escape_clean_quit_exits() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "tree-escape-quit.txt"
    f.write_text("foo")
    app = _make_app(f, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#file-tree", DirectoryTree).focus()
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, mod.QuitConfirmationScreen)
        await pilot.click("#quit")
        await pilot.pause()


async def test_file_tree_escape_dirty_shows_unsaved_changes() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "tree-escape-dirty.txt"
    f.write_text("orig")
    app = _make_app(f, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("changed")
        app.query_one("#file-tree", DirectoryTree).focus()
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, mod.UnsavedChangesScreen)
        await pilot.click("#cancel")
        await pilot.pause()
        assert not isinstance(app.screen, mod.UnsavedChangesScreen)
    assert f.read_text() == "orig"


async def test_ctrl_w_does_not_close_buffer() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "clean-close.txt"
    f.write_text("foo bar")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 7))
        await pilot.pause()
        await pilot.press("ctrl+w")
        await pilot.pause()
        assert app.path == f, app.path
        assert list(app.query("#editor"))


async def test_close_buffer_dirty_shows_wide_modal_then_cancel() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "dirty-close.txt"
    f.write_text("orig")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("changed")
        await pilot.pause()
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
        assert app.query_one("#editor", TextArea).text == "changed"
    assert f.read_text() == "orig"


async def test_close_buffer_dirty_space_discard_enters_no_buffer_state() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "dirty-discard-close.txt"
    f.write_text("orig")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("changed")
        await pilot.pause()
        app.action_close_buffer()
        await pilot.pause()
        assert isinstance(app.screen, mod.UnsavedChangesScreen)
        app.screen.query_one("#discard", Button).focus()
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        assert not isinstance(app.screen, mod.UnsavedChangesScreen)
        assert app.path is None, app.path
        assert not list(app.query("#editor"))
    assert f.read_text() == "orig"
