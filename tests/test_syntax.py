from __future__ import annotations

from textual.widgets import TextArea

from .helpers import _fresh_env, _make_app

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


