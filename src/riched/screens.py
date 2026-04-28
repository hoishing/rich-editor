from __future__ import annotations

from pathlib import Path

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from .keybindings import binding_help_groups, build_screen_bindings
from .quick_open import QuickOpenEntry, ranked_matches

MAX_QUICK_OPEN_RESULTS = 100


class _DismissOnCloseScreen:
    def action_close(self) -> None:
        self.dismiss(None)


class _ConfirmationScreen(ModalScreen[str]):
    """Shared button behavior for simple confirmation dialogs."""

    MESSAGE = ""
    BUTTONS: tuple[tuple[str, str, str | None], ...] = ()

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.MESSAGE)
            with Horizontal(id="buttons"):
                for label, button_id, variant in self.BUTTONS:
                    if variant is None:
                        yield Button(label, id=button_id)
                    else:
                        yield Button(label, variant=variant, id=button_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id or "cancel")

    def on_key(self, event: events.Key) -> None:
        focused = self.focused
        if event.key == "space" and isinstance(focused, Button):
            event.stop()
            event.prevent_default()
            focused.action_press()

    def action_cancel(self) -> None:
        self.dismiss("cancel")


class UnsavedChangesScreen(_ConfirmationScreen):
    """Prompt asking whether to save, discard, or cancel."""

    BINDINGS = build_screen_bindings("unsaved_changes")
    MESSAGE = "Unsaved changes.\nSave before continuing?"
    BUTTONS = (
        ("Save", "save", "primary"),
        ("Discard", "discard", "error"),
        ("Cancel", "cancel", None),
    )
    CSS = """
    UnsavedChangesScreen {
        align: center middle;
    }
    UnsavedChangesScreen > #dialog {
        width: 64;
        height: auto;
        padding: 1 2;
        background: $panel;
        border: tall $accent;
    }
    UnsavedChangesScreen Label {
        width: 100%;
        content-align: center middle;
        padding-bottom: 1;
    }
    UnsavedChangesScreen #buttons {
        height: auto;
        align: center middle;
    }
    UnsavedChangesScreen Button {
        margin: 0 1;
    }
    """


class QuitConfirmationScreen(_ConfirmationScreen):
    """Prompt asking whether to quit a clean session."""

    BINDINGS = build_screen_bindings("quit_confirmation")
    MESSAGE = "Quit riched?"
    BUTTONS = (
        ("Quit", "quit", "error"),
        ("Cancel", "cancel", None),
    )
    CSS = """
    QuitConfirmationScreen {
        align: center middle;
    }
    QuitConfirmationScreen > #dialog {
        width: 44;
        height: auto;
        padding: 1 2;
        background: $panel;
        border: tall $accent;
    }
    QuitConfirmationScreen Label {
        width: 100%;
        content-align: center middle;
        padding-bottom: 1;
    }
    QuitConfirmationScreen #buttons {
        height: auto;
        align: center middle;
    }
    QuitConfirmationScreen Button {
        margin: 0 1;
    }
    """


