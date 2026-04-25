#!/usr/bin/env -S uv run --project . python
"""End-to-end tests for `riched` driven by Textual's Pilot harness.

Run with:  uv run ./e2e.py
"""
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import traceback
from pathlib import Path
from types import SimpleNamespace
from typing import Awaitable, Callable

import yaml
from textual.widgets import Button, DataTable, DirectoryTree, TextArea

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from riched import keybindings, syntax as syntax_mod  # noqa: E402
from riched.app import RichedApp  # noqa: E402
from riched.keybindings import (  # noqa: E402
    COMMANDS,
    DEFAULT_BINDINGS,
    build_bindings,
    load_bindings,
    save_bindings,
)
from riched.screens import (  # noqa: E402
    FileMenuScreen,
    KeyCaptureScreen,
    KeybindingsScreen,
    UnsavedChangesScreen,
)

mod = SimpleNamespace(
    COMMANDS=COMMANDS,
    DEFAULT_BINDINGS=DEFAULT_BINDINGS,
    FileMenuScreen=FileMenuScreen,
    KeyCaptureScreen=KeyCaptureScreen,
    KeybindingsScreen=KeybindingsScreen,
    RichedApp=RichedApp,
    UnsavedChangesScreen=UnsavedChangesScreen,
    build_bindings=build_bindings,
    load_bindings=load_bindings,
    save_bindings=save_bindings,
)


def _fresh_env() -> tuple[Path, Path]:
    """Create an isolated tmpdir + redirect riched's config + reset globals."""
    tmp = Path(tempfile.mkdtemp(prefix="riched-e2e-"))
    cfg = tmp / "keybindings.yaml"
    keybindings.CONFIG_PATH = cfg
    keybindings.LEGACY_CONFIG_PATH = tmp / "keybindings.json"
    syntax_mod.reset_ts_registration()
    return tmp, cfg


def _make_app(
    path: Path,
    mapping: dict[str, str] | None = None,
    root: Path | None = None,
):
    """Replicate `riched.main()`'s dynamic subclass so BINDINGS take effect."""
    if mapping is None:
        mapping = dict(mod.DEFAULT_BINDINGS)
    cls = type(
        "ConfiguredRichedApp",
        (mod.RichedApp,),
        {"BINDINGS": mod.build_bindings(mapping)},
    )
    return cls(path, mapping, root or path.parent)


# ---------------------------------------------------------------- file I/O ---


async def test_open_existing_file() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "hello.txt"
    f.write_text("hello\nworld\n")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        assert editor.text == "hello\nworld\n", repr(editor.text)


async def test_open_missing_file() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "does-not-exist.txt"
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        assert editor.text == "", repr(editor.text)
        assert not f.exists()


