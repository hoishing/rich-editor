from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.command import CommandPalette
from textual.widgets import Button, DirectoryTree, Footer, Input

from .helpers import (
    _directory_app,
    _editor,
    _file_app,
    _footer_labels,
    _key_help_rows,
    _press,
    mod,
)


def _tree_has_path(node: Any, path: Path) -> bool:
    target = path.resolve(strict=False)
    data = getattr(node, "data", None)
    if data is not None and Path(data.path).resolve(strict=False) == target:
        return True
    return any(_tree_has_path(child, path) for child in node.children)


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


async def _submit_create_file(app, pilot, name: str) -> None:
    assert isinstance(app.screen, mod.CreateFileScreen)
    filename = app.screen.query_one("#filename", Input)
    filename.value = name
    await pilot.pause()
    await _press(pilot, "enter")


async def test_alt_n_opens_create_file_prompt() -> None:
    _, _, app = _file_app("current.txt", "current", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _press(pilot, "alt+n")
        assert isinstance(app.screen, mod.CreateFileScreen)
        assert app.screen.query_one("#filename", Input).has_focus


async def test_create_file_uses_open_file_folder() -> None:
    tmp, current, app = _file_app("folder/current.txt", "current", root_is_tmp=True)
    target = current.parent / "new.txt"
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_create_file()
        await pilot.pause()
        await _submit_create_file(app, pilot, "new.txt")

        assert target.exists()
        assert target.read_text() == ""
        assert app.path == target.resolve(strict=False)
        assert _editor(app).text == ""
    assert not (tmp / "new.txt").exists()


async def test_create_file_uses_highlighted_sidebar_folder() -> None:
    tmp, current, app = _file_app("folder/current.txt", "current", root_is_tmp=True)
    selected = tmp / "selected"
    selected.mkdir()
    target = selected / "new.txt"
    fallback = current.parent / "new.txt"
    async with app.run_test() as pilot:
        await pilot.pause()
        app._show_sidebar()
        tree = app.query_one("#sidebar", DirectoryTree)
        await tree.reload()
        await pilot.pause()
        tree.focus()
        tree.move_cursor(_find_tree_node(tree.root, selected))
        await pilot.pause()

        await _press(pilot, "alt+n")
        await _submit_create_file(app, pilot, "new.txt")

        assert target.exists()
        assert app.path == target.resolve(strict=False)
        assert _editor(app).text == ""
    assert not fallback.exists()


async def test_create_file_accepts_nested_relative_path() -> None:
    _, current, app = _file_app("folder/current.txt", "current", root_is_tmp=True)
    target = current.parent / "notes" / "today.md"
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_create_file()
        await pilot.pause()
        await _submit_create_file(app, pilot, "notes/today.md")

        assert target.exists()
        assert app.path == target.resolve(strict=False)
        assert _editor(app).text == ""


async def test_create_file_without_open_buffer_uses_project_root() -> None:
    tmp, app = _directory_app()
    target = tmp / "root-new.txt"
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_create_file()
        await pilot.pause()
        await _submit_create_file(app, pilot, "root-new.txt")

        assert target.exists()
        assert app.path == target.resolve(strict=False)
        assert _editor(app).text == ""
        tree = app.query_one("#sidebar", DirectoryTree)
        assert _tree_has_path(tree.root, target)


async def test_create_file_existing_file_opens_without_overwriting() -> None:
    _, current, app = _file_app("folder/current.txt", "current", root_is_tmp=True)
    target = current.parent / "existing.txt"
    target.write_text("keep me")
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_create_file()
        await pilot.pause()
        await _submit_create_file(app, pilot, "existing.txt")

        assert app.path == target.resolve(strict=False)
        assert _editor(app).text == "keep me"
    assert target.read_text() == "keep me"


async def test_create_file_dirty_save_then_opens_new_file() -> None:
    _, current, app = _file_app("folder/current.txt", "current", root_is_tmp=True)
    target = current.parent / "saved-new.txt"
    async with app.run_test() as pilot:
        await pilot.pause()
        _editor(app).load_text("changed")
        app.action_create_file()
        await pilot.pause()
        await _submit_create_file(app, pilot, "saved-new.txt")
        assert isinstance(app.screen, mod.UnsavedChangesScreen)

        await pilot.click("#save")
        await pilot.pause()

        assert current.read_text() == "changed"
        assert target.exists()
        assert app.path == target.resolve(strict=False)
        assert _editor(app).text == ""


async def test_create_file_dirty_discard_then_opens_new_file() -> None:
    _, current, app = _file_app("folder/current.txt", "current", root_is_tmp=True)
    target = current.parent / "discard-new.txt"
    async with app.run_test() as pilot:
        await pilot.pause()
        _editor(app).load_text("changed")
        app.action_create_file()
        await pilot.pause()
        await _submit_create_file(app, pilot, "discard-new.txt")
        assert isinstance(app.screen, mod.UnsavedChangesScreen)

        await pilot.click("#discard")
        await pilot.pause()

        assert current.read_text() == "current"
        assert target.exists()
        assert app.path == target.resolve(strict=False)


async def test_create_file_dirty_cancel_keeps_current_buffer() -> None:
    _, current, app = _file_app("folder/current.txt", "current", root_is_tmp=True)
    target = current.parent / "cancel-new.txt"
    async with app.run_test() as pilot:
        await pilot.pause()
        _editor(app).load_text("changed")
        app.action_create_file()
        await pilot.pause()
        await _submit_create_file(app, pilot, "cancel-new.txt")
        assert isinstance(app.screen, mod.UnsavedChangesScreen)

        await pilot.click("#cancel")
        await pilot.pause()

        assert not target.exists()
        assert app.path == current
        assert _editor(app).text == "changed"


async def test_create_file_dirty_space_discard_opens_new_file() -> None:
    _, current, app = _file_app("folder/current.txt", "current", root_is_tmp=True)
    target = current.parent / "space-discard-new.txt"
    async with app.run_test() as pilot:
        await pilot.pause()
        _editor(app).load_text("changed")
        app.action_create_file()
        await pilot.pause()
        await _submit_create_file(app, pilot, "space-discard-new.txt")
        assert isinstance(app.screen, mod.UnsavedChangesScreen)
        app.screen.query_one("#discard", Button).focus()
        await _press(pilot, "space")

        assert target.exists()
        assert app.path == target.resolve(strict=False)


async def test_create_file_rejects_path_outside_base() -> None:
    _, current, app = _file_app("folder/current.txt", "current", root_is_tmp=True)
    target = current.parent.parent / "outside.txt"
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_create_file()
        await pilot.pause()
        await _submit_create_file(app, pilot, "../outside.txt")

        assert not target.exists()
        assert app.path == current
        assert _editor(app).text == "current"


async def test_create_file_footer_and_key_help_show_alt_n() -> None:
    _, _, app = _file_app(
        "current.txt",
        "current",
        root_is_tmp=True,
        ghostty_conflicted_hotkey_triggers=set(),
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = _footer_labels(footer)
        assert labels["Create file"] == "⌥N"

        app.action_show_keys_popup()
        await pilot.pause()
        rows = _key_help_rows(app)
        assert ("⌥N", "Create file") in rows


async def test_command_palette_includes_create_file() -> None:
    _, _, app = _file_app("current.txt", "current", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        commands = {
            command.title: command for command in app.get_system_commands(app.screen)
        }
        assert "Create file" in commands
        commands["Create file"].callback()
        await pilot.pause()
        assert isinstance(app.screen, mod.CreateFileScreen)


async def test_command_palette_opens_from_alt_n() -> None:
    _, _, app = _file_app("current.txt", "current", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _press(pilot, "alt+n")
        assert not CommandPalette.is_open(app)
        assert isinstance(app.screen, mod.CreateFileScreen)
