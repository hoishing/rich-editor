from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label, OptionList
from textual.widgets.option_list import Option

from .keybindings import (
    COMMAND_DESCRIPTIONS,
    COMMANDS,
    DEFAULT_BINDINGS,
    build_screen_bindings,
    key_capture_cancel_key,
    save_bindings,
)


class FileMenuScreen(ModalScreen[str | None]):
    """Pulldown-style File menu anchored below the File button."""

    BINDINGS = build_screen_bindings("file_menu")

    CSS = """
    FileMenuScreen {
        align: left top;
        background: transparent;
    }
    FileMenuScreen > #file-menu-wrap {
        offset: 0 2;
        width: 16;
        height: auto;
        background: $panel;
        border: tall $accent;
    }
    FileMenuScreen OptionList {
        background: $panel;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="file-menu-wrap"):
            yield OptionList(
                Option("Save", id="save"),
                Option("Keybindings", id="keybindings"),
                Option("Quit", id="quit"),
                id="file-menu",
            )

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self.dismiss(event.option.id)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            self.dismiss(None)


class UnsavedChangesScreen(ModalScreen[str]):
    """Prompt asking whether to save, discard, or cancel."""

    BINDINGS = build_screen_bindings("unsaved_changes")

    CSS = """
    UnsavedChangesScreen {
        align: center middle;
    }
    UnsavedChangesScreen > #dialog {
        width: 50;
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

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Unsaved changes.\nSave before continuing?")
            with Horizontal(id="buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Discard", variant="error", id="discard")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id or "cancel")

    def action_cancel(self) -> None:
        self.dismiss("cancel")


class KeyCaptureScreen(ModalScreen[str | None]):
    """Modal that captures the next keypress and returns it."""

    CSS = """
    KeyCaptureScreen {
        align: center middle;
    }
    KeyCaptureScreen > #dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $panel;
        border: tall $accent;
    }
    KeyCaptureScreen Label {
        width: 100%;
        content-align: center middle;
    }
    """

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"Press new key for: {self.command}")
            yield Label("(Escape to cancel)")

    def on_key(self, event: events.Key) -> None:
        event.stop()
        event.prevent_default()
        if event.key == key_capture_cancel_key():
            self.dismiss(None)
        else:
            self.dismiss(event.key)


class KeybindingsScreen(ModalScreen[None]):
    """Config page: lists every command and its current key."""

    BINDINGS = build_screen_bindings("keybindings")

    CSS = """
    KeybindingsScreen {
        align: center middle;
    }
    KeybindingsScreen > #dialog {
        width: 64;
        height: auto;
        padding: 1 2;
        background: $panel;
        border: tall $accent;
    }
    KeybindingsScreen #title {
        width: 100%;
        content-align: center middle;
        padding-bottom: 1;
    }
    KeybindingsScreen #table {
        height: auto;
        max-height: 16;
    }
    KeybindingsScreen #hint {
        width: 100%;
        content-align: center middle;
        padding-top: 1;
        color: $text-muted;
    }
    KeybindingsScreen #status {
        width: 100%;
        content-align: center middle;
        padding-top: 1;
        color: $warning;
    }
    """

    def __init__(self, mapping: dict[str, str]) -> None:
        super().__init__()
        self.mapping = dict(mapping)

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Keybindings", id="title")
            yield DataTable(id="table", cursor_type="row", zebra_stripes=True)
            yield Label("Enter/click: edit   r: reset defaults   Esc: close", id="hint")
            yield Label("", id="status")

    def on_mount(self) -> None:
        table = self.query_one("#table", DataTable)
        table.add_columns("Command", "Key")
        self._refresh()
        table.focus()

    def _refresh(self) -> None:
        table = self.query_one("#table", DataTable)
        table.clear()
        for name, desc, _default in COMMANDS:
            table.add_row(desc, self.mapping[name], key=name)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        command = event.row_key.value if event.row_key else None
        if not command:
            return

        def handle(new_key: str | None) -> None:
            if not new_key:
                return
            self.mapping[command] = new_key
            try:
                save_bindings(self.mapping)
            except Exception as exc:
                self.query_one("#status", Label).update(f"Save failed: {exc}")
                return
            self._refresh()
            desc = COMMAND_DESCRIPTIONS.get(command, command)
            self.query_one("#status", Label).update(
                f"Set {desc} -> {new_key}. Restart to apply."
            )

        self.app.push_screen(KeyCaptureScreen(command), handle)

    def action_reset(self) -> None:
        self.mapping = dict(DEFAULT_BINDINGS)
        try:
            save_bindings(self.mapping)
        except Exception as exc:
            self.query_one("#status", Label).update(f"Save failed: {exc}")
            return
        self._refresh()
        self.query_one("#status", Label).update("Reset to defaults. Restart to apply.")

    def action_close(self) -> None:
        self.dismiss(None)
