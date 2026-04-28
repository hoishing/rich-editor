from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from textual.widgets import DirectoryTree

from .helpers import _editor, _file_app, mod


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
    tree = app.query_one("#file-tree", DirectoryTree)
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


async def test_file_tree_cmd_backspace_moves_selected_file_to_trash() -> None:
    tmp, _, app = _file_app("first.txt", "first", root_is_tmp=True)
    selected = tmp / "second.txt"
    selected.write_text("second")
    trashed = _stub_trash(app)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select_tree_path(pilot, app, selected)
        await pilot.press("cmd+backspace")
        await pilot.pause()
        assert trashed == [selected.resolve(strict=False)]
    assert not selected.exists()


async def test_file_tree_ctrl_u_moves_selected_file_to_trash() -> None:
    tmp, _, app = _file_app("first.txt", "first", root_is_tmp=True)
    selected = tmp / "second.txt"
    selected.write_text("second")
    trashed = _stub_trash(app)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select_tree_path(pilot, app, selected)
        await pilot.press("ctrl+u")
        await pilot.pause()
        assert trashed == [selected.resolve(strict=False)]
    assert not selected.exists()


async def test_editor_cmd_backspace_does_not_trash_file_tree_selection() -> None:
    tmp, _, app = _file_app("first.txt", "hello world", root_is_tmp=True)
    selected = tmp / "second.txt"
    selected.write_text("second")
    trashed = _stub_trash(app)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select_tree_path(pilot, app, selected)
        editor = _editor(app)
        editor.focus()
        editor.move_cursor((0, 6))
        await pilot.press("cmd+backspace")
        await pilot.pause()
        assert editor.text == "world"
        assert trashed == []
    assert selected.exists()


async def test_trashing_open_file_closes_buffer_and_focuses_file_tree() -> None:
    tmp, path, app = _file_app("first.txt", "first", root_is_tmp=True)
    trashed = _stub_trash(app)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = await _select_tree_path(pilot, app, path)
        await pilot.press("cmd+backspace")
        await pilot.pause()
        assert trashed == [path.resolve(strict=False)]
        assert app.path is None
        assert tree.has_focus
        assert not list(app.query("#editor"))
    assert not path.exists()
