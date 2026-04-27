from __future__ import annotations

from textual.widgets import Markdown, MarkdownViewer, Static, TextArea

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


async def test_cmd_shift_v_warns_for_non_markdown_file() -> None:
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

        await pilot.press("cmd+shift+v")
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


async def test_markdown_preview_external_link_opens_without_navigation() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "README.md"
    f.write_text("[Rich](https://github.com/Textualize/rich)")
    app = _make_app(f, root=tmp)
    opened_urls: list[str] = []
    app.open_url = lambda url, **kwargs: opened_urls.append(url)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("cmd+shift+v")
        await pilot.pause()

        preview = app.query_one("#markdown-preview", MarkdownViewer)
        preview.document.post_message(
            Markdown.LinkClicked(
                preview.document,
                "https://github.com/Textualize/rich",
            )
        )
        await pilot.pause()

        assert opened_urls == ["https://github.com/Textualize/rich"]
        assert preview.document.source == "[Rich](https://github.com/Textualize/rich)"


async def test_keys_help_includes_markdown_preview_binding() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "README.md"
    f.write_text("# Title")
    app = _make_app(f, root=tmp, ghostty_app_hotkey_conflicts=set())
    async with app.run_test() as pilot:
        await pilot.pause()

        app.action_show_keys_popup()
        await pilot.pause()

        rows = [
            (row.children[0].content, row.children[1].content)
            for row in app.screen.query(".binding-row")
        ]
        assert ("⌘⇧V", "Toggle Markdown preview") in rows


async def test_keys_help_warns_for_ghostty_conflicted_markdown_preview() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "README.md"
    f.write_text("# Title")
    app = _make_app(
        f,
        root=tmp,
        ghostty_app_hotkey_conflicts={"toggle_markdown_preview"},
    )
    async with app.run_test() as pilot:
        await pilot.pause()

        app.action_show_keys_popup()
        await pilot.pause()

        rows = [
            (row.children[0].content, row.children[1].content)
            for row in app.screen.query(".binding-row")
        ]
        assert ("⚠️ ⌘⇧V", "Toggle Markdown preview") in rows
        assert (
            app.screen.query_one(".binding-legend", Static).content
            == "⚠️ Unbind this shortcut in Ghostty config to use it in riched."
        )
