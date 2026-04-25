from __future__ import annotations

from pathlib import Path

from textual.widgets import DirectoryTree, TextArea

from .helpers import _fresh_env, _make_app, mod

# ------------------------------------------------------------- file menu ----


async def test_file_menu_opens_via_f10_and_save_works() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "menu.txt"
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("via menu")
        await pilot.pause()
        await pilot.press("f10")
        await pilot.pause()
        assert isinstance(app.screen, mod.FileMenuScreen)
        # OptionList is focused; first option ("Save") highlighted by default.
        await pilot.press("enter")
        await pilot.pause()
    assert f.read_text() == "via menu"


# --------------------------------------------------------------- file tree --


async def test_file_tree_is_rooted_at_project_dir() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "tree.txt"
    f.write_text("tree")
    app = _make_app(f, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one("#file-tree", DirectoryTree)
        assert Path(tree.path) == tmp, tree.path


async def test_file_tree_switch_opens_selected_file() -> None:
    tmp, _ = _fresh_env()
    first = tmp / "first.txt"
    second = tmp / "second.txt"
    first.write_text("first")
    second.write_text("second")
    app = _make_app(first, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._switch_path(second)
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        assert editor.text == "second", repr(editor.text)
        assert app.path == second, app.path


async def test_file_tree_dirty_switch_prompts_then_discard_opens_file() -> None:
    tmp, _ = _fresh_env()
    first = tmp / "first.txt"
    second = tmp / "second.txt"
    first.write_text("first")
    second.write_text("second")
    app = _make_app(first, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("dirty")
        await pilot.pause()
        app._switch_path(second)
        await pilot.pause()
        assert isinstance(app.screen, mod.UnsavedChangesScreen)
        await pilot.click("#discard")
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        assert editor.text == "second", repr(editor.text)
        assert app.path == second, app.path
    assert first.read_text() == "first"