async def test_open_directory_starts_with_no_buffer() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "file.txt"
    f.write_text("content")
    app = _make_app(tmp, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one("#file-tree", DirectoryTree)
        assert Path(tree.path) == tmp, tree.path
        assert app.path is None, app.path
        assert not list(app.query("#editor"))

        app._switch_path(f)
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        assert app.path == f, app.path
        assert editor.text == "content", repr(editor.text)


async def test_save_writes_file() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "out.txt"
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("typed content")
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()
    assert f.read_text() == "typed content"


# ----------------------------------------------------------- quit + dirty ---


async def test_quit_clean_exits() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "clean.txt"
    f.write_text("foo")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+q")
        await pilot.pause()
    # If the app didn't exit, run_test would never return — reaching here is the assertion.


async def test_quit_dirty_shows_modal_then_cancel() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "dirty.txt"
    f.write_text("orig")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("changed")
        await pilot.pause()
        await pilot.press("ctrl+q")
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
        await pilot.press("ctrl+q")
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
        await pilot.press("ctrl+q")
        await pilot.pause()
        await pilot.click("#discard")
        await pilot.pause()
    assert f.read_text() == "orig"


async def test_close_buffer_clean_enters_no_buffer_state_via_ctrl_w() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "clean-close.txt"
    f.write_text("foo")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+w")
        await pilot.pause()
        assert app.path is None, app.path
        assert not list(app.query("#editor"))


async def test_close_buffer_dirty_shows_wide_modal_then_cancel() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "dirty-close.txt"
    f.write_text("orig")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("changed")
        await pilot.pause()
        await pilot.press("ctrl+w")
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
        await pilot.press("ctrl+w")
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


# -------------------------------------------------- syntax highlighting ----


async def test_python_highlight() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "x.py"
    f.write_text("def foo():\n    return 1\n")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        assert editor.language == "python", editor.language


async def test_typescript_highlight() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "x.ts"
    f.write_text("interface Foo { bar: number }\n")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        assert editor.language == "typescript", editor.language


async def test_tsx_highlight() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "x.tsx"
    f.write_text("const X = () => <div>hi</div>;\n")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        assert editor.language == "tsx", editor.language


async def test_unknown_extension_no_language() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "notes.xyz"
    f.write_text("plain text")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        assert editor.language is None, editor.language


# ---------------------------------------------------- keybindings (config) --


async def test_keybindings_default_load_no_file() -> None:
    _fresh_env()
    assert mod.load_bindings() == mod.DEFAULT_BINDINGS


async def test_keybindings_corrupt_yaml_fallback() -> None:
    _, cfg = _fresh_env()
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("{not valid")
    assert mod.load_bindings() == mod.DEFAULT_BINDINGS


async def test_keybindings_persist_roundtrip() -> None:
    _, cfg = _fresh_env()
    m = dict(mod.DEFAULT_BINDINGS)
    m["save"] = "ctrl+g"
    mod.save_bindings(m)
    assert mod.load_bindings()["save"] == "ctrl+g"
    data = yaml.safe_load(cfg.read_text())
    assert data["save"] == "ctrl+g"
    assert data["quit_check"] == "ctrl+q"


async def test_keybindings_legacy_json_migrates_to_yaml() -> None:
    tmp, cfg = _fresh_env()
    legacy = tmp / "keybindings.json"
    legacy.write_text(json.dumps({"save": "ctrl+g"}))
    assert mod.load_bindings()["save"] == "ctrl+g"
    data = yaml.safe_load(cfg.read_text())
    assert data["save"] == "ctrl+g", data
    assert data["quit_check"] == "ctrl+q", data


async def test_custom_bindings_active_in_app() -> None:
    tmp, _ = _fresh_env()
    m = dict(mod.DEFAULT_BINDINGS)
    m["save"] = "ctrl+g"
    mod.save_bindings(m)
    f = tmp / "custom.txt"
    app = _make_app(f, mod.load_bindings())
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("via ctrl+g")
        await pilot.pause()
        await pilot.press("ctrl+g")
        await pilot.pause()
    assert f.read_text() == "via ctrl+g"


# ---------------------------------------------------- keybindings (UI) -----


async def test_keybindings_screen_opens_via_ctrl_k() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "k.txt"
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+k")
        await pilot.pause()
        assert isinstance(app.screen, mod.KeybindingsScreen)
        table = app.screen.query_one(DataTable)
        assert table.row_count == len(mod.COMMANDS), table.row_count
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, mod.KeybindingsScreen)


async def test_keybindings_edit_via_capture_screen_persists_to_disk() -> None:
    tmp, cfg = _fresh_env()
    f = tmp / "k.txt"
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+k")
        await pilot.pause()
        assert isinstance(app.screen, mod.KeybindingsScreen)
        # DataTable cursor on row 0 ("save"). Press Enter to open KeyCaptureScreen.
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, mod.KeyCaptureScreen), type(app.screen).__name__
        await pilot.press("ctrl+g")
        await pilot.pause()
        assert isinstance(app.screen, mod.KeybindingsScreen)
    data = yaml.safe_load(cfg.read_text())
    assert data["save"] == "ctrl+g", data
    # Other defaults preserved.
    assert data["quit_check"] == "ctrl+q"


