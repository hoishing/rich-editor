from __future__ import annotations

import os

from textual.widgets import Footer

from .helpers import _fresh_env, _make_app


async def test_footer_uses_macos_modifier_symbols_with_preferred_markdown_preview() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "footer.txt"
    f.write_text("footer")
    app = _make_app(f, markdown_preview_hotkey_conflicted=False)
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = {
            child.description: child.key_display
            for child in footer.children
            if hasattr(child, "key_display")
        }
        assert labels["Save"] == "⌘S"
        assert "Close buffer" not in labels
        assert labels["Command palette"] == "F1"
        assert labels["Toggle file tree"] == "⌘B"
        assert labels["Quick open"] == "⌘P"
        assert labels["Toggle Markdown preview"] == "⌘⇧V"
        assert not footer.query(".-command-palette")


async def test_footer_uses_markdown_preview_fallback_for_ghostty_conflict() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "footer.txt"
    f.write_text("footer")
    app = _make_app(f, markdown_preview_hotkey_conflicted=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = {
            child.description: child.key_display
            for child in footer.children
            if hasattr(child, "key_display")
        }
        assert labels["Toggle Markdown preview"] == "⌃⇧V"


async def test_footer_defaults_to_markdown_preview_fallback_outside_ghostty() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "footer.txt"
    f.write_text("footer")
    original_term = os.environ.get("TERM")
    original_term_program = os.environ.get("TERM_PROGRAM")
    try:
        os.environ["TERM"] = "xterm-256color"
        os.environ.pop("TERM_PROGRAM", None)
        app = _make_app(f)
    finally:
        if original_term is None:
            os.environ.pop("TERM", None)
        else:
            os.environ["TERM"] = original_term
        if original_term_program is None:
            os.environ.pop("TERM_PROGRAM", None)
        else:
            os.environ["TERM_PROGRAM"] = original_term_program

    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = {
            child.description: child.key_display
            for child in footer.children
            if hasattr(child, "key_display")
        }
        assert labels["Toggle Markdown preview"] == "⌃⇧V"
