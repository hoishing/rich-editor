from __future__ import annotations

from pathlib import Path

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from .keybindings import binding_help_groups, build_screen_bindings

MAX_QUICK_OPEN_RESULTS = 100


class UnsavedChangesScreen(ModalScreen[str]):
    """Prompt asking whether to save, discard, or cancel."""

    BINDINGS = build_screen_bindings("unsaved_changes")

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

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Unsaved changes.\nSave before continuing?")
            with Horizontal(id="buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Discard", variant="error", id="discard")
                yield Button("Cancel", id="cancel")

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


class QuickOpenScreen(ModalScreen[Path | None]):
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

    def __init__(self, root: Path, files: list[Path]) -> None:
        super().__init__()
        self.root = root
        self.files = files
        self._relative_paths = {
            path: path.relative_to(root).as_posix() for path in files
        }
        self._option_paths: dict[str, Path] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Input(placeholder="Quick open", id="query")
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

    def action_close(self) -> None:
        self.dismiss(None)

    def _refresh_results(self, query: str) -> None:
        results = self.query_one("#results", OptionList)
        results.clear_options()
        self._option_paths.clear()

        matches = self._ranked_matches(query)
        if not matches:
            results.add_option(Option("No matches", id="no-matches", disabled=True))
            return

        options: list[Option] = []
        for index, path in enumerate(matches[:MAX_QUICK_OPEN_RESULTS]):
            option_id = str(index)
            self._option_paths[option_id] = path
            options.append(Option(self._relative_paths[path], id=option_id))
        results.add_options(options)
        results.highlighted = 0

    def _ranked_matches(self, query: str) -> list[Path]:
        stripped_query = query.strip()
        if not stripped_query:
            return sorted(self.files, key=lambda path: self._relative_paths[path].lower())

        scored: list[tuple[tuple[int, int, int, int, str], Path]] = []
        for path in self.files:
            relative_path = self._relative_paths[path]
            score = _fuzzy_score(stripped_query, relative_path)
            if score is not None:
                scored.append((score, path))
        scored.sort(key=lambda item: item[0])
        return [path for _score, path in scored]

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


class KeysHelpScreen(ModalScreen[None]):
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
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Key Bindings")
            with Vertical(id="bindings-list"):
                for group in binding_help_groups():
                    with Vertical(classes="binding-group"):
                        yield Static(group.title, classes="binding-title")
                        for key, description in group.rows:
                            with Horizontal(classes="binding-row"):
                                yield Static(key, classes="binding-key")
                                yield Static(description, classes="binding-description")

    def action_close(self) -> None:
        self.dismiss(None)


def _fuzzy_score(query: str, candidate: str) -> tuple[int, int, int, int, str] | None:
    query_lower = query.lower()
    candidate_lower = candidate.lower()
    positions: list[int] = []
    search_from = 0
    for char in query_lower:
        index = candidate_lower.find(char, search_from)
        if index == -1:
            return None
        positions.append(index)
        search_from = index + 1

    first = positions[0]
    last = positions[-1]
    spread = last - first + 1
    gaps = spread - len(query_lower)
    basename = Path(candidate_lower).name
    basename_index = candidate_lower.rfind(basename)
    basename_bonus = 0 if first >= basename_index else 1
    contiguous_bonus = 0 if query_lower in candidate_lower else 1
    return (basename_bonus, contiguous_bonus, gaps, len(candidate_lower), candidate_lower)
