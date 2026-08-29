from __future__ import annotations

from subprocess import CompletedProcess

from textual.widgets import Footer

from .helpers import _directory_app, _file_app, _footer_labels, _temporary_env
from rich_editor.keybindings import ghostty_conflicted_hotkey_triggers


def _footer_app(name: str = "footer.txt", content: str = "footer", **kwargs):
    return _file_app(name, content, **kwargs)[2]


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
    app = _footer_app(
        "footer.md",
        "# footer",
        ghostty_conflicted_hotkey_triggers=set(),
        in_ghostty=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = _footer_labels(footer)
        assert set(labels) == {
            "Save",
            "Command palette",
            "Toggle sidebar",
            "Quick open",
            "Replace",
            "Create file",
            "Toggle Markdown preview",
            "Format document",
            "Refresh",
        }
        assert labels["Save"] == "⌘S"
        assert labels["Command palette"] == "F1"
        assert labels["Toggle sidebar"] == "⌘B"
        assert labels["Quick open"] == "⌘P"
        assert labels["Replace"] == "⌃H"
        assert labels["Create file"] == "⌃N"
        assert labels["Toggle Markdown preview"] == "⌘⇧V"
        assert labels["Format document"] == "⌥⇧F"
        assert labels["Refresh"] == "⌘R"
        assert not footer.query(".-command-palette")


async def test_footer_shows_ctrl_b_for_sidebar_in_ghostty() -> None:
    app = _footer_app(ghostty_conflicted_hotkey_triggers=set(), in_ghostty=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = _footer_labels(footer)
        assert labels["Toggle sidebar"] == "⌃B"


async def test_footer_keeps_command_palette_f1_when_ghostty_has_no_cmd_shift_p_conflict() -> None:
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
        assert labels["Command palette"] == "F1"
        assert "Toggle Markdown preview" not in labels


async def test_footer_hides_markdown_preview_for_ghostty_conflict() -> None:
    app = _footer_app(
        "footer.md",
        "# footer",
        markdown_preview_hotkey_conflicted=True,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = _footer_labels(footer)
        assert labels["Toggle Markdown preview"] == "⌃⇧V"


async def test_footer_hides_markdown_preview_outside_ghostty() -> None:
    with _temporary_env(TERM="xterm-256color", TERM_PROGRAM=None):
        app = _footer_app("footer.md", "# footer")

    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        labels = _footer_labels(footer)
        assert labels["Command palette"] == "F1"
        assert labels["Toggle sidebar"] == "⌘B"
        assert labels["Toggle Markdown preview"] == "⌃⇧V"


async def test_footer_uses_markdown_preview_preferred_when_ghostty_unbound() -> None:
    app = _footer_app(
        "footer.md",
        "# footer",
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


async def test_footer_shows_markdown_preview_for_open_markdown_file() -> None:
    app = _footer_app(
        "notes.md",
        "# notes",
        edit_mode=True,
        ghostty_conflicted_hotkey_triggers=set(),
        in_ghostty=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        labels = _footer_labels(app.query_one(Footer))
        assert labels["Toggle Markdown preview"] == "⌘⇧V"


async def test_footer_shows_markdown_preview_for_markdown_extension() -> None:
    app = _footer_app(
        "notes.markdown",
        "# notes",
        edit_mode=True,
        ghostty_conflicted_hotkey_triggers=set(),
        in_ghostty=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        labels = _footer_labels(app.query_one(Footer))
        assert labels["Toggle Markdown preview"] == "⌘⇧V"


async def test_footer_shows_markdown_preview_while_preview_is_open() -> None:
    _, _, app = _file_app(
        "notes.md",
        "# notes",
        root_is_tmp=True,
        ghostty_conflicted_hotkey_triggers=set(),
        in_ghostty=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        assert list(app.query("#markdown-preview"))
        labels = _footer_labels(app.query_one(Footer))
        assert labels["Toggle Markdown preview"] == "⌘⇧V"


async def test_footer_hides_markdown_preview_for_non_markdown_file() -> None:
    app = _footer_app(ghostty_conflicted_hotkey_triggers=set(), in_ghostty=False)
    async with app.run_test() as pilot:
        await pilot.pause()
        labels = _footer_labels(app.query_one(Footer))
        assert "Toggle Markdown preview" not in labels


async def test_footer_hides_markdown_preview_with_no_buffer() -> None:
    _, app = _directory_app(
        ghostty_conflicted_hotkey_triggers=set(), in_ghostty=False
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        labels = _footer_labels(app.query_one(Footer))
        assert "Toggle Markdown preview" not in labels


async def test_footer_hides_markdown_preview_after_switching_from_markdown() -> None:
    tmp, _, app = _file_app(
        "notes.md",
        "# notes",
        root_is_tmp=True,
        edit_mode=True,
        ghostty_conflicted_hotkey_triggers=set(),
        in_ghostty=False,
    )
    other = tmp / "notes.txt"
    other.write_text("plain")
    async with app.run_test() as pilot:
        await pilot.pause()
        app._switch_path(other)
        await pilot.pause()
        labels = _footer_labels(app.query_one(Footer))
        assert "Toggle Markdown preview" not in labels


async def test_footer_shows_markdown_preview_after_opening_markdown_from_directory() -> None:
    tmp, app = _directory_app(
        ghostty_conflicted_hotkey_triggers=set(), in_ghostty=False
    )
    path = tmp / "notes.md"
    path.write_text("# notes")
    async with app.run_test() as pilot:
        await pilot.pause()
        app._switch_path(path)
        await pilot.pause()
        labels = _footer_labels(app.query_one(Footer))
        assert labels["Toggle Markdown preview"] == "⌘⇧V"


async def test_footer_hides_markdown_preview_after_closing_markdown_buffer() -> None:
    _, _, app = _file_app(
        "notes.md",
        "# notes",
        root_is_tmp=True,
        edit_mode=True,
        ghostty_conflicted_hotkey_triggers=set(),
        in_ghostty=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_close_buffer()
        await pilot.pause()
        labels = _footer_labels(app.query_one(Footer))
        assert "Toggle Markdown preview" not in labels
