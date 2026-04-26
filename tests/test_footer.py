from __future__ import annotations

from textual.widgets import Footer

from .helpers import _fresh_env, _make_app


async def test_footer_uses_macos_modifier_symbols() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "footer.txt"
    f.write_text("footer")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = {
            child.description: child.key_display
            for child in footer.children
            if hasattr(child, "key_display")
        }
        assert labels["Save"] == "⌃S"
        assert labels["Close buffer"] == "⌃W"
        assert labels["Toggle file tree"] == "⌘B"
        assert labels["Quick open"] == "⌘P"
