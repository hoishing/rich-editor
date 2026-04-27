from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from itertools import groupby
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from textual import events, work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.command import CommandPalette
from textual.containers import Container, Horizontal
from textual.keys import format_key
from textual.screen import Screen
from textual.worker import get_current_worker
from textual.widgets import (
    DirectoryTree,
    Footer,
    Header,
    MarkdownViewer,
    Static,
    TextArea,
)
from textual.widgets._footer import FooterKey, FooterLabel, KeyGroup

from .editor import RichedTextArea
from .keybindings import (
    DEFAULT_BINDINGS,
    app_binding_display_key,
    ghostty_app_hotkey_conflicts,
)
from .quick_open import (
    MAX_QUICK_OPEN_INDEX_FILES,
    QUICK_OPEN_BATCH_SIZE,
    QuickOpenEntry,
    git_quick_open_entries,
    scan_quick_open_entries,
)
from .screens import (
    KeysHelpScreen,
    QuickOpenScreen,
    QuitConfirmationScreen,
    UnsavedChangesScreen,
)
from .settings import load_theme, save_theme
from .syntax import apply_language

FILE_TREE_DEFAULT_WIDTH = 30
FILE_TREE_MIN_WIDTH = 18
FILE_TREE_MAX_WIDTH = 44
KEY_MODIFIER_SYMBOLS = {
    "cmd": "⌘",
    "super": "⌘",
    "ctrl": "⌃",
    "control": "⌃",
    "alt": "⌥",
    "option": "⌥",
    "shift": "⇧",
}
MARKDOWN_SUFFIXES = {".md", ".markdown"}


class RichedFooter(Footer):
    """Footer that shows app bindings and omits blocked bindings."""

    def _hide_binding(self, binding: Binding) -> bool:
        return (
            not self.app.get_key_display(binding)
            and binding.action in self.app._ghostty_app_hotkey_conflicts
        )

    def compose(self) -> ComposeResult:
        if not self._bindings_ready:
            return
        active_bindings = self.screen.active_bindings
        bindings = [
            (binding, enabled, tooltip)
            for (_, binding, enabled, tooltip) in active_bindings.values()
            if (
                binding.show
                and binding.action in DEFAULT_BINDINGS
                and not self._hide_binding(binding)
            )
        ]
        action_to_bindings: defaultdict[str, list[tuple[Binding, bool, str]]]
        action_to_bindings = defaultdict(list)
        for binding, enabled, tooltip in bindings:
            action_to_bindings[binding.action].append((binding, enabled, tooltip))

        self.styles.grid_size_columns = len(action_to_bindings)

        for group, multi_bindings_iterable in groupby(
            action_to_bindings.values(),
            lambda multi_bindings_: multi_bindings_[0][0].group,
        ):
            multi_bindings = list(multi_bindings_iterable)
            if group is not None and len(multi_bindings) > 1:
                with KeyGroup(classes="-compact" if group.compact else ""):
                    for multi_bindings in multi_bindings:
                        binding, enabled, tooltip = multi_bindings[0]
                        yield FooterKey(
                            binding.key,
                            self.app.get_key_display(binding),
                            "",
                            binding.action,
                            disabled=not enabled,
                            tooltip=tooltip or binding.description,
                            classes="-grouped",
                        ).data_bind(compact=Footer.compact)
                yield FooterLabel(group.description)
            else:
                for multi_bindings in multi_bindings:
                    binding, enabled, tooltip = multi_bindings[0]
                    yield FooterKey(
                        binding.key,
                        self.app.get_key_display(binding),
                        binding.description,
                        binding.action,
                        disabled=not enabled,
                        tooltip=tooltip,
                    ).data_bind(compact=Footer.compact)
        if self.show_command_palette and self.app.ENABLE_COMMAND_PALETTE:
            try:
                _node, binding, enabled, tooltip = active_bindings[
                    self.app.COMMAND_PALETTE_BINDING
                ]
            except KeyError:
                pass
            else:
                if not self._hide_binding(binding):
                    yield FooterKey(
                        binding.key,
                        self.app.get_key_display(binding),
                        binding.description,
                        binding.action,
                        classes="-command-palette",
                        disabled=not enabled,
                        tooltip=binding.tooltip or binding.description or tooltip,
                    )


