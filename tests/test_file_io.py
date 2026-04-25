from __future__ import annotations

from pathlib import Path

from textual.widgets import DirectoryTree, TextArea

from .helpers import _fresh_env, _make_app

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

