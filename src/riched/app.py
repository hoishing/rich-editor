from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Button, DirectoryTree, Footer, Header, TextArea

from .editor import RichedTextArea
from .screens import FileMenuScreen, KeybindingsScreen, UnsavedChangesScreen
from .syntax import apply_language


class RichedApp(App):
    """TUI text editor with a project file tree."""

    CSS = """
    #menubar {
        height: 1;
        background: $panel;
    }
    #file-btn {
        min-width: 8;
        height: 1;
        border: none;
        background: $panel;
        color: $text;
    }
    #file-btn:hover {
        background: $accent;
    }
    #workspace {
        height: 1fr;
    }
    #file-tree {
        width: 30;
        min-width: 18;
        max-width: 44;
        border-right: solid $panel;
    }
    #editor {
        height: 1fr;
        width: 1fr;
    }
    """

    BINDINGS: list[Binding] = []

    def __init__(
        self,
        path: Path,
        bindings_map: dict[str, str],
        root: Path | None = None,
    ) -> None:
        super().__init__()
        self.path = path
        self.root = root or Path.cwd()
        self._saved_text = ""
        self._bindings_map = bindings_map

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="menubar"):
            yield Button("File", id="file-btn")
        with Horizontal(id="workspace"):
            yield DirectoryTree(str(self.root), id="file-tree")
            yield RichedTextArea.code_editor(id="editor")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "riched"
        self._open_path(self.path)

    def _open_path(self, path: Path) -> None:
        self.path = path.expanduser()
        self.sub_title = str(self.path)
        editor = self.query_one("#editor", TextArea)
        if self.path.exists():
            try:
                content = self.path.read_text()
            except Exception as exc:
                self.notify(f"Could not read: {exc}", severity="error")
                content = ""
        else:
            content = ""
        editor.load_text(content)
        self._saved_text = content
        try:
            apply_language(editor, self.path.suffix)
        except Exception as exc:
            self.notify(f"Syntax highlight off: {exc}", severity="warning")
        editor.focus()

    def _is_dirty(self) -> bool:
        return self.query_one("#editor", TextArea).text != self._saved_text

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "file-btn":
            self.action_open_file_menu()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        event.stop()
        selected = Path(event.path)
        if selected == self.path:
            self.query_one("#editor", TextArea).focus()
            return
        self._switch_path(selected)

    def _switch_path(self, selected: Path) -> None:
        if not self._is_dirty():
            self._open_path(selected)
            return

        def handle(choice: str) -> None:
            if choice == "save":
                self.action_save()
                if not self._is_dirty():
                    self._open_path(selected)
            elif choice == "discard":
                self._open_path(selected)

        self.push_screen(UnsavedChangesScreen(), handle)

    def action_open_file_menu(self) -> None:
        def handle(choice: str | None) -> None:
            if choice == "save":
                self.action_save()
            elif choice == "quit":
                self.action_quit_check()
            elif choice == "keybindings":
                self.action_open_keybindings()

        self.push_screen(FileMenuScreen(), handle)

    def action_open_keybindings(self) -> None:
        self.push_screen(KeybindingsScreen(self._bindings_map))

    def action_save(self) -> None:
        editor = self.query_one("#editor", TextArea)
        try:
            self.path.write_text(editor.text)
        except Exception as exc:
            self.notify(f"Save failed: {exc}", severity="error")
            return
        self._saved_text = editor.text
        self.notify(f"Saved {self.path}")

    def action_quit_check(self) -> None:
        if not self._is_dirty():
            self.exit()
            return

        def handle(choice: str) -> None:
            if choice == "save":
                self.action_save()
                if not self._is_dirty():
                    self.exit()
            elif choice == "discard":
                self.exit()

        self.push_screen(UnsavedChangesScreen(), handle)