async def test_keybindings_capture_escape_cancels() -> None:
    tmp, cfg = _fresh_env()
    f = tmp / "k.txt"
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+k")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, mod.KeyCaptureScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, mod.KeybindingsScreen)
    # No config file written because nothing changed.
    assert not cfg.exists()


async def test_keybindings_reset_to_defaults() -> None:
    tmp, cfg = _fresh_env()
    m = dict(mod.DEFAULT_BINDINGS)
    m["save"] = "ctrl+w"
    mod.save_bindings(m)
    f = tmp / "k.txt"
    app = _make_app(f, mod.load_bindings())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+k")
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
    data = yaml.safe_load(cfg.read_text())
    assert data == mod.DEFAULT_BINDINGS, data


# -------------------------------------------------- editor line shortcuts --


async def test_move_line_down() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("aaa\nbbb\nccc")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 1))
        await pilot.pause()
        await pilot.press("alt+down")
        await pilot.pause()
        assert editor.text == "bbb\naaa\nccc", repr(editor.text)
        assert editor.cursor_location == (1, 1), editor.cursor_location


async def test_move_line_up() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("aaa\nbbb\nccc")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((1, 2))
        await pilot.pause()
        await pilot.press("alt+up")
        await pilot.pause()
        assert editor.text == "bbb\naaa\nccc", repr(editor.text)
        assert editor.cursor_location == (0, 2), editor.cursor_location


async def test_move_line_at_boundaries_is_noop() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("aaa\nbbb")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 0))
        await pilot.pause()
        await pilot.press("alt+up")
        await pilot.pause()
        assert editor.text == "aaa\nbbb", repr(editor.text)
        editor.move_cursor((1, 0))
        await pilot.pause()
        await pilot.press("alt+down")
        await pilot.pause()
        assert editor.text == "aaa\nbbb", repr(editor.text)


async def test_copy_line_down() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("aaa\nbbb")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 1))
        await pilot.pause()
        await pilot.press("shift+alt+down")
        await pilot.pause()
        assert editor.text == "aaa\naaa\nbbb", repr(editor.text)
        assert editor.cursor_location == (1, 1), editor.cursor_location


async def test_copy_line_up() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("aaa\nbbb")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((1, 2))
        await pilot.pause()
        await pilot.press("shift+alt+up")
        await pilot.pause()
        assert editor.text == "aaa\nbbb\nbbb", repr(editor.text)
        assert editor.cursor_location == (1, 2), editor.cursor_location


async def test_alt_backspace_deletes_word_left() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "words.txt"
    f.write_text("hello world foo")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 15))
        await pilot.pause()
        await pilot.press("alt+backspace")
        await pilot.pause()
        text = editor.text
        assert "foo" not in text, repr(text)
        assert text.startswith("hello world"), repr(text)


async def test_alt_shift_arrows_select_word_left_and_right() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "words.txt"
    f.write_text("alpha beta gamma")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 10))
        await pilot.pause()
        await pilot.press("alt+shift+left")
        await pilot.pause()
        assert editor.cursor_location == (0, 6), editor.cursor_location
        assert editor.selection.start == (0, 10), editor.selection
        assert editor.selection.end == (0, 6), editor.selection
        assert editor.selected_text == "beta", repr(editor.selected_text)

        editor.move_cursor((0, 6))
        await pilot.pause()
        await pilot.press("alt+shift+right")
        await pilot.pause()
        assert editor.cursor_location == (0, 10), editor.cursor_location
        assert editor.selection.start == (0, 6), editor.selection
        assert editor.selection.end == (0, 10), editor.selection
        assert editor.selected_text == "beta", repr(editor.selected_text)


async def test_cmd_l_selects_current_line_with_newline() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("alpha\nbeta\ngamma\n")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((1, 2))
        await pilot.pause()
        await pilot.press("cmd+l")
        await pilot.pause()
        assert editor.selection.start == (1, 0), editor.selection
        assert editor.selection.end == (2, 0), editor.selection
        assert editor.cursor_location == (2, 0), editor.cursor_location
        assert editor.selected_text == "beta\n", repr(editor.selected_text)


