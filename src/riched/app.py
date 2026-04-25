from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import Button, DirectoryTree, Footer, Header, TextArea

from .editor import RichedTextArea
from .screens import FileMenuScreen, KeybindingsScreen, UnsavedChangesScreen
from .syntax import apply_language


class RichedDirectoryTree(DirectoryTree):
    """Directory tree with editor-style keyboard affordances."""

    BINDINGS = [
        *(binding for binding in DirectoryTree.BINDINGS if binding.key != "space"),
        Binding("left", "collapse_cursor", "Collapse folder", show=False),
        Binding("right", "expand_cursor", "Expand folder", show=False),
        Binding("space", "activate_cursor", "Open file or toggle folder", show=False),
    ]

    def _cursor_dir_node(self) -> Any | None:
        node = self.cursor_node
        if node is None or node.data is None or not node.allow_expand:
            return None
        return node

    def action_collapse_cursor(self) -> None:
        node = self._cursor_dir_node()
        if node is not None:
            node.collapse()

    def action_expand_cursor(self) -> None:
        node = self._cursor_dir_node()
        if node is not None:
            node.expand()

    def action_activate_cursor(self) -> None:
        node = self.cursor_node
        if node is None:
            return
        if node.allow_expand:
            node.toggle()
            return
        self.action_select_cursor()


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
    #editor-slot {
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
        initial_path = path.expanduser()
        self._initial_path = None if initial_path.is_dir() else initial_path
        self.path: Path | None = self._initial_path
        self.root = root or Path.cwd()
        self._saved_text = ""
        self._bindings_map = bindings_map

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="menubar"):
            yield Button("File", id="file-btn")
        with Horizontal(id="workspace"):
            yield RichedDirectoryTree(str(self.root), id="file-tree")
            yield Container(id="editor-slot")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "riched"
        if self._initial_path is None:
            self.sub_title = ""
            self.query_one("#file-tree", DirectoryTree).focus()
            return
        self._open_path(self._initial_path)

    def _editor_or_none(self) -> TextArea | None:
        editors = list(self.query("#editor"))
        return editors[0] if editors else None

    def _file_tree(self) -> DirectoryTree:
        return self.query_one("#file-tree", DirectoryTree)

    def _is_file_tree_visible(self) -> bool:
        return self._file_tree().styles.display != "none"

    def _show_file_tree(self) -> None:
        self._file_tree().styles.display = "block"

    def _hide_file_tree(self) -> None:
        self._file_tree().styles.display = "none"

    def _get_or_create_editor(self) -> TextArea:
        editor = self._editor_or_none()
        if editor is not None:
            return editor
        editor = RichedTextArea.code_editor(id="editor")
        self.query_one("#editor-slot", Container).mount(editor)
        return editor

    def _close_buffer(self) -> None:
        self.query_one("#editor-slot", Container).remove_children()
        self.path = None
        self.sub_title = ""
        self._saved_text = ""
        self._show_file_tree()
        self._file_tree().focus()

    def _open_path(self, path: Path) -> None:
        self.path = path.expanduser()
        self.sub_title = str(self.path)
        editor = self._get_or_create_editor()
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
        editor = self._editor_or_none()
        return self.path is not None and editor is not None and editor.text != self._saved_text

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "file-btn":
            self.action_open_file_menu()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        event.stop()
        selected = Path(event.path)
        if selected == self.path:
            editor = self._editor_or_none()
            if editor is not None:
                editor.focus()
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
        if self.path is None:
            self.notify("No file open", severity="warning")
            return
        editor = self._editor_or_none()
        if editor is None:
            self.notify("No file open", severity="warning")
            return
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

    def action_close_buffer(self) -> None:
        if self.path is None:
            return
        if not self._is_dirty():
            self._close_buffer()
            return

        def handle(choice: str) -> None:
            if choice == "save":
                self.action_save()
                if not self._is_dirty():
                    self._close_buffer()
            elif choice == "discard":
                self._close_buffer()

        self.push_screen(UnsavedChangesScreen(), handle)

    def action_toggle_file_tree(self) -> None:
        editor = self._editor_or_none()
        if self._is_file_tree_visible():
            if editor is None:
                return
            self._hide_file_tree()
            editor.focus()
            return
        self._show_file_tree()

    def action_toggle_file_tree_focus(self) -> None:
        tree = self._file_tree()
        if not self._is_file_tree_visible():
            self._show_file_tree()
            tree.focus()
            return
        editor = self._editor_or_none()
        if tree.has_focus:
            if editor is not None:
                editor.focus()
            return
        tree.focus()
