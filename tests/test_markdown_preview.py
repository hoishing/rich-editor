from __future__ import annotations

from textual.widgets import DirectoryTree, Markdown, MarkdownViewer, Static

from .helpers import _editor, _file_app, _key_help_rows, _press


async def test_markdown_preview_toggles_from_primary_key() -> None:
    _, _, app = _file_app("README.md", "# Title\n\nBody", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)

        await _press(pilot, "cmd+shift+v")

        preview = app.query_one("#markdown-preview", MarkdownViewer)
        assert editor.styles.display == "none"
        assert preview.document.source == "# Title\n\nBody"

        await _press(pilot, "cmd+shift+v")

        assert not list(app.query("#markdown-preview"))
        assert editor.styles.display == "block"
        assert editor.has_focus


async def test_markdown_preview_opens_from_alias_keys() -> None:
    for key, name in (("cmd+shift+v", "README.md"), ("super+shift+v", "README.markdown")):
        _, _, app = _file_app(name, "# Title", root_is_tmp=True)
        async with app.run_test() as pilot:
            await pilot.pause()
            await _press(pilot, key)
            preview = app.query_one("#markdown-preview", MarkdownViewer)
            assert preview.document.source == "# Title", key


async def test_markdown_preview_uses_unsaved_editor_content() -> None:
    _, f, app = _file_app("README.md", "# Saved", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        editor.load_text("# Unsaved\n\nPreview this")

        await _press(pilot, "cmd+shift+v")

        preview = app.query_one("#markdown-preview", MarkdownViewer)
        assert preview.document.source == "# Unsaved\n\nPreview this"
        assert f.read_text() == "# Saved"


async def test_markdown_preview_toc_button_only_shows_for_preview() -> None:
    _, _, app = _file_app(
        "README.md",
        "# Title\n\n## Section",
        root_is_tmp=True,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        toc_button = app.query_one("#markdown-toc-button", Static)
        assert toc_button.content == "☰"
        assert toc_button.styles.display == "none"

        await _press(pilot, "cmd+shift+v")

        preview = app.query_one("#markdown-preview", MarkdownViewer)
        assert toc_button.styles.display == "block"
        assert preview.show_table_of_contents is False

        await pilot.click("#markdown-toc-button")
        await pilot.pause()

        assert preview.show_table_of_contents is True

        await pilot.click("#markdown-toc-button")
        await pilot.pause()

        assert preview.show_table_of_contents is False

        await _press(pilot, "cmd+shift+v")

        assert not list(app.query("#markdown-preview"))
        assert toc_button.styles.display == "none"


async def test_cmd_shift_v_warns_for_non_markdown_file() -> None:
    _, _, app = _file_app("notes.txt", "# Plain text", root_is_tmp=True)
    notifications: list[tuple[str, str | None]] = []
    app.notify = lambda message, **kwargs: notifications.append(
        (str(message), kwargs.get("severity"))
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)

        await _press(pilot, "cmd+shift+v")

        assert not list(app.query("#markdown-preview"))
        assert editor.styles.display == "block"
        assert notifications == [
            ("Markdown preview is only available for Markdown files.", "warning")
        ]


async def test_switching_files_exits_markdown_preview() -> None:
    tmp, first, app = _file_app("first.md", "# First", root_is_tmp=True)
    second = tmp / "second.md"
    second.write_text("# Second")
    async with app.run_test() as pilot:
        await pilot.pause()

        await _press(pilot, "cmd+shift+v")
        assert app.query_one("#markdown-preview", MarkdownViewer)

        app._switch_path(second)
        await pilot.pause()

        editor = _editor(app)
        assert not list(app.query("#markdown-preview"))
        assert editor.styles.display == "block"
        assert editor.text == "# Second"
        assert editor.has_focus


async def test_markdown_preview_external_link_opens_without_navigation() -> None:
    _, _, app = _file_app(
        "README.md",
        "[Rich](https://github.com/Textualize/rich)",
        root_is_tmp=True,
    )
    opened_urls: list[str] = []
    app.open_url = lambda url, **kwargs: opened_urls.append(url)
    async with app.run_test() as pilot:
        await pilot.pause()

        await _press(pilot, "cmd+shift+v")

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


async def test_markdown_preview_escape_focuses_file_tree() -> None:
    _, _, app = _file_app("README.md", "# Title", root_is_tmp=True)
    async with app.run_test() as pilot:
        await pilot.pause()

        await _press(pilot, "cmd+shift+v")
        preview = app.query_one("#markdown-preview", MarkdownViewer)
        tree = app.query_one("#file-tree", DirectoryTree)
        assert preview.document.has_focus

        await _press(pilot, "escape")

        assert tree.has_focus
        assert app.query_one("#markdown-preview", MarkdownViewer)


async def test_keys_help_includes_markdown_preview_binding() -> None:
    _, _, app = _file_app(
        "README.md",
        "# Title",
        root_is_tmp=True,
        ghostty_conflicted_hotkey_triggers=set(),
    )
    async with app.run_test() as pilot:
        await pilot.pause()

        app.action_show_keys_popup()
        await pilot.pause()

        rows = _key_help_rows(app)
        assert ("⌘⇧V", "Toggle Markdown preview") in rows


async def test_keys_help_warns_for_ghostty_conflicted_markdown_preview() -> None:
    _, _, app = _file_app(
        "README.md",
        "# Title",
        root_is_tmp=True,
        ghostty_conflicted_hotkey_triggers={"super+shift+v"},
    )
    async with app.run_test() as pilot:
        await pilot.pause()

        app.action_show_keys_popup()
        await pilot.pause()

        rows = _key_help_rows(app)
        assert ("⚠️ ⌘⇧V", "Toggle Markdown preview") in rows
        assert (
            app.screen.query_one(".binding-legend", Static).content
            == "⚠️ Unbind this shortcut in Ghostty config to use it in Rich Editor."
        )