class QuickOpenScreen(_DismissOnCloseScreen, ModalScreen[Path | None]):
    """Fuzzy file picker."""

    BINDINGS = build_screen_bindings("quick_open")

    CSS = """
    QuickOpenScreen {
        align: center top;
    }
    QuickOpenScreen > #dialog {
        offset-y: 2;
        width: 76;
        height: auto;
        max-height: 24;
        padding: 1 2;
        background: $panel;
        border: tall $accent;
    }
    QuickOpenScreen #query {
        margin-bottom: 1;
    }
    QuickOpenScreen #results {
        height: auto;
        max-height: 18;
    }
    """

    def __init__(
        self,
        root: Path,
        entries: list[QuickOpenEntry],
        *,
        indexing: bool,
        limited: bool,
    ) -> None:
        super().__init__()
        self.root = root
        self.entries = list(entries)
        self._indexing = indexing
        self._limited = limited
        self._error: str | None = None
        self._option_paths: dict[str, Path] = {}
        self._query = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Input(placeholder="Quick open", id="query")
            yield Static("", id="status")
            yield OptionList(id="results")

    def on_mount(self) -> None:
        self._refresh_results("")
        self.query_one("#query", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "query":
            self._refresh_results(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "query":
            self._open_highlighted()

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        path = self._option_paths.get(event.option.id or "")
        if path is not None:
            self.dismiss(path)

    def on_key(self, event: events.Key) -> None:
        results = self.query_one("#results", OptionList)
        if event.key == "up":
            event.stop()
            event.prevent_default()
            results.action_cursor_up()
        elif event.key == "down":
            event.stop()
            event.prevent_default()
            results.action_cursor_down()
        elif event.key == "enter":
            event.stop()
            event.prevent_default()
            self._open_highlighted()

    def append_entries(
        self,
        entries: list[QuickOpenEntry],
        *,
        complete: bool = False,
        limited: bool = False,
    ) -> None:
        self.entries.extend(entries)
        if complete:
            self._indexing = False
        if limited:
            self._limited = True
        self._refresh_results(self._query)

    def replace_entries(
        self,
        entries: list[QuickOpenEntry],
        *,
        complete: bool,
        limited: bool,
    ) -> None:
        self.entries = list(entries)
        self._indexing = not complete
        self._limited = limited
        self._refresh_results(self._query)

    def finish_indexing(self, *, limited: bool) -> None:
        self._indexing = False
        self._limited = limited
        self._refresh_results(self._query)

    def fail_indexing(self, message: str) -> None:
        self._indexing = False
        self._error = message
        self._refresh_results(self._query)

    def _refresh_results(self, query: str) -> None:
        self._query = query
        self._refresh_status()
        results = self.query_one("#results", OptionList)
        results.clear_options()
        self._option_paths.clear()

        matches = self._ranked_matches(query)
        if not matches:
            results.add_option(Option("No matches", id="no-matches", disabled=True))
            return

        options: list[Option] = []
        for index, entry in enumerate(matches[:MAX_QUICK_OPEN_RESULTS]):
            option_id = str(index)
            self._option_paths[option_id] = entry.path
            options.append(Option(entry.relative_path, id=option_id))
        results.add_options(options)
        results.highlighted = 0

    def _refresh_status(self) -> None:
        status = self.query_one("#status", Static)
        if self._error is not None:
            status.update(f"Indexing failed: {self._error}")
        elif self._limited:
            status.update(
                f"Showing first {len(self.entries)} files; index limit reached."
            )
        elif self._indexing:
            status.update(f"Indexing {len(self.entries)} files...")
        else:
            status.update("")

    def _ranked_matches(self, query: str) -> list[QuickOpenEntry]:
        return ranked_matches(self.entries, query, limit=MAX_QUICK_OPEN_RESULTS)

    def _open_highlighted(self) -> None:
        results = self.query_one("#results", OptionList)
        highlighted = results.highlighted
        if highlighted is None:
            return
        try:
            option = results.get_option_at_index(highlighted)
        except Exception:
            return
        path = self._option_paths.get(option.id or "")
        if path is not None:
            self.dismiss(path)


class CreateFileScreen(_DismissOnCloseScreen, ModalScreen[str | None]):
    """Prompt for a file path to create."""

    BINDINGS = build_screen_bindings("create_file")

    CSS = """
    CreateFileScreen {
        align: center top;
    }
    CreateFileScreen > #dialog {
        offset-y: 2;
        width: 76;
        height: auto;
        padding: 1 2;
        background: $panel;
        border: tall $accent;
    }
    CreateFileScreen Label {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Create file")
            yield Input(placeholder="File name", id="filename")

    def on_mount(self) -> None:
        self.query_one("#filename", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filename":
            self.dismiss(event.value)


class KeysHelpScreen(_DismissOnCloseScreen, ModalScreen[None]):
    """Popup key binding help."""

    BINDINGS = build_screen_bindings("keys_help")

    CSS = """
    KeysHelpScreen {
        align: center middle;
    }
    KeysHelpScreen > #dialog {
        width: 80%;
        height: 80%;
        max-width: 96;
        padding: 1 2;
        background: $panel;
        border: tall $accent;
    }
    KeysHelpScreen Label {
        height: auto;
        margin-bottom: 1;
        text-style: bold;
    }
    KeysHelpScreen #bindings-list {
        width: 1fr;
        height: 1fr;
        padding: 0;
        overflow-y: auto;
    }
    KeysHelpScreen .binding-group {
        height: auto;
        margin-bottom: 1;
    }
    KeysHelpScreen .binding-title {
        height: auto;
        color: $text-primary;
        text-style: underline bold;
    }
    KeysHelpScreen .binding-row {
        height: auto;
        layout: horizontal;
    }
    KeysHelpScreen .binding-key {
        width: 38;
        height: auto;
        color: $text-accent;
        text-style: bold;
        padding-right: 1;
    }
    KeysHelpScreen .binding-description {
        width: 1fr;
        height: auto;
        color: $foreground;
    }
    KeysHelpScreen .binding-warning {
        color: $warning;
    }
    KeysHelpScreen .binding-legend {
        height: auto;
        color: $warning;
        margin-top: 1;
    }
    """

    def __init__(self, conflicted_triggers: set[str] | None = None) -> None:
        super().__init__()
        self._conflicted_triggers = conflicted_triggers or set()

    def compose(self) -> ComposeResult:
        has_warnings = False
        with Vertical(id="dialog"):
            yield Label("Key Bindings")
            with Vertical(id="bindings-list"):
                for group in binding_help_groups(self._conflicted_triggers):
                    with Vertical(classes="binding-group"):
                        yield Static(group.title, classes="binding-title")
                        for key, description, conflicted in group.rows:
                            has_warnings = has_warnings or conflicted
                            with Horizontal(classes="binding-row"):
                                display_key = f"⚠️ {key}" if conflicted else key
                                key_classes = (
                                    "binding-key binding-warning"
                                    if conflicted
                                    else "binding-key"
                                )
                                yield Static(display_key, classes=key_classes)
                                yield Static(description, classes="binding-description")
                if has_warnings:
                    yield Static(
                        "⚠️ Unbind this shortcut in Ghostty config to use it in riched.",
                        classes="binding-legend",
                    )
