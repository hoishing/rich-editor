from __future__ import annotations

from pathlib import Path

from textual.widgets import DirectoryTree

from .helpers import _editor, _file_app, mod


async def test_file_tree_is_rooted_at_project_dir() -> None:
    tmp, _, app = _file_app("tree.txt", "tree", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one("#file-tree", DirectoryTree)
        assert Path(tree.path) == tmp, tree.path


async def test_file_tree_switch_opens_selected_file() -> None:
    tmp, first, app = _file_app("first.txt", "first", root_is_tmp=True)
    second = tmp / "second.txt"
    second.write_text("second")
    async with app.run_test() as pilot:
        await pilot.pause()
        app._switch_path(second)
        await pilot.pause()
        assert _editor(app).text == "second", repr(_editor(app).text)
        assert app.path == second, app.path


async def test_file_tree_dirty_switch_prompts_then_discard_opens_file() -> None:
    tmp, first, app = _file_app("first.txt", "first", root_is_tmp=True)
    second = tmp / "second.txt"
    second.write_text("second")
    async with app.run_test() as pilot:
        await pilot.pause()
        _editor(app).load_text("dirty")
        await pilot.pause()
        app._switch_path(second)
        await pilot.pause()
        assert isinstance(app.screen, mod.UnsavedChangesScreen)
        await pilot.click("#discard")
        await pilot.pause()
        assert _editor(app).text == "second", repr(_editor(app).text)
        assert app.path == second, app.path
    assert first.read_text() == "first"
