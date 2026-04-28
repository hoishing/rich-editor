from __future__ import annotations

from subprocess import CompletedProcess

from textual.widgets import Footer

from .helpers import _file_app, _footer_labels, _temporary_env
from riched.keybindings import ghostty_conflicted_hotkey_triggers


def _footer_app(**kwargs):
    return _file_app("footer.txt", "footer", **kwargs)[2]


def _conflicts_from_config(*lines: str) -> set[str]:
    config = "\n".join(lines)
    return ghostty_conflicted_hotkey_triggers(
        env={"TERM_PROGRAM": "ghostty"},
        run_command=lambda *args, **kwargs: CompletedProcess(
            args[0],
            0,
            stdout=config,
            stderr="",
        ),
        find_binary=lambda name: name,
    )


async def test_footer_uses_macos_modifier_symbols_with_preferred_markdown_preview() -> None:
    app = _footer_app(ghostty_conflicted_hotkey_triggers=set())
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = _footer_labels(footer)
        assert set(labels) == {
            "Save",
            "Command palette",
            "Toggle file tree",
            "Quick open",
            "Create file",
            "Toggle Markdown preview",
            "Format document",
            "Refresh",
        }
        assert labels["Save"] == "⌘S"
        assert labels["Command palette"] == "⌘⇧P"
        assert labels["Toggle file tree"] == "⌘B"
        assert labels["Quick open"] == "⌘P"
        assert labels["Create file"] == "⌥N"
        assert labels["Toggle Markdown preview"] == "⌘⇧V"
        assert labels["Format document"] == "⌥⇧F"
        assert labels["Refresh"] == "⌘R"
        assert not footer.query(".-command-palette")


async def test_footer_uses_command_palette_alternative_for_ghostty_conflict() -> None:
    app = _footer_app(ghostty_conflicted_hotkey_triggers={"super+shift+p"})
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = _footer_labels(footer)
        assert labels["Command palette"] == "F1"


async def test_footer_uses_command_palette_preferred_when_ghostty_unbound() -> None:
    app = _footer_app(
        ghostty_conflicted_hotkey_triggers=_conflicts_from_config(
            "keybind = super+shift+,=reload_config",
            "keybind = super+shift+v=toggle_quick_terminal",
        )
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = _footer_labels(footer)
        assert labels["Command palette"] == "⌘⇧P"
        assert "Toggle Markdown preview" not in labels


async def test_footer_hides_markdown_preview_for_ghostty_conflict() -> None:
    app = _footer_app(markdown_preview_hotkey_conflicted=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = _footer_labels(footer)
        assert "Toggle Markdown preview" not in labels


async def test_footer_hides_markdown_preview_outside_ghostty() -> None:
    with _temporary_env(TERM="xterm-256color", TERM_PROGRAM=None):
        app = _footer_app()

    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = _footer_labels(footer)
        assert labels["Command palette"] == "F1"
        assert "Toggle Markdown preview" not in labels


async def test_footer_uses_markdown_preview_preferred_when_ghostty_unbound() -> None:
    app = _footer_app(
        ghostty_conflicted_hotkey_triggers=_conflicts_from_config(
            "keybind = super+shift+,=reload_config",
            "keybind = super+shift+v=unbind",
        )
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = _footer_labels(footer)
        assert labels["Toggle Markdown preview"] == "⌘⇧V"
