from __future__ import annotations

from pathlib import Path

from textual.widgets import DirectoryTree

from .helpers import _directory_app, _editor, _file_app, _fresh_env, _make_app


async def test_open_existing_file() -> None:
    _, _, app = _file_app("hello.txt", "hello\nworld\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        assert _editor(app).text == "hello\nworld\n", repr(_editor(app).text)


async def test_open_missing_file() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "does-not-exist.txt"
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        assert editor.text == "", repr(editor.text)
        assert not f.exists()


async def test_open_directory_starts_with_no_buffer() -> None:
    tmp, app = _directory_app()
    f = tmp / "file.txt"
    f.write_text("content")
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one("#sidebar", DirectoryTree)
        assert Path(tree.path) == tmp, tree.path
        assert app.path is None, app.path
        assert not list(app.query("#editor"))

        app._switch_path(f)
        await pilot.pause()
        assert app.path == f, app.path
        assert _editor(app).text == "content", repr(_editor(app).text)


async def test_save_writes_file() -> None:
    _, f, app = _file_app("out.txt")
    async with app.run_test() as pilot:
        await pilot.pause()
        _editor(app).load_text("typed content")
        await pilot.pause()
        await pilot.press("cmd+s")
        await pilot.pause()
    assert f.read_text() == "typed content"
