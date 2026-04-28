from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.widgets import Button, DirectoryTree, Static

from .helpers import _directory_app, _editor, _file_app, _press, mod


def _tree_has_path(node: Any, path: Path) -> bool:
    target = path.resolve(strict=False)
    data = getattr(node, "data", None)
    if data is not None and Path(data.path).resolve(strict=False) == target:
        return True
    return any(_tree_has_path(child, path) for child in node.children)


async def test_refresh_button_exists_in_header() -> None:
    _, _, app = _file_app("refresh.txt", "orig", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        refresh_button = app.query_one("#refresh-button", Static)
        assert refresh_button.content == "↻"


async def test_refresh_button_reloads_file_tree() -> None:
    tmp, _, app = _file_app("first.txt", "first", root_is_tmp=True)
    created = tmp / "created.txt"
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one("#file-tree", DirectoryTree)
        await tree.reload()
        await pilot.pause()
        assert not _tree_has_path(tree.root, created)

        created.write_text("created")
        await pilot.click("#refresh-button")
        await pilot.pause()

        assert _tree_has_path(tree.root, created)


async def test_cmd_r_reloads_clean_open_file() -> None:
    _, path, app = _file_app("refresh.txt", "orig", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        path.write_text("external")
        await _press(pilot, "cmd+r")
        assert _editor(app).text == "external"


async def test_super_r_reloads_clean_open_file() -> None:
    _, path, app = _file_app("refresh.txt", "orig", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        path.write_text("external")
        await _press(pilot, "super+r")
        assert _editor(app).text == "external"


async def test_refresh_dirty_save_writes_then_reloads() -> None:
    _, path, app = _file_app("save-refresh.txt", "orig", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        _editor(app).load_text("changed")
        await _press(pilot, "cmd+r")
        assert isinstance(app.screen, mod.UnsavedChangesScreen)

        await pilot.click("#save")
        await pilot.pause()

        assert path.read_text() == "changed"
        assert _editor(app).text == "changed"


async def test_refresh_dirty_discard_reloads_disk_content() -> None:
    _, path, app = _file_app("discard-refresh.txt", "orig", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        _editor(app).load_text("changed")
        await _press(pilot, "cmd+r")
        assert isinstance(app.screen, mod.UnsavedChangesScreen)

        await pilot.click("#discard")
        await pilot.pause()

        assert path.read_text() == "orig"
        assert _editor(app).text == "orig"


async def test_refresh_dirty_cancel_leaves_buffer_unchanged() -> None:
    _, path, app = _file_app("cancel-refresh.txt", "orig", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        _editor(app).load_text("changed")
        await _press(pilot, "cmd+r")
        assert isinstance(app.screen, mod.UnsavedChangesScreen)

        await pilot.click("#cancel")
        await pilot.pause()

        assert path.read_text() == "orig"
        assert _editor(app).text == "changed"


async def test_refresh_deleted_open_file_closes_buffer_and_focuses_file_tree() -> None:
    _, path, app = _file_app("missing-refresh.txt", "orig", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        path.unlink()
        await _press(pilot, "cmd+r")

        tree = app.query_one("#file-tree", DirectoryTree)
        assert app.path is None
        assert not list(app.query("#editor"))
        assert tree.has_focus


async def test_refresh_no_buffer_reloads_file_tree_and_keeps_tree_focus() -> None:
    tmp, app = _directory_app()
    created = tmp / "created.txt"
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one("#file-tree", DirectoryTree)
        assert tree.has_focus

        created.write_text("created")
        await _press(pilot, "cmd+r")

        assert _tree_has_path(tree.root, created)
        assert tree.has_focus
        assert app.path is None


async def test_refresh_dirty_space_discard_reloads_disk_content() -> None:
    _, _, app = _file_app("space-discard-refresh.txt", "orig", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        _editor(app).load_text("changed")
        await _press(pilot, "cmd+r")
        assert isinstance(app.screen, mod.UnsavedChangesScreen)
        app.screen.query_one("#discard", Button).focus()
        await _press(pilot, "space")
        assert _editor(app).text == "orig"
