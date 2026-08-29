from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import groupby
import json
from pathlib import Path
import re
from shutil import which
import subprocess
import sys
from typing import Any, Callable
from urllib.parse import urlparse

from textual import events, work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding, BindingType
from textual.command import CommandPalette
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.worker import get_current_worker
from textual.widgets import (
    DirectoryTree,
    Footer,
    Header,
    MarkdownViewer,
    OptionList,
    Static,
    TextArea,
)
from textual.widgets._footer import FooterKey, FooterLabel, KeyGroup
from textual.widgets._header import HeaderClock, HeaderClockSpace, HeaderTitle
from textual.widgets.option_list import Option

from .editor import RichedTextArea
from .formatting import format_text
from .keybindings import (
    DEFAULT_BINDINGS,
    app_binding_display_key,
    build_static_bindings,
    display_key_with_symbols,
    ghostty_conflicted_hotkey_triggers,
    running_in_ghostty,
    running_in_wezterm,
    wezterm_conflicted_hotkey_triggers,
)
from .quick_open import (
    MAX_QUICK_OPEN_INDEX_FILES,
    QUICK_OPEN_BATCH_SIZE,
    QuickOpenEntry,
    QuickOpenIndexUpdate,
    quick_open_index_updates,
)
from .screens import (
    CreateFileScreen,
    KeysHelpScreen,
    QuickOpenScreen,
    QuitConfirmationScreen,
    RenamePathScreen,
    ReplaceScreen,
    ReplaceTerms,
    TrashPathConfirmationScreen,
    UnsavedChangesScreen,
)
from .settings import load_theme, save_theme
from .syntax import (
    PLAIN_TEXT_ID,
    active_file_type_id,
    active_file_type_label,
    apply_language,
    language_label,
    set_file_type,
    supported_file_types,
)

SIDEBAR_DEFAULT_WIDTH = 30
SIDEBAR_MIN_WIDTH = 18
SIDEBAR_MAX_WIDTH = 44
MARKDOWN_SUFFIXES = {".md", ".markdown"}
FILE_TYPE_PICKER_WIDTH = 24
FILE_TYPE_PICKER_MAX_HEIGHT = 16
PLAIN_TEXT_OPTION_ID = f"language:{PLAIN_TEXT_ID}"


@dataclass(frozen=True)
class _ReplaceContext:
    editor: TextArea
    screen: ReplaceScreen
    terms: ReplaceTerms
    pattern: re.Pattern[str]
    matches: list[re.Match[str]]


def _binding_key(binding: BindingType) -> str:
    if isinstance(binding, Binding):
        return binding.key
    return binding[0]


def _clamp_location(text: str, location: tuple[int, int]) -> tuple[int, int]:
    lines = text.split("\n")
    row, column = location
    row = max(0, min(row, len(lines) - 1))
    column = max(0, min(column, len(lines[row])))
    return row, column


class RichedFooter(Footer):
    """Footer that shows app bindings and omits blocked bindings."""

    def _hide_binding(self, binding: Binding) -> bool:
        return not self.app.get_key_display(binding)

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
        yield MarkdownPreviewButton()
        yield FileTypeButton()


class FileTypeButton(Static):
    """Footer control for the active syntax language."""

    can_focus = False

    def __init__(self) -> None:
        super().__init__("No file", id="file-type-button")
        self.tooltip = "Change file type"

    def on_mount(self) -> None:
        app = self.app
        if isinstance(app, RichedApp):
            self.update(app._current_file_type_label())

    async def on_click(self, event: events.Click) -> None:
        event.stop()
        await self.run_action("app.toggle_file_type_picker")


class MarkdownPreviewButton(Static):
    """Footer control for toggling Markdown preview."""

    can_focus = False

    def __init__(self) -> None:
        super().__init__("Preview", id="markdown-preview-button")
        self.tooltip = "Toggle Markdown preview"

    async def on_click(self, event: events.Click) -> None:
        event.stop()
        await self.run_action("app.toggle_markdown_preview")


class FileTypePicker(OptionList):
    """Language picker dismissed by Escape."""

    BINDINGS = [Binding("escape", "dismiss", show=False)]

    def action_dismiss(self) -> None:
        app = self.app
        if isinstance(app, RichedApp):
            app.close_file_type_picker(focus_editor=True)


class RefreshButton(Static):
    """Header control for refreshing the workspace."""

    can_focus = False

    def __init__(self) -> None:
        super().__init__("↻", id="refresh-button")
        self.tooltip = "Refresh"

    async def on_click(self, event: events.Click) -> None:
        event.stop()
        await self.run_action("app.refresh_workspace")


