from __future__ import annotations

from textual.widgets import MarkdownViewer, TextArea

from .helpers import _fresh_env, _make_app


async def test_cmd_shift_v_toggles_markdown_preview() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "README.md"
    f.write_text("# Title\n\nBody")
    app = _make_app(f, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)

        await pilot.press("cmd+shift+v")
        await pilot.pause()

        preview = app.query_one("#markdown-preview", MarkdownViewer)
        assert editor.styles.display == "none"
        assert preview.document.source == "# Title\n\nBody"

        await pilot.press("cmd+shift+v")
        await pilot.pause()

        assert not list(app.query("#markdown-preview"))
        assert editor.styles.display == "block"
        assert editor.has_focus


async def test_super_shift_v_toggles_markdown_preview_alias() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "README.markdown"
    f.write_text("# Title")
    app = _make_app(f, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("super+shift+v")
        await pilot.pause()

        assert app.query_one("#markdown-preview", MarkdownViewer).document.source == "# Title"


async def test_ctrl_shift_v_toggles_markdown_preview_fallback() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "README.md"
    f.write_text("# Title")
    app = _make_app(f, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("ctrl+shift+v")
        await pilot.pause()

        assert app.query_one("#markdown-preview", MarkdownViewer).document.source == "# Title"


async def test_markdown_preview_uses_unsaved_editor_content() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "README.md"
    f.write_text("# Saved")
    app = _make_app(f, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.load_text("# Unsaved\n\nPreview this")

        await pilot.press("cmd+shift+v")
        await pilot.pause()

        preview = app.query_one("#markdown-preview", MarkdownViewer)
        assert preview.document.source == "# Unsaved\n\nPreview this"
        assert f.read_text() == "# Saved"


async def test_ctrl_shift_v_warns_for_non_markdown_file() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "notes.txt"
    f.write_text("# Plain text")
    app = _make_app(f, root=tmp)
    notifications: list[tuple[str, str | None]] = []
    app.notify = lambda message, **kwargs: notifications.append(
        (str(message), kwargs.get("severity"))
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)

        await pilot.press("ctrl+shift+v")
        await pilot.pause()

        assert not list(app.query("#markdown-preview"))
        assert editor.styles.display == "block"
        assert notifications == [
            ("Markdown preview is only available for Markdown files.", "warning")
        ]


async def test_switching_files_exits_markdown_preview() -> None:
    tmp, _ = _fresh_env()
    first = tmp / "first.md"
    second = tmp / "second.md"
    first.write_text("# First")
    second.write_text("# Second")
    app = _make_app(first, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("cmd+shift+v")
        await pilot.pause()
        assert app.query_one("#markdown-preview", MarkdownViewer)

        app._switch_path(second)
        await pilot.pause()

        editor = app.query_one("#editor", TextArea)
        assert not list(app.query("#markdown-preview"))
        assert editor.styles.display == "block"
        assert editor.text == "# Second"
        assert editor.has_focus


async def test_keys_help_includes_markdown_preview_binding() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "README.md"
    f.write_text("# Title")
    app = _make_app(f, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()

        app.action_show_keys_popup()
        await pilot.pause()

        rows = [
            (row.children[0].content, row.children[1].content)
            for row in app.screen.query(".binding-row")
        ]
        assert ("cmd+shift+v / ctrl+shift+v", "Toggle Markdown preview") in rows
