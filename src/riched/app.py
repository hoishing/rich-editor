from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from textual import events
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.command import CommandPalette
from textual.containers import Container, Horizontal
from textual.keys import format_key
from textual.screen import Screen
from textual.widgets import DirectoryTree, Footer, Header, Static, TextArea

from .editor import RichedTextArea
from .keybindings import display_key
from .screens import KeysHelpScreen, QuickOpenScreen, UnsavedChangesScreen
from .settings import load_theme, save_theme
from .syntax import apply_language

FILE_TREE_DEFAULT_WIDTH = 30
FILE_TREE_MIN_WIDTH = 18
FILE_TREE_MAX_WIDTH = 44
QUICK_OPEN_SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
KEY_MODIFIER_SYMBOLS = {
    "cmd": "⌘",
    "super": "⌘",
    "ctrl": "⌃",
    "control": "⌃",
    "alt": "⌥",
    "option": "⌥",
    "shift": "⇧",
}


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


class FileTreeResizeHandle(Static):
    """Mouse handle for resizing the file tree."""

    can_focus = False

    def __init__(self) -> None:
        super().__init__("", id="file-tree-resize-handle")
        self._drag_start_x: int | None = None
        self._drag_start_width: int | None = None

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button != 1 or event.screen_x is None:
            return
        tree = self.app.query_one("#file-tree", DirectoryTree)
        self._drag_start_x = int(event.screen_x)
        self._drag_start_width = tree.region.width
        self.capture_mouse()
        self.add_class("dragging")
        event.stop()
        event.prevent_default()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self._drag_start_x is None or self._drag_start_width is None:
            return
        if event.screen_x is None:
            return
        delta = int(event.screen_x) - self._drag_start_x
        app = self.app
        if isinstance(app, RichedApp):
            app.set_file_tree_width(self._drag_start_width + delta)
        event.stop()
        event.prevent_default()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self._drag_start_x is None:
            return
        self._drag_start_x = None
        self._drag_start_width = None
        self.release_mouse()
        self.remove_class("dragging")
        event.stop()
        event.prevent_default()


class RichedApp(App):
    """TUI text editor with a project file tree."""

    CSS = """
    #workspace {
        height: 1fr;
    }
    #file-tree {
        width: 30;
        min-width: 18;
        max-width: 44;
    }
    #file-tree-resize-handle {
        width: 1;
        min-width: 1;
        max-width: 1;
        height: 1fr;
        background: $panel;
    }
    #file-tree-resize-handle:hover,
    #file-tree-resize-handle.dragging {
        background: $accent;
    }
    #editor {
        height: 1fr;
        width: 1fr;
    }
    #editor-slot {
        height: 1fr;
        width: 1fr;
    }
    HeaderIcon {
        display: none;
    }
    """

    BINDINGS: list[Binding] = []

    def __init__(
        self,
        path: Path,
        root: Path | None = None,
    ) -> None:
        super().__init__()
        saved_theme = load_theme()
        if saved_theme in self.available_themes:
            self.theme = saved_theme
        self.watch(self, "theme", self._save_theme, init=False)
        initial_path = path.expanduser()
        self._initial_path = None if initial_path.is_dir() else initial_path
        self.path: Path | None = self._initial_path
        self.root = root or Path.cwd()
        self._saved_text = ""

    def _save_theme(self, theme: str) -> None:
        try:
            save_theme(theme)
        except Exception as exc:
            self.notify(f"Could not save theme: {exc}", severity="warning")

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        for command in super().get_system_commands(screen):
            if command.title == "Maximize":
                continue
            if command.title == "Keys":
                yield SystemCommand(
                    "Keys",
                    "Show key bindings",
                    self.action_show_keys_popup,
                )
                continue
            yield command

    def get_key_display(self, binding: Binding) -> str:
        if binding.key_display:
            return binding.key_display

        key = display_key(binding.key)
        parts = key.split("+")
        base_key = format_key(parts[-1])
        if len(base_key) == 1:
            base_key = base_key.upper()
        else:
            base_key = base_key.title()
        modifiers = "".join(
            KEY_MODIFIER_SYMBOLS.get(part, part) for part in parts[:-1]
        )
        return f"{modifiers}{base_key}"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="workspace"):
            yield RichedDirectoryTree(str(self.root), id="file-tree")
            yield FileTreeResizeHandle()
            yield Container(id="editor-slot")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "riched"
        self.set_file_tree_width(FILE_TREE_DEFAULT_WIDTH)
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

    def _file_tree_resize_handle(self) -> Static:
        return self.query_one("#file-tree-resize-handle", Static)

    def _is_file_tree_visible(self) -> bool:
        return self._file_tree().styles.display != "none"

    def _show_file_tree(self) -> None:
        self._file_tree().styles.display = "block"
        self._file_tree_resize_handle().styles.display = "block"

    def _hide_file_tree(self) -> None:
        self._file_tree().styles.display = "none"
        self._file_tree_resize_handle().styles.display = "none"

    def set_file_tree_width(self, width: int) -> None:
        clamped_width = max(FILE_TREE_MIN_WIDTH, min(FILE_TREE_MAX_WIDTH, width))
        tree = self._file_tree()
        tree.styles.width = clamped_width
        tree.refresh(layout=True)

    def _get_or_create_editor(self) -> TextArea:
        editor = self._editor_or_none()
        if editor is not None:
            return editor
        editor = RichedTextArea.code_editor(id="editor", theme="css")
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

    def _quick_open_files(self) -> list[Path]:
        root = self.root.expanduser()
        files: list[Path] = []
        stack = [root]
        while stack:
            directory = stack.pop()
            try:
                entries = sorted(directory.iterdir(), key=lambda path: path.name.lower())
            except OSError:
                continue
            for entry in entries:
                try:
                    if entry.is_dir():
                        if entry.name not in QUICK_OPEN_SKIP_DIRS and not entry.is_symlink():
                            stack.append(entry)
                    elif entry.is_file():
                        files.append(entry)
                except OSError:
                    continue
        return sorted(files, key=lambda path: path.relative_to(root).as_posix().lower())

    def action_quick_open(self) -> None:
        def handle(selected: Path | None) -> None:
            if selected is not None:
                self._switch_path(selected)

        self.push_screen(
            QuickOpenScreen(self.root.expanduser(), self._quick_open_files()),
            handle,
        )

    def action_toggle_command_palette(self) -> None:
        if CommandPalette.is_open(self):
            self.pop_screen()
            return
        self.action_command_palette()

    def action_show_keys_popup(self) -> None:
        self.push_screen(KeysHelpScreen())

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