class MarkdownTocButton(Static):
    """Header control for the Markdown preview table of contents."""

    can_focus = False

    def __init__(self) -> None:
        super().__init__("☰", id="markdown-toc-button")
        self.tooltip = "Toggle table of contents"

    async def on_click(self, event: events.Click) -> None:
        event.stop()
        await self.run_action("app.toggle_markdown_toc")


class RichedHeader(Header):
    """Header with a compact refresh control on the left."""

    def compose(self) -> ComposeResult:
        yield RefreshButton()
        yield HeaderTitle()
        yield (
            HeaderClock().data_bind(Header.time_format)
            if self._show_clock
            else HeaderClockSpace()
        )
        yield MarkdownTocButton()


class RichedDirectoryTree(DirectoryTree):
    """Directory tree with editor-style keyboard affordances."""

    BINDINGS = [
        *(
            binding
            for binding in DirectoryTree.BINDINGS
            if _binding_key(binding) not in {"enter", "space"}
        ),
        *build_static_bindings("sidebar"),
        Binding("left", "collapse_cursor", "Collapse folder", show=False),
        Binding("right", "expand_cursor", "Expand folder", show=False),
        Binding("enter", "rename_cursor", "Rename", show=False),
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
            app.action_sidebar_quit_check()

    def action_rename_cursor(self) -> None:
        if not self.has_focus:
            return
        node = self.cursor_node
        if node is None or node.data is None:
            return
        app = self.app
        if isinstance(app, RichedApp):
            app.rename_sidebar_path(Path(node.data.path))

    def action_trash_selected(self) -> None:
        if not self.has_focus:
            return
        node = self.cursor_node
        if node is None or node.data is None:
            return
        app = self.app
        if isinstance(app, RichedApp):
            app.trash_sidebar_path(Path(node.data.path))

    def reveal_path(self, target: Path) -> None:
        self.run_worker(self._reveal_path(target), exclusive=True, group="reveal")

    async def _reveal_path(self, target: Path) -> None:
        root_entry = self.root.data
        if root_entry is None:
            return
        try:
            rel = target.resolve().relative_to(Path(root_entry.path).resolve())
        except (ValueError, OSError):
            return
        node = self.root
        if not node.is_expanded:
            node.expand()
        await self._add_to_load_queue(node)
        parts = rel.parts
        for index, part in enumerate(parts):
            match = next(
                (c for c in node.children if c.data is not None and c.data.path.name == part),
                None,
            )
            if match is None:
                return
            node = match
            if index < len(parts) - 1:
                if not node.is_expanded:
                    node.expand()
                await self._add_to_load_queue(node)
        self.move_cursor(node, animate=False)


class SidebarResizeHandle(Static):
    """Mouse handle for resizing the sidebar."""

    can_focus = False

    def __init__(self) -> None:
        super().__init__("", id="sidebar-resize-handle")
        self._drag_start_x: int | None = None
        self._drag_start_width: int | None = None

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button != 1 or event.screen_x is None:
            return
        tree = self.app.query_one("#sidebar", DirectoryTree)
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
            app.set_sidebar_width(self._drag_start_width + delta)
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

    BINDINGS = [
        *MarkdownViewer.BINDINGS,
        Binding("escape", "sidebar_escape", "Sidebar / quit", show=False),
    ]

    async def go(self, location: str | Any) -> None:
        href = str(location)
        parsed = urlparse(href)
        if parsed.scheme and (parsed.netloc or parsed.scheme not in {"", "file"}):
            self.app.open_url(href)
            return
        await super().go(location)

    def action_sidebar_escape(self) -> None:
        app = self.app
        if isinstance(app, RichedApp):
            app.action_sidebar_escape()


class RichedApp(App):
    """TUI text editor with a sidebar."""

    COMMAND_PALETTE_BINDING = "f1"

    CSS = """
    RichedApp {
        layers: default overlay;
    }
    #workspace {
        height: 1fr;
    }
    #sidebar {
        width: 30;
        min-width: 18;
        max-width: 44;
    }
    #sidebar-resize-handle {
        width: 1;
        min-width: 1;
        max-width: 1;
        height: 1fr;
        background: $panel;
    }
    #sidebar-resize-handle:hover,
    #sidebar-resize-handle.dragging {
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
    #refresh-button {
        dock: left;
        width: 3;
        min-width: 3;
        height: 1;
        content-align: center middle;
    }
    #refresh-button:hover {
        background: $foreground 10%;
    }
    #markdown-toc-button {
        dock: right;
        display: none;
        width: 3;
        min-width: 3;
        height: 1;
        content-align: center middle;
    }
    #markdown-toc-button:hover {
        background: $foreground 10%;
    }
    #markdown-preview-button {
        dock: right;
        width: auto;
        min-width: 10;
        height: 1;
        padding: 0 1;
        content-align: center middle;
        border-left: vkey $foreground 20%;
        background: $footer-item-background;
    }
    #markdown-preview-button:hover {
        background: $block-hover-background;
    }
    #file-type-button {
        dock: right;
        width: auto;
        min-width: 12;
        height: 1;
        padding: 0 1;
        content-align: center middle;
        border-left: vkey $foreground 20%;
        background: $footer-item-background;
    }
    #file-type-button:hover {
        background: $block-hover-background;
    }
    #file-type-picker {
        position: absolute;
        layer: overlay;
        width: 24;
        height: auto;
        max-height: 16;
        background: $panel;
        border: tall $accent;
    }
    """

    BINDINGS: list[Binding] = []

    def __init__(
        self,
        path: Path,
        root: Path | None = None,
        show_sidebar: bool = True,
        edit_mode: bool = False,
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
        self._show_sidebar_on_startup = show_sidebar
        self._open_markdown_in_edit_mode = edit_mode
        self._saved_text = ""
        self._quick_open_entries: list[QuickOpenEntry] = []
        self._quick_open_complete = False
        self._quick_open_indexing = False
        self._quick_open_limited = False
        self._quick_open_generation = 0
        self._quick_open_screen: QuickOpenScreen | None = None
        self._file_type_picker: FileTypePicker | None = None
        self._file_type_option_languages: dict[str, str | None] = {}
        self._ghostty_conflicted_hotkey_triggers = (
            ghostty_conflicted_hotkey_triggers()
        )
        self._wezterm_conflicted_hotkey_triggers = (
            wezterm_conflicted_hotkey_triggers()
        )
        self._conflicted_hotkey_triggers = (
            self._ghostty_conflicted_hotkey_triggers
            | self._wezterm_conflicted_hotkey_triggers
        )
        self._in_ghostty = running_in_ghostty()
        self._in_wezterm = running_in_wezterm()

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
                    "Create file",
                    "Create a file in the current folder",
                    self.action_create_file,
                ),
                SystemCommand(
                    "Replace",
                    "Find and replace text in the current file",
                    self.action_replace,
                ),
                SystemCommand(
                    "Toggle Markdown preview",
                    "Show or hide the current Markdown file preview",
                    self.action_toggle_markdown_preview,
                ),
            ]
        )
        selected = self._selected_sidebar_path()
        if selected is not None and not self._is_project_root_path(selected):
            commands.append(
                SystemCommand(
                    f'Move "{selected.name}" to Trash',
                    "Move the selected sidebar item to Trash",
                    lambda path=selected: self.trash_sidebar_path(path),
                )
            )
        yield from sorted(commands, key=lambda command: command.title.casefold())

    def get_key_display(self, binding: Binding) -> str:
        if binding.key_display:
            return binding.key_display
        if (
            binding.action == "toggle_markdown_preview"
            and not self._is_markdown_path()
        ):
            return ""

        key = app_binding_display_key(
            binding.action,
            binding.key,
            conflicted_triggers=self._conflicted_hotkey_triggers,
            in_ghostty=self._in_ghostty,
            in_wezterm=self._in_wezterm,
        )
        return display_key_with_symbols(key)

    def compose(self) -> ComposeResult:
        yield RichedHeader()
        with Horizontal(id="workspace"):
            yield RichedDirectoryTree(str(self.root), id="sidebar")
            yield SidebarResizeHandle()
            yield Container(id="editor-slot")
        yield RichedFooter(show_command_palette=False)

    def on_mount(self) -> None:
        self.title = "Riched"
        self.set_sidebar_width(SIDEBAR_DEFAULT_WIDTH)
        self._hide_sidebar()
        if self._show_sidebar_on_startup:
            self._show_sidebar()
            if self._initial_path is None:
                self.sub_title = ""
                self._sidebar().focus()
                return
        if self._initial_path is not None:
            self._open_path(self._initial_path)
        else:
            self.sub_title = ""

    def _editor_or_none(self) -> TextArea | None:
        editors = list(self.query("#editor"))
        return editors[0] if editors else None

    def _file_type_button_or_none(self) -> Static | None:
        buttons = list(self.query("#file-type-button"))
        return buttons[0] if buttons else None

    def _markdown_toc_button(self) -> Static:
        return self.query_one("#markdown-toc-button", Static)

    def _markdown_preview_or_none(self) -> MarkdownViewer | None:
        previews = list(self.query("#markdown-preview"))
        return previews[0] if previews else None

    def _sidebar(self) -> DirectoryTree:
        return self.query_one("#sidebar", DirectoryTree)

    def _sidebar_resize_handle(self) -> Static:
        return self.query_one("#sidebar-resize-handle", Static)

    def _current_file_type_label(self) -> str:
        editor = self._editor_or_none()
        if editor is None or self.path is None:
            return "No file"
        return active_file_type_label(editor)

    def _update_file_type_button(self) -> None:
        button = self._file_type_button_or_none()
        if button is not None:
            button.update(self._current_file_type_label())
        for footer in self.query(RichedFooter):
            footer.refresh(recompose=True)

    def _set_markdown_toc_button_visible(self, visible: bool) -> None:
        self._markdown_toc_button().styles.display = "block" if visible else "none"

    def _is_sidebar_visible(self) -> bool:
        return self._sidebar().styles.display != "none"

    def _set_sidebar_visible(self, visible: bool) -> None:
        display = "block" if visible else "none"
        self._sidebar().styles.display = display
        self._sidebar_resize_handle().styles.display = display

    def _show_sidebar(self) -> None:
        self._set_sidebar_visible(True)

    def _hide_sidebar(self) -> None:
        self._set_sidebar_visible(False)

    def set_sidebar_width(self, width: int) -> None:
        clamped_width = max(SIDEBAR_MIN_WIDTH, min(SIDEBAR_MAX_WIDTH, width))
        tree = self._sidebar()
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

    async def _enter_markdown_preview(self) -> None:
        editor = self._editor_or_none()
        if editor is None:
            return
        preview = RichedMarkdownViewer(
            editor.text,
            id="markdown-preview",
            show_table_of_contents=False,
            open_links=False,
        )
        editor.styles.display = "none"
        await self.query_one("#editor-slot", Container).mount(preview)
        self._set_markdown_toc_button_visible(True)
        preview.document.focus()

    def _exit_markdown_preview(self) -> None:
        preview = self._markdown_preview_or_none()
        if preview is not None:
            preview.remove()
        self._set_markdown_toc_button_visible(False)
        editor = self._editor_or_none()
        if editor is not None:
            editor.styles.display = "block"

    def _close_buffer(self) -> None:
        self.close_file_type_picker()
        self.query_one("#editor-slot", Container).remove_children()
        self.path = None
        self.sub_title = ""
        self._saved_text = ""
        self._show_sidebar()
        self._sidebar().focus()
        self._update_file_type_button()

    def _selected_sidebar_path(self) -> Path | None:
        tree = self._sidebar()
        node = tree.cursor_node
        if node is None or node.data is None:
            return None
        return Path(node.data.path)

    def _is_project_root_path(self, path: Path) -> bool:
        selected = path.expanduser().resolve(strict=False)
        root = self.root.expanduser().resolve(strict=False)
        return selected == root

    def _trash_path(self, path: Path) -> None:
        if sys.platform == "darwin":
            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'tell application "Finder" to delete POSIX file {json.dumps(str(path))}',
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                message = result.stderr.strip() or result.stdout.strip()
                if not message:
                    message = f"osascript exited with status {result.returncode}"
                raise RuntimeError(message)
            return

        local_script = Path(sys.executable).parent / "trash-put"
        trash_put = str(local_script) if local_script.exists() else which("trash-put")
        if trash_put is None:
            raise FileNotFoundError("trash-put is not available")
        result = subprocess.run(
            [trash_put, str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            if not message:
                message = f"trash-put exited with status {result.returncode}"
            raise RuntimeError(message)

    def trash_sidebar_path(self, path: Path) -> None:
        selected = path.expanduser().resolve(strict=False)
        if self._is_project_root_path(selected):
            self.notify("Cannot move the project root to Trash.", severity="warning")
            return
        if self.path is not None and self._is_dirty():
            current = self.path.expanduser().resolve(strict=False)
            current_inside_selected = current.is_relative_to(selected)
            if current == selected or current_inside_selected:
                self.notify(
                    "Save or discard changes before moving this item to Trash.",
                    severity="warning",
                )
                return

        source = path.expanduser()

        def handle(choice: str) -> None:
            if choice == "trash":
                self._apply_trash_sidebar_path(source)
                return
            self._sidebar().focus()

        self.push_screen(
            TrashPathConfirmationScreen(source.name, source.is_dir()),
            handle,
        )

    def _apply_trash_sidebar_path(self, path: Path) -> None:
        tree = self._sidebar()
        selected = path.expanduser().resolve(strict=False)
        try:
            self._trash_path(selected)
        except Exception as exc:
            self.notify(f"Move to Trash failed: {exc}", severity="error")
            return

        if self.path is not None:
            current = self.path.expanduser().resolve(strict=False)
            current_inside_selected = current.is_relative_to(selected)
            if current == selected or current_inside_selected:
                self._close_buffer()
        tree.reload()
        self._invalidate_quick_open_index()
        self.notify(f"Moved {selected.name} to Trash")

    def rename_sidebar_path(self, path: Path) -> None:
        selected = path.expanduser().resolve(strict=False)
        root = self.root.expanduser().resolve(strict=False)
        if selected == root:
            self.notify("Cannot rename the project root.", severity="warning")
            self._sidebar().focus()
            return

        source = path.expanduser()

        def validate(new_name: str) -> str | None:
            return self._validate_sidebar_rename(source, new_name)

        def handle(new_name: str | None) -> None:
            if new_name is None:
                self._sidebar().focus()
                return
            self._apply_sidebar_rename(source, new_name)

        self.push_screen(RenamePathScreen(source.name, validate), handle)

    def _validate_sidebar_rename(self, source: Path, new_name: str) -> str | None:
        if not new_name.strip():
            return "Name cannot be empty."
        if new_name in {".", ".."}:
            return "Name cannot be . or ..."
        if "/" in new_name:
            return "Name cannot contain /."
        if new_name == source.name:
            return "Name is unchanged."

        destination = source.with_name(new_name)
        if not destination.exists():
            return None
        try:
            if source.samefile(destination):
                return None
        except OSError:
            pass
        return "An item with that name already exists."

    def _apply_sidebar_rename(self, source: Path, new_name: str) -> None:
        old_path = source.expanduser().resolve(strict=False)
        destination = source.with_name(new_name).expanduser()
        new_path = destination.resolve(strict=False)
        open_display_path = self.path.expanduser() if self.path else None
        old_open_path = (
            open_display_path.resolve(strict=False)
            if open_display_path is not None
            else None
        )

        try:
            source.rename(destination)
        except Exception as exc:
            self.notify(f"Rename failed: {exc}", severity="error")
            self._sidebar().focus()
            return

        if old_open_path is not None:
            try:
                relative_open_path = old_open_path.relative_to(old_path)
            except ValueError:
                relative_open_path = None
            if relative_open_path is not None:
                assert open_display_path is not None
                self.path = self._open_path_after_sidebar_rename(
                    open_display_path,
                    old_path,
                    new_name,
                    new_path / relative_open_path,
                )
                self.sub_title = str(self.path)
                editor = self._editor_or_none()
                if editor is not None:
                    try:
                        apply_language(editor, self.path)
                    except Exception as exc:
                        self.notify(
                            f"Syntax highlight off: {exc}",
                            severity="warning",
                        )
                    self._update_file_type_button()

        self._sidebar().reload()
        self._invalidate_quick_open_index()
        self._sidebar().focus()
        self.notify(f"Renamed {old_path.name} to {new_path.name}")

    def _open_path_after_sidebar_rename(
        self,
        open_path: Path,
        old_path: Path,
        new_name: str,
        fallback: Path,
    ) -> Path:
        open_path = open_path.expanduser()
        for ancestor in (open_path, *open_path.parents):
            if ancestor.expanduser().resolve(strict=False) != old_path:
                continue
            return ancestor.with_name(new_name) / open_path.relative_to(ancestor)
        return fallback

    def _open_path(self, path: Path) -> None:
        self.close_file_type_picker()
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
            apply_language(editor, self.path)
        except Exception as exc:
            self.notify(f"Syntax highlight off: {exc}", severity="warning")
        self._update_file_type_button()
        if (
            not self._open_markdown_in_edit_mode
            and self._is_markdown_path()
            and content.strip()
        ):
            self.call_later(self._enter_markdown_preview)
        else:
            editor.focus()

    def _is_dirty(self) -> bool:
        editor = self._editor_or_none()
        return self.path is not None and editor is not None and editor.text != self._saved_text

    def _after_saved_or_discarded(
        self,
        on_clean: Callable[[], None],
    ) -> None:
        if not self._is_dirty():
            on_clean()
            return

        def handle(choice: str) -> None:
            if choice == "save":
                self.action_save()
                if not self._is_dirty():
                    on_clean()
            elif choice == "discard":
                on_clean()

        self.push_screen(UnsavedChangesScreen(), handle)

    def _refresh_workspace_clean(self) -> None:
        self._sidebar().reload()
        self._invalidate_quick_open_index()
        if self.path is None:
            self._show_sidebar()
            self._sidebar().focus()
            self.notify("Refreshed")
            return

        path = self.path.expanduser()
        if not path.exists():
            self._close_buffer()
            self.notify(f"Closed missing file {path}", severity="warning")
            return

        self._open_path(path)
        self.notify("Refreshed")

    def action_refresh_workspace(self) -> None:
        self._after_saved_or_discarded(self._refresh_workspace_clean)

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
        self._after_saved_or_discarded(lambda: self._open_path(selected))

    def _create_file_base(self) -> Path:
        tree = self._sidebar()
        node = tree.cursor_node
        root = self.root.expanduser().resolve(strict=False)
        if (
            node is not None
            and node.data is not None
            and node.allow_expand
            and (
                tree.has_focus
                or Path(node.data.path).expanduser().resolve(strict=False) != root
            )
        ):
            return Path(node.data.path).expanduser()
        if self.path is not None:
            return self.path.expanduser().parent
        return self.root.expanduser()

    def _create_file_target(self, name: str, base: Path) -> Path | None:
        raw_name = name.strip()
        if not raw_name:
            self.notify("Enter a file name.", severity="warning")
            return None
        if "\0" in raw_name:
            self.notify("File name cannot contain null bytes.", severity="warning")
            return None
        if raw_name.endswith(("/", "\\")):
            self.notify("Enter a file path, not a folder.", severity="warning")
            return None

        relative = Path(raw_name)
        if relative.is_absolute() or ".." in relative.parts:
            self.notify(
                "File name must stay inside the current folder.", severity="warning"
            )
            return None

        resolved_base = base.resolve(strict=False)
        target = (resolved_base / relative).resolve(strict=False)
        if target == resolved_base or not target.is_relative_to(resolved_base):
            self.notify(
                "File name must stay inside the current folder.", severity="warning"
            )
            return None
        return target

    def _create_or_open_file(self, target: Path) -> None:
        existed = target.exists()
        if existed and target.is_dir():
            self.notify(f"Cannot open folder {target}", severity="warning")
            return
        if not existed:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("")
            except Exception as exc:
                self.notify(f"Create file failed: {exc}", severity="error")
                return
        self._sidebar().reload()
        self._invalidate_quick_open_index()
        self._open_path(target)
        if existed:
            self.notify(f"Opened existing file {target}")
        else:
            self.notify(f"Created {target}")

    def action_create_file(self) -> None:
        base = self._create_file_base()

        def handle(name: str | None) -> None:
            if name is None:
                return
            target = self._create_file_target(name, base)
            if target is None:
                return
            self._after_saved_or_discarded(lambda: self._create_or_open_file(target))

        self.push_screen(CreateFileScreen(), handle)

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
            worker = get_current_worker()
            for update in quick_open_index_updates(
                root,
                limit=MAX_QUICK_OPEN_INDEX_FILES,
                batch_size=QUICK_OPEN_BATCH_SIZE,
            ):
                if worker.is_cancelled:
                    return
                self.call_from_thread(
                    self._apply_quick_open_update,
                    generation,
                    update,
                )
        except Exception as exc:
            self.call_from_thread(
                self._fail_quick_open_index, generation, str(exc) or type(exc).__name__
            )

    def _apply_quick_open_update(
        self,
        generation: int,
        update: QuickOpenIndexUpdate,
    ) -> None:
        if update.error is not None:
            self._fail_quick_open_index(generation, update.error)
        elif update.replace:
            self._replace_quick_open_entries(
                generation,
                update.entries,
                update.complete,
                update.limited,
            )
        elif update.complete and not update.entries:
            self._finish_quick_open_index(generation, update.limited)
        else:
            self._append_quick_open_entries(
                generation,
                update.entries,
                update.complete,
                update.limited,
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

    def _file_type_option_id(self, language: str | None) -> str:
        if language is None:
            return PLAIN_TEXT_OPTION_ID
        return f"language:{language}"

    def _position_file_type_picker(self, picker: FileTypePicker | None = None) -> None:
        picker = picker or self._file_type_picker
        if picker is None or not picker.is_mounted:
            return
        width = min(FILE_TYPE_PICKER_WIDTH, max(1, self.size.width))
        height = min(
            FILE_TYPE_PICKER_MAX_HEIGHT,
            picker.option_count + 2,
            max(1, self.size.height - 1),
        )
        picker.styles.width = width
        picker.styles.height = height
        picker.styles.offset = (
            max(0, self.size.width - width),
            max(0, self.size.height - height - 1),
        )

    async def action_toggle_file_type_picker(self) -> None:
        if self._file_type_picker is not None:
            self.close_file_type_picker(focus_editor=True)
            return

        editor = self._editor_or_none()
        if editor is None or self.path is None:
            self.notify("No file open", severity="warning")
            return

        options = [Option(language_label(None), id=PLAIN_TEXT_OPTION_ID)]
        option_ids = [PLAIN_TEXT_OPTION_ID]
        self._file_type_option_languages = {PLAIN_TEXT_OPTION_ID: None}
        for file_type in supported_file_types(editor):
            option_id = self._file_type_option_id(file_type.id)
            self._file_type_option_languages[option_id] = file_type.id
            option_ids.append(option_id)
            options.append(Option(file_type.label, id=option_id))

        picker = FileTypePicker(*options, id="file-type-picker")
        self._file_type_picker = picker
        await self.mount(picker)
        current_id = self._file_type_option_id(active_file_type_id(editor))
        picker.highlighted = (
            option_ids.index(current_id) if current_id in option_ids else 0
        )
        self._position_file_type_picker(picker)
        picker.focus()

    def close_file_type_picker(self, *, focus_editor: bool = False) -> None:
        picker = self._file_type_picker
        self._file_type_picker = None
        self._file_type_option_languages.clear()
        if picker is not None and picker.is_mounted:
            picker.remove()
        if focus_editor:
            editor = self._editor_or_none()
            if editor is not None:
                editor.focus()

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        if event.option_list.id != "file-type-picker":
            return
        event.stop()
        if event.option_id not in self._file_type_option_languages:
            return
        editor = self._editor_or_none()
        if editor is None:
            self.close_file_type_picker()
            return
        try:
            set_file_type(editor, self._file_type_option_languages[event.option_id])
        except Exception as exc:
            self.notify(f"Syntax highlight off: {exc}", severity="warning")
            return
        self._update_file_type_button()
        self.close_file_type_picker(focus_editor=True)

    def on_resize(self, event: events.Resize) -> None:
        self._position_file_type_picker()

    def action_toggle_command_palette(self) -> None:
        if CommandPalette.is_open(self):
            self.pop_screen()
            return
        self.action_command_palette()

    def action_show_keys_popup(self) -> None:
        self.push_screen(
            KeysHelpScreen(
                conflicted_triggers=self._conflicted_hotkey_triggers
            )
        )

    def action_replace(self) -> None:
        editor = self._editor_or_none()
        if self.path is None or editor is None:
            self.notify("No file open", severity="warning")
            return
        if self._markdown_preview_or_none() is not None:
            self._exit_markdown_preview()
        self.push_screen(ReplaceScreen())

    def action_replace_next(self) -> None:
        context = self._replace_context()
        if context is None:
            return
        self._select_replace_match(context, self._next_replace_match_index(context))

    def action_replace_previous(self) -> None:
        context = self._replace_context()
        if context is None:
            return
        self._select_replace_match(context, self._previous_replace_match_index(context))

    def action_replace_current(self) -> None:
        context = self._replace_context()
        if context is None:
            return
        index = self._selected_replace_match_index(context)
        if index is None:
            self._select_replace_match(
                context,
                self._next_replace_match_index(context),
            )
            return

        match = context.matches[index]
        replacement = self._replacement_for_match(context.terms, match, context.screen)
        if replacement is None:
            return
        start = context.editor.document.get_location_from_index(match.start())
        end = context.editor.document.get_location_from_index(match.end())
        context.editor.replace(
            replacement,
            start,
            end,
            maintain_selection_offset=False,
        )
        next_offset = match.start() + len(replacement)
        context.editor.move_cursor(
            context.editor.document.get_location_from_index(next_offset),
            center=True,
        )

        next_context = self._replace_context(require_match=False)
        if next_context is None:
            return
        if not next_context.matches:
            context.screen.set_status("Replaced 1 match. No more matches.")
            return
        next_index = self._first_match_at_or_after(next_context.matches, next_offset)
        self._select_replace_match(next_context, next_index)

    def action_replace_all(self) -> None:
        context = self._replace_context()
        if context is None:
            return
        if context.terms.regex:
            try:
                new_text, count = context.pattern.subn(
                    context.terms.replace,
                    context.editor.text,
                )
            except re.error as exc:
                context.screen.set_status(f"Invalid replacement: {exc}", error=True)
                return
        else:
            count = len(context.matches)
            new_text = context.editor.text.replace(
                context.terms.find,
                context.terms.replace,
            )
        context.editor.replace(
            new_text,
            (0, 0),
            context.editor.document.end,
            maintain_selection_offset=False,
        )
        context.editor.move_cursor((0, 0), center=True)
        context.screen.set_status(f"Replaced {count} matches.")

    def _replace_context(self, *, require_match: bool = True) -> _ReplaceContext | None:
        screen = self.screen if isinstance(self.screen, ReplaceScreen) else None
        editor = self._editor_or_none()
        if screen is None or editor is None:
            return None
        terms = screen.terms
        if not terms.find:
            screen.set_status("Enter a find term.", error=True)
            return None
        try:
            pattern = re.compile(terms.find if terms.regex else re.escape(terms.find))
        except re.error as exc:
            screen.set_status(f"Invalid regex: {exc}", error=True)
            return None
        matches = list(pattern.finditer(editor.text))
        if any(match.start() == match.end() for match in matches):
            screen.set_status(
                "Find pattern must match at least one character.",
                error=True,
            )
            return None
        if require_match and not matches:
            screen.set_status("No matches.", error=True)
            return None
        return _ReplaceContext(editor, screen, terms, pattern, matches)

    def _replacement_for_match(
        self,
        terms: ReplaceTerms,
        match: re.Match[str],
        screen: ReplaceScreen,
    ) -> str | None:
        if not terms.regex:
            return terms.replace
        try:
            return match.expand(terms.replace)
        except re.error as exc:
            screen.set_status(f"Invalid replacement: {exc}", error=True)
            return None

    def _selected_replace_match_index(self, context: _ReplaceContext) -> int | None:
        selection = context.editor.selection
        if selection.is_empty:
            return None
        start, end = sorted((selection.start, selection.end))
        start_offset = context.editor.document.get_index_from_location(start)
        end_offset = context.editor.document.get_index_from_location(end)
        for index, match in enumerate(context.matches):
            if match.start() == start_offset and match.end() == end_offset:
                return index
        return None

    def _next_replace_match_index(self, context: _ReplaceContext) -> int:
        current = self._selected_replace_match_index(context)
        if current is not None:
            anchor = context.matches[current].end()
        else:
            anchor = context.editor.document.get_index_from_location(
                context.editor.cursor_location
            )
        return self._first_match_at_or_after(context.matches, anchor)

    def _previous_replace_match_index(self, context: _ReplaceContext) -> int:
        current = self._selected_replace_match_index(context)
        if current is not None:
            anchor = context.matches[current].start()
        else:
            anchor = context.editor.document.get_index_from_location(
                context.editor.cursor_location
            )
        for index in range(len(context.matches) - 1, -1, -1):
            if context.matches[index].end() <= anchor:
                return index
        return len(context.matches) - 1

    def _first_match_at_or_after(
        self,
        matches: list[re.Match[str]],
        offset: int,
    ) -> int:
        for index, match in enumerate(matches):
            if match.start() >= offset:
                return index
        return 0

    def _select_replace_match(self, context: _ReplaceContext, index: int) -> None:
        match = context.matches[index]
        start = context.editor.document.get_location_from_index(match.start())
        end = context.editor.document.get_location_from_index(match.end())
        context.editor.selection = type(context.editor.selection)(start, end)
        context.editor.scroll_cursor_visible(center=True)
        context.screen.set_status(f"Match {index + 1} of {len(context.matches)}.")

    def action_toggle_markdown_toc(self) -> None:
        preview = self._markdown_preview_or_none()
        if preview is None:
            return
        preview.show_table_of_contents = not preview.show_table_of_contents

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

        await self._enter_markdown_preview()

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

    def action_format_document(self) -> None:
        if self.path is None:
            self.notify("No file open", severity="warning")
            return
        editor = self._editor_or_none()
        if editor is None:
            self.notify("No file open", severity="warning")
            return

        result = format_text(self.path, editor.text)
        if result.missing_tool is not None:
            detail = (
                "Install it and ensure Prettier can load it."
                if result.missing_tool.startswith("@")
                else "Install it and ensure it is on PATH."
            )
            self.notify(
                f"`{result.missing_tool}` is required for formatting. {detail}",
                severity="warning",
            )
            return
        if result.unsupported:
            self.notify(
                "Formatting is not supported for this file type.",
                severity="warning",
            )
            return
        if result.error is not None:
            self.notify(result.error, severity="error")
            return
        if result.text is None or result.text == editor.text:
            self.notify("Already formatted")
            return

        cursor_location = editor.cursor_location
        selection = editor.selection
        last_row = editor.document.line_count - 1
        last_location = (last_row, len(editor.document.get_line(last_row)))
        editor.replace(
            result.text,
            (0, 0),
            last_location,
            maintain_selection_offset=False,
        )
        if selection.is_empty:
            editor.move_cursor(_clamp_location(result.text, cursor_location))
        else:
            editor.selection = type(selection)(
                _clamp_location(result.text, selection.start),
                _clamp_location(result.text, selection.end),
            )
        _ = editor.focus()
        self.notify(f"Formatted {self.path}")

    def action_quit_check(self) -> None:
        self._after_saved_or_discarded(self.exit)

    def action_sidebar_quit_check(self) -> None:
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
        self._after_saved_or_discarded(self._close_buffer)

    def action_toggle_sidebar(self) -> None:
        editor = self._editor_or_none()
        if self._is_sidebar_visible():
            self._hide_sidebar()
            if editor is not None:
                editor.focus()
            return
        self._show_sidebar()

    def action_toggle_sidebar_focus(self) -> None:
        tree = self._sidebar()
        if not self._is_sidebar_visible():
            self._show_sidebar()
            tree.focus()
            return
        editor = self._editor_or_none()
        if tree.has_focus:
            if editor is not None:
                editor.focus()
            return
        tree.focus()

    def action_sidebar_escape(self) -> None:
        if not self._is_sidebar_visible():
            self.action_sidebar_quit_check()
            return
        tree = self._sidebar()
        tree.focus()
        if isinstance(tree, RichedDirectoryTree) and self.path is not None:
            tree.reveal_path(self.path)
