from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from textual.widgets import DirectoryTree, Input, Static

from rich_editor.screens import RenamePathScreen

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


async def test_file_tree_enter_renames_selected_file_without_opening_it() -> None:
    tmp, first, app = _file_app("first.txt", "first", root_is_tmp=True)
    selected = tmp / "second.txt"
    renamed = tmp / "renamed.txt"
    selected.write_text("second")
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select_tree_path(pilot, app, selected)
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, RenamePathScreen)
        input_widget = app.screen.query_one("#rename-input", Input)
        assert input_widget.value == "second.txt"
        input_widget.value = renamed.name
        await pilot.click("#ok")
        await pilot.pause()

        assert renamed.read_text() == "second"
        assert not selected.exists()
        assert app.path == first
        assert _editor(app).text == "first"


async def test_file_tree_rename_cancel_leaves_item_unchanged_and_refocuses_tree() -> None:
    tmp, _, app = _file_app("first.txt", "first", root_is_tmp=True)
    selected = tmp / "second.txt"
    selected.write_text("second")
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = await _select_tree_path(pilot, app, selected)
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, RenamePathScreen)
        app.screen.query_one("#rename-input", Input).value = "renamed.txt"
        await pilot.click("#cancel")
        await pilot.pause()

        assert selected.read_text() == "second"
        assert not (tmp / "renamed.txt").exists()
        assert tree.has_focus


async def test_file_tree_enter_renames_selected_folder() -> None:
    tmp, _, app = _file_app("first.txt", "first", root_is_tmp=True)
    selected = tmp / "folder"
    renamed = tmp / "renamed"
    selected.mkdir()
    (selected / "child.txt").write_text("child")
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select_tree_path(pilot, app, selected)
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, RenamePathScreen)
        app.screen.query_one("#rename-input", Input).value = renamed.name
        await pilot.click("#ok")
        await pilot.pause()

        assert (renamed / "child.txt").read_text() == "child"
        assert not selected.exists()


async def test_renaming_open_file_updates_save_path() -> None:
    tmp, path, app = _file_app("first.txt", "first", root_is_tmp=True)
    renamed = tmp / "renamed.md"
    async with app.run_test() as pilot:
        await pilot.pause()
        _editor(app).load_text("changed")
        await _select_tree_path(pilot, app, path)
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, RenamePathScreen)
        app.screen.query_one("#rename-input", Input).value = renamed.name
        await pilot.click("#ok")
        await pilot.pause()

        assert app.path == renamed
        assert _editor(app).text == "changed"
        app.action_save()
        await pilot.pause()

    assert renamed.read_text() == "changed"
    assert not path.exists()


async def test_renaming_open_file_parent_updates_open_path() -> None:
    tmp, path, app = _file_app("folder/open.txt", "open", root_is_tmp=True)
    folder = tmp / "folder"
    renamed = tmp / "renamed"
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select_tree_path(pilot, app, folder)
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, RenamePathScreen)
        app.screen.query_one("#rename-input", Input).value = renamed.name
        await pilot.click("#ok")
        await pilot.pause()

        assert app.path == renamed / "open.txt"
        assert _editor(app).text == "open"

    assert not path.exists()
    assert (renamed / "open.txt").read_text() == "open"


async def test_file_tree_space_still_opens_files_and_toggles_folders() -> None:
    tmp, _, app = _file_app("first.txt", "first", root_is_tmp=True)
    selected = tmp / "second.txt"
    selected.write_text("second")
    folder = tmp / "folder"
    folder.mkdir()
    (folder / "child.txt").write_text("child")
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select_tree_path(pilot, app, selected)
        await pilot.press("space")
        await pilot.pause()

        assert app.path is not None
        assert app.path.resolve(strict=False) == selected.resolve(strict=False)
        assert _editor(app).text == "second"

        tree = await _select_tree_path(pilot, app, folder)
        node = _find_tree_node(tree.root, folder)
        was_expanded = node.is_expanded
        await pilot.press("space")
        await pilot.pause()

        assert node.is_expanded is not was_expanded


async def test_file_tree_rename_duplicate_or_invalid_name_stays_open() -> None:
    tmp, _, app = _file_app("first.txt", "first", root_is_tmp=True)
    selected = tmp / "second.txt"
    selected.write_text("second")
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select_tree_path(pilot, app, selected)
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, RenamePathScreen)
        input_widget = app.screen.query_one("#rename-input", Input)
        input_widget.value = "first.txt"
        await pilot.click("#ok")
        await pilot.pause()

        assert isinstance(app.screen, RenamePathScreen)
        assert "already exists" in str(
            app.screen.query_one("#rename-error", Static).content
        )
        assert selected.read_text() == "second"
        assert (tmp / "first.txt").read_text() == "first"

        input_widget = app.screen.query_one("#rename-input", Input)
        input_widget.value = ""
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, RenamePathScreen)
        assert "empty" in str(app.screen.query_one("#rename-error", Static).content)
        assert selected.read_text() == "second"


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