class RichedDirectoryTree(DirectoryTree):
    """Directory tree with editor-style keyboard affordances."""

    BINDINGS = [
        *(binding for binding in DirectoryTree.BINDINGS if binding.key != "space"),
        Binding("left", "collapse_cursor", "Collapse folder", show=False),
        Binding("right", "expand_cursor", "Expand folder", show=False),
        Binding("space", "activate_cursor", "Open file or toggle folder", show=False),
        Binding("escape", "quit_check", "Quit", show=False),
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

    def action_quit_check(self) -> None:
        app = self.app
        if isinstance(app, RichedApp):
            app.action_file_tree_quit_check()


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


class RichedMarkdownViewer(MarkdownViewer):
    """Markdown preview that opens external URLs without navigating to them."""

    async def go(self, location: str | Any) -> None:
        href = str(location)
        parsed = urlparse(href)
        if parsed.scheme and (parsed.netloc or parsed.scheme not in {"", "file"}):
            self.app.open_url(href)
            return
        await super().go(location)


class RichedApp(App):
    """TUI text editor with a project file tree."""

    COMMAND_PALETTE_BINDING = "f1"

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
    #markdown-preview {
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
        self._quick_open_entries: list[QuickOpenEntry] = []
        self._quick_open_complete = False
        self._quick_open_indexing = False
        self._quick_open_limited = False
        self._quick_open_generation = 0
        self._quick_open_screen: QuickOpenScreen | None = None
        self._ghostty_app_hotkey_conflicts = ghostty_app_hotkey_conflicts()

    def _save_theme(self, theme: str) -> None:
        try:
            save_theme(theme)
        except Exception as exc:
            self.notify(f"Could not save theme: {exc}", severity="warning")

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        commands: list[SystemCommand] = []
        for command in super().get_system_commands(screen):
            if command.title == "Maximize":
                continue
            if command.title == "Keys":
                continue
            commands.append(command)
        commands.extend(
            [
                SystemCommand(
                    "Show key bindings",
                    "Open the key bindings reference",
                    self.action_show_keys_popup,
                ),
                SystemCommand(
                    "Toggle Markdown preview",
                    "Show or hide the current Markdown file preview",
                    self.action_toggle_markdown_preview,
                ),
            ]
        )
        yield from sorted(commands, key=lambda command: command.title.casefold())

    def get_key_display(self, binding: Binding) -> str:
        if binding.key_display:
            return binding.key_display

        key = app_binding_display_key(
            binding.action,
            binding.key,
            conflicted_actions=self._ghostty_app_hotkey_conflicts,
        )
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
        yield RichedFooter(show_command_palette=False)

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

    def _markdown_preview_or_none(self) -> MarkdownViewer | None:
        previews = list(self.query("#markdown-preview"))
        return previews[0] if previews else None

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

    def _is_markdown_path(self) -> bool:
        return self.path is not None and self.path.suffix.lower() in MARKDOWN_SUFFIXES

    def _exit_markdown_preview(self) -> None:
        preview = self._markdown_preview_or_none()
        if preview is not None:
            preview.remove()
        editor = self._editor_or_none()
        if editor is not None:
            editor.styles.display = "block"

    def _close_buffer(self) -> None:
        self.query_one("#editor-slot", Container).remove_children()
        self.path = None
        self.sub_title = ""
        self._saved_text = ""
        self._show_file_tree()
        self._file_tree().focus()

    def _open_path(self, path: Path) -> None:
        self._exit_markdown_preview()
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

    def action_quick_open(self) -> None:
        root = self.root.expanduser()
        screen = QuickOpenScreen(
            root,
            self._quick_open_entries,
            indexing=not self._quick_open_complete,
            limited=self._quick_open_limited,
        )
        self._quick_open_screen = screen

        def handle(selected: Path | None) -> None:
            if self._quick_open_screen is screen:
                self._quick_open_screen = None
            if selected is not None:
                self._switch_path(selected)

        self.push_screen(screen, handle)
        if not self._quick_open_complete and not self._quick_open_indexing:
            self._start_quick_open_index()

    def _start_quick_open_index(self) -> None:
        self._quick_open_indexing = True
        self._build_quick_open_index(self._quick_open_generation)

    @work(thread=True, exclusive=True, group="quick_open_index", exit_on_error=False)
    def _build_quick_open_index(self, generation: int) -> None:
        try:
            root = self.root.expanduser()
            git_result = git_quick_open_entries(root, MAX_QUICK_OPEN_INDEX_FILES)
            if git_result is not None:
                git_entries, limited = git_result
                self.call_from_thread(
                    self._replace_quick_open_entries,
                    generation,
                    git_entries,
                    True,
                    limited,
                )
                return

            worker = get_current_worker()
            batch: list[QuickOpenEntry] = []
            count = 0
            limited = False
            for entry in scan_quick_open_entries(root):
                if worker.is_cancelled:
                    return
                if count >= MAX_QUICK_OPEN_INDEX_FILES:
                    limited = True
                    break
                batch.append(entry)
                count += 1
                if len(batch) >= QUICK_OPEN_BATCH_SIZE:
                    self.call_from_thread(
                        self._append_quick_open_entries,
                        generation,
                        batch,
                        False,
                        False,
                    )
                    batch = []

            if batch:
                self.call_from_thread(
                    self._append_quick_open_entries, generation, batch, False, False
                )
            self.call_from_thread(self._finish_quick_open_index, generation, limited)
        except Exception as exc:
            self.call_from_thread(
                self._fail_quick_open_index, generation, str(exc) or type(exc).__name__
            )

    def _append_quick_open_entries(
        self,
        generation: int,
        entries: list[QuickOpenEntry],
        complete: bool,
        limited: bool,
    ) -> None:
        if generation != self._quick_open_generation:
            return
        self._quick_open_entries.extend(entries)
        self._quick_open_limited = self._quick_open_limited or limited
        screen = self._quick_open_screen
        if screen is not None and screen.is_mounted:
            screen.append_entries(entries, complete=complete, limited=limited)

    def _replace_quick_open_entries(
        self,
        generation: int,
        entries: list[QuickOpenEntry],
        complete: bool,
        limited: bool,
    ) -> None:
        if generation != self._quick_open_generation:
            return
        self._quick_open_entries = list(entries)
        self._quick_open_complete = complete
        self._quick_open_limited = limited
        self._quick_open_indexing = False
        screen = self._quick_open_screen
        if screen is not None and screen.is_mounted:
            screen.replace_entries(entries, complete=complete, limited=limited)

    def _finish_quick_open_index(self, generation: int, limited: bool) -> None:
        if generation != self._quick_open_generation:
            return
        self._quick_open_complete = True
        self._quick_open_limited = limited
        self._quick_open_indexing = False
        screen = self._quick_open_screen
        if screen is not None and screen.is_mounted:
            screen.finish_indexing(limited=limited)

    def _fail_quick_open_index(self, generation: int, message: str) -> None:
        if generation != self._quick_open_generation:
            return
        self._quick_open_complete = True
        self._quick_open_indexing = False
        screen = self._quick_open_screen
        if screen is not None and screen.is_mounted:
            screen.fail_indexing(message)

    def _invalidate_quick_open_index(self) -> None:
        self._quick_open_generation += 1
        self._quick_open_entries = []
        self._quick_open_complete = False
        self._quick_open_indexing = False
        self._quick_open_limited = False
        screen = self._quick_open_screen
        if screen is not None and screen.is_mounted:
            screen.replace_entries([], complete=False, limited=False)

    def action_toggle_command_palette(self) -> None:
        if CommandPalette.is_open(self):
            self.pop_screen()
            return
        self.action_command_palette()

    def action_show_keys_popup(self) -> None:
        self.push_screen(
            KeysHelpScreen(conflicted_actions=self._ghostty_app_hotkey_conflicts)
        )

    async def action_toggle_markdown_preview(self) -> None:
        editor = self._editor_or_none()
        if self.path is None or editor is None:
            self.notify("No file open", severity="warning")
            return
        if not self._is_markdown_path():
            self.notify(
                "Markdown preview is only available for Markdown files.",
                severity="warning",
            )
            return

        preview = self._markdown_preview_or_none()
        if preview is not None:
            self._exit_markdown_preview()
            editor.focus()
            return

        preview = RichedMarkdownViewer(
            editor.text,
            id="markdown-preview",
            show_table_of_contents=False,
            open_links=False,
        )
        editor.styles.display = "none"
        await self.query_one("#editor-slot", Container).mount(preview)
        preview.document.focus()

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
        self._invalidate_quick_open_index()
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

    def action_file_tree_quit_check(self) -> None:
        if self._is_dirty():
            self.action_quit_check()
            return

        def handle(choice: str) -> None:
            if choice == "quit":
                self.exit()

        self.push_screen(QuitConfirmationScreen(), handle)

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
            self._hide_file_tree()
            if editor is not None:
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