async def test_cmd_l_repeats_expand_line_selection() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("alpha\nbeta\ngamma\n")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 3))
        await pilot.pause()
        await pilot.press("cmd+l")
        await pilot.pause()
        await pilot.press("cmd+l")
        await pilot.pause()
        assert editor.selection.start == (0, 0), editor.selection
        assert editor.selection.end == (2, 0), editor.selection
        assert editor.cursor_location == (2, 0), editor.cursor_location
        assert editor.selected_text == "alpha\nbeta\n", repr(editor.selected_text)


async def test_super_l_selects_current_line_alias() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("alpha\nbeta\n")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 1))
        await pilot.pause()
        await pilot.press("super+l")
        await pilot.pause()
        assert editor.selection.start == (0, 0), editor.selection
        assert editor.selection.end == (1, 0), editor.selection
        assert editor.selected_text == "alpha\n", repr(editor.selected_text)


async def test_cmd_l_selects_final_line_without_newline() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("alpha\nbeta\ngamma")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((2, 2))
        await pilot.pause()
        await pilot.press("cmd+l")
        await pilot.pause()
        assert editor.selection.start == (2, 0), editor.selection
        assert editor.selection.end == (2, 5), editor.selection
        assert editor.cursor_location == (2, 5), editor.cursor_location
        assert editor.selected_text == "gamma", repr(editor.selected_text)


async def test_cmd_shift_left_selects_to_line_start() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "select.txt"
    f.write_text("hello world")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 5))
        await pilot.pause()
        await pilot.press("cmd+shift+left")
        await pilot.pause()
        assert editor.cursor_location == (0, 0), editor.cursor_location
        assert editor.selection.start == (0, 5), editor.selection
        assert editor.selection.end == (0, 0), editor.selection


async def test_cmd_shift_right_selects_to_line_end() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "select.txt"
    f.write_text("hello world")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 5))
        await pilot.pause()
        await pilot.press("cmd+shift+right")
        await pilot.pause()
        assert editor.cursor_location == (0, 11), editor.cursor_location
        assert editor.selection.start == (0, 5), editor.selection
        assert editor.selection.end == (0, 11), editor.selection


async def test_super_shift_line_selection_aliases() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "select.txt"
    f.write_text("hello world")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 5))
        await pilot.pause()
        await pilot.press("super+shift+left")
        await pilot.pause()
        assert editor.selection.start == (0, 5), editor.selection
        assert editor.selection.end == (0, 0), editor.selection
        editor.move_cursor((0, 5))
        await pilot.pause()
        await pilot.press("super+shift+right")
        await pilot.pause()
        assert editor.selection.start == (0, 5), editor.selection
        assert editor.selection.end == (0, 11), editor.selection


async def test_parser_order_super_shift_line_selection_aliases() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "select.txt"
    f.write_text("  hello world")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 8))
        await pilot.pause()
        await pilot.press("shift+super+left")
        await pilot.pause()
        assert editor.cursor_location == (0, 2), editor.cursor_location
        assert editor.selection.start == (0, 8), editor.selection
        assert editor.selection.end == (0, 2), editor.selection
        assert editor.selected_text == "hello ", repr(editor.selected_text)

        editor.move_cursor((0, 5))
        await pilot.pause()
        await pilot.press("shift+super+right")
        await pilot.pause()
        assert editor.cursor_location == (0, 13), editor.cursor_location
        assert editor.selection.start == (0, 5), editor.selection
        assert editor.selection.end == (0, 13), editor.selection
        assert editor.selected_text == "lo world", repr(editor.selected_text)


# ---------------------------------------------------------------- runner ----


