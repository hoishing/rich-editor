from __future__ import annotations

from textual.widgets import MarkdownViewer, TextArea
from textual.widgets.markdown import MarkdownBlock

from .helpers import _editor, _file_app, _press

SENTINEL = "__clipboard_sentinel__"


def _editor_content_offset(
    editor: TextArea, column: int, row: int = 0
) -> tuple[int, int]:
    return (
        editor.gutter.left + editor.gutter_width + column,
        editor.gutter.top + row,
    )


async def _drag(pilot, widget, start: tuple[int, int], end: tuple[int, int]) -> None:
    await pilot.mouse_down(widget, offset=start)
    await pilot.pause()
    await pilot.hover(widget, offset=end)
    await pilot.pause()
    await pilot.mouse_up(widget, offset=end)
    await pilot.pause()


async def test_editor_mouse_select_copies_source_text() -> None:
    _, _, app = _file_app("hello.txt", "hello world")
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        app.copy_to_clipboard(SENTINEL)

        await _drag(
            pilot,
            editor,
            _editor_content_offset(editor, 0),
            _editor_content_offset(editor, 5),
        )

        assert editor.selected_text == "hello", repr(editor.selected_text)
        assert app.clipboard == "hello", repr(app.clipboard)
        assert "1" not in app.clipboard


async def test_editor_click_without_drag_does_not_copy() -> None:
    _, _, app = _file_app("hello.txt", "hello world")
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        app.copy_to_clipboard(SENTINEL)
        offset = _editor_content_offset(editor, 0)

        await pilot.mouse_down(editor, offset=offset)
        await pilot.pause()
        await pilot.mouse_up(editor, offset=offset)
        await pilot.pause()

        assert editor.selection.is_empty
        assert app.clipboard == SENTINEL, repr(app.clipboard)


async def test_editor_keyboard_selection_does_not_copy() -> None:
    _, _, app = _file_app("hello.txt", "hello world")
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        app.copy_to_clipboard(SENTINEL)
        editor.move_cursor((0, 0))
        await pilot.pause()

        await _press(pilot, "shift+right")

        assert editor.selected_text == "h", repr(editor.selected_text)
        assert app.clipboard == SENTINEL, repr(app.clipboard)


async def test_markdown_preview_mouse_select_copies_rendered_text() -> None:
    _, _, app = _file_app(
        "README.md",
        "# Heading\n\ncopy-me-please\n",
        root_is_tmp=True,
        edit_mode=True,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await _press(pilot, "cmd+shift+v")
        preview = app.query_one("#markdown-preview", MarkdownViewer)
        paragraph = next(
            block
            for block in preview.document.query(MarkdownBlock)
            if (block.source or "").find("copy-me-please") >= 0
        )
        app.copy_to_clipboard(SENTINEL)

        await _drag(pilot, paragraph, (0, 0), (max(1, paragraph.size.width - 1), 0))

        assert "copy-me-please" in app.clipboard, repr(app.clipboard)
        assert "# Heading" not in app.clipboard
        assert SENTINEL not in app.clipboard


async def test_markdown_preview_click_without_drag_does_not_copy() -> None:
    _, _, app = _file_app(
        "README.md",
        "# Heading\n\ncopy-me-please\n",
        root_is_tmp=True,
        edit_mode=True,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await _press(pilot, "cmd+shift+v")
        preview = app.query_one("#markdown-preview", MarkdownViewer)
        paragraph = next(
            block
            for block in preview.document.query(MarkdownBlock)
            if (block.source or "").find("copy-me-please") >= 0
        )
        app.copy_to_clipboard(SENTINEL)

        await pilot.mouse_down(paragraph, offset=(0, 0))
        await pilot.pause()
        await pilot.mouse_up(paragraph, offset=(0, 0))
        await pilot.pause()

        assert app.clipboard == SENTINEL, repr(app.clipboard)