TESTS: list[tuple[str, Callable[[], Awaitable[None]]]] = [
    ("open existing file", test_open_existing_file),
    ("open missing file", test_open_missing_file),
    ("open directory starts with no buffer", test_open_directory_starts_with_no_buffer),
    ("save writes file", test_save_writes_file),
    ("quit clean exits", test_quit_clean_exits),
    ("quit dirty: modal + cancel", test_quit_dirty_shows_modal_then_cancel),
    ("quit dirty: save writes & exits", test_quit_dirty_save_writes_and_exits),
    ("quit dirty: discard keeps file", test_quit_dirty_discard_keeps_file),
    (
        "close buffer clean enters no-buffer state via Ctrl+W",
        test_close_buffer_clean_enters_no_buffer_state_via_ctrl_w,
    ),
    (
        "close buffer dirty: wide modal + cancel",
        test_close_buffer_dirty_shows_wide_modal_then_cancel,
    ),
    (
        "close buffer dirty: Space discard enters no-buffer state",
        test_close_buffer_dirty_space_discard_enters_no_buffer_state,
    ),
    ("file menu via F10 + Save", test_file_menu_opens_via_f10_and_save_works),
    ("file tree: rooted at project dir", test_file_tree_is_rooted_at_project_dir),
    ("file tree: switch opens file", test_file_tree_switch_opens_selected_file),
    (
        "file tree: dirty switch prompts then discard",
        test_file_tree_dirty_switch_prompts_then_discard_opens_file,
    ),
    ("syntax: python", test_python_highlight),
    ("syntax: typescript", test_typescript_highlight),
    ("syntax: tsx", test_tsx_highlight),
    ("syntax: unknown extension", test_unknown_extension_no_language),
    ("keybindings: default load (no file)", test_keybindings_default_load_no_file),
    ("keybindings: corrupt YAML fallback", test_keybindings_corrupt_yaml_fallback),
    ("keybindings: persist roundtrip", test_keybindings_persist_roundtrip),
    ("keybindings: legacy JSON migrates", test_keybindings_legacy_json_migrates_to_yaml),
    ("keybindings: custom binding active", test_custom_bindings_active_in_app),
    ("keybindings: screen opens via Ctrl+K", test_keybindings_screen_opens_via_ctrl_k),
    ("keybindings: edit via capture", test_keybindings_edit_via_capture_screen_persists_to_disk),
    ("keybindings: capture escape cancels", test_keybindings_capture_escape_cancels),
    ("keybindings: reset to defaults", test_keybindings_reset_to_defaults),
    ("editor: move line down", test_move_line_down),
    ("editor: move line up", test_move_line_up),
    ("editor: move line at boundaries no-op", test_move_line_at_boundaries_is_noop),
    ("editor: copy line down", test_copy_line_down),
    ("editor: copy line up", test_copy_line_up),
    ("editor: alt+backspace deletes word", test_alt_backspace_deletes_word_left),
    (
        "editor: alt+shift arrows select word",
        test_alt_shift_arrows_select_word_left_and_right,
    ),
    ("editor: cmd+l selects current line", test_cmd_l_selects_current_line_with_newline),
    ("editor: cmd+l repeats expand line selection", test_cmd_l_repeats_expand_line_selection),
    ("editor: super+l selects current line alias", test_super_l_selects_current_line_alias),
    (
        "editor: cmd+l selects final line without newline",
        test_cmd_l_selects_final_line_without_newline,
    ),
    ("editor: cmd+shift+left selects line start", test_cmd_shift_left_selects_to_line_start),
    ("editor: cmd+shift+right selects line end", test_cmd_shift_right_selects_to_line_end),
    ("editor: super+shift line selection aliases", test_super_shift_line_selection_aliases),
    (
        "editor: parser-order super+shift line selection aliases",
        test_parser_order_super_shift_line_selection_aliases,
    ),
]


async def main() -> int:
    passed = 0
    failed: list[tuple[str, str]] = []
    for name, fn in TESTS:
        try:
            await fn()
        except Exception:
            failed.append((name, traceback.format_exc()))
            print(f"FAIL  {name}")
        else:
            passed += 1
            print(f"PASS  {name}")

    print()
    print(f"{passed} passed, {len(failed)} failed, {len(TESTS)} total")
    if failed:
        print()
        for name, tb in failed:
            print(f"--- {name} " + "-" * (60 - len(name)))
            print(tb)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
