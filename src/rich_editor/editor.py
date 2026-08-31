from __future__ import annotations

from collections.abc import Callable
import re
from typing import Protocol, cast

from textual import events
from textual.widgets import TextArea

from .keybindings import build_static_bindings
from .syntax import active_file_type_id

LINE_COMMENT_MARKERS = {
    "bash": "#",
    "dockerfile": "#",
    "go": "//",
    "java": "//",
    "javascript": "//",
    "makefile": "#",
    "python": "#",
    "rust": "//",
    "toml": "#",
    "tsx": "//",
    "typescript": "//",
    "yaml": "#",
}
BLOCK_COMMENT_MARKERS = {
    "css": ("/*", "*/"),
    "html": ("<!--", "-->"),
    "markdown": ("<!--", "-->"),
    "xml": ("<!--", "-->"),
}
FILE_TYPE_LINE_COMMENT_MARKERS = {
    "environment": "#",
    "dockerfile": "#",
    "ini": ";",
    "jsonc": "//",
    "makefile": "#",
}
LOG_HIGHLIGHT_PATTERNS = (
    (re.compile(r"\b(?:TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b"), "keyword"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ][0-9:.+-]+Z?\b"), "number"),
    (re.compile(r"\bhttps?://[^\s]+"), "string.special"),
    (re.compile(r"(?<!\w)(?:/[\w.\-]+)+"), "string"),
    (re.compile(r"[{}[\]:,]"), "punctuation.delimiter"),
)


class _FormattingApp(Protocol):
    def action_format_document(self) -> None: ...


class RichedTextArea(TextArea):
    """TextArea with VS Code-style line-edit shortcuts."""

    ALLOW_SELECT = False
    BINDINGS = build_static_bindings("editor")

    def _end_mouse_selection(self) -> None:
        was_selecting = self._selecting
        super()._end_mouse_selection()
        if was_selecting and self.selected_text:
            self.app.copy_to_clipboard(self.selected_text)

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            from .app import RichedApp

            app = self.app
            if isinstance(app, RichedApp):
                app.action_sidebar_escape()
                event.stop()
                event.prevent_default()
                return
        await super()._on_key(event)  # type: ignore[misc]

    def _clamp_location(self, location: tuple[int, int]) -> tuple[int, int]:
        row, column = location
        row = max(0, min(row, self.document.line_count - 1))
        column = max(0, min(column, len(self.document.get_line(row))))
        return row, column

    def _clamp_selection(self) -> None:
        start, end = self.selection
        clamped_start = self._clamp_location(start)
        clamped_end = self._clamp_location(end)
        if (clamped_start, clamped_end) != (start, end):
            self.selection = type(self.selection)(clamped_start, clamped_end)

    def _refresh_size(self) -> None:
        self._clamp_selection()
        super()._refresh_size()

    def _line_selection_end(self, row: int) -> tuple[int, int]:
        if row + 1 < self.document.line_count:
            return (row + 1, 0)
        return (row, len(self.document.get_line(row)))

    def _has_whole_line_selection(self) -> bool:
        start, end = self.selection
        if start > end:
            return False
        if start[1] != 0:
            return False
        if end[1] == 0 and end[0] > start[0]:
            return True
        last_row = self.document.line_count - 1
        return end[0] == last_row and end[1] == len(self.document.get_line(last_row))

    def action_select_line(self) -> None:
        start, end = self.selection
        if self._has_whole_line_selection():
            selection_start = start
            row = min(end[0], self.document.line_count - 1)
        else:
            row, _column = self.cursor_location
            selection_start = (row, 0)

        selection_end = self._line_selection_end(row)
        self.selection = type(self.selection)(selection_start, selection_end)

    def action_move_line_down(self) -> None:
        self._move_line(1)

    def action_move_line_up(self) -> None:
        self._move_line(-1)

    def _move_line(self, direction: int) -> None:
        row, col = self.cursor_location
        other_row = row + direction
        if other_row < 0 or other_row >= self.document.line_count:
            return
        top_row = min(row, other_row)
        bottom_row = max(row, other_row)
        top_line = self.document.get_line(top_row)
        bottom_line = self.document.get_line(bottom_row)
        self.replace(
            bottom_line + "\n" + top_line,
            (top_row, 0),
            (bottom_row, len(bottom_line)),
            maintain_selection_offset=False,
        )
        self.move_cursor((other_row, col))

    def action_copy_line_down(self) -> None:
        self._copy_line(1)

    def action_copy_line_up(self) -> None:
        self._copy_line(-1)

    def _copy_line(self, direction: int) -> None:
        row, col = self.cursor_location
        line = self.document.get_line(row)
        if direction > 0:
            self.insert("\n" + line, (row, len(line)), maintain_selection_offset=False)
            self.move_cursor((row + 1, col))
        else:
            self.insert(line + "\n", (row, 0), maintain_selection_offset=False)
            self.move_cursor((row, col))

    def action_indent_line(self) -> None:
        self._shift_target_line_indent(2)

    def action_outdent_line(self) -> None:
        self._shift_target_line_indent(-2)

    def action_delete_to_start_of_line_or_delete_left(self) -> None:
        if not self.selection.is_empty or self.cursor_location[1] == 0:
            self.action_delete_left()
            return
        self.action_delete_to_start_of_line()

    def action_toggle_word_wrap(self) -> None:
        self.soft_wrap = not self.soft_wrap

    def action_format_document(self) -> None:
        cast(_FormattingApp, cast(object, self.app)).action_format_document()

    def action_toggle_line_comment(self) -> None:
        file_type_id = active_file_type_id(self)
        if file_type_id in FILE_TYPE_LINE_COMMENT_MARKERS:
            self._toggle_line_comment(FILE_TYPE_LINE_COMMENT_MARKERS[file_type_id])
            return
        language = self.language
        if language in LINE_COMMENT_MARKERS:
            self._toggle_line_comment(LINE_COMMENT_MARKERS[language])
            return
        if language in BLOCK_COMMENT_MARKERS:
            self._toggle_block_comment(*BLOCK_COMMENT_MARKERS[language])
            return
        self.app.notify(
            "Line comments are not supported for this file type.",
            severity="warning",
        )

    def _build_highlight_map(self) -> None:
        super()._build_highlight_map()
        if active_file_type_id(self) == "log":
            self._build_log_highlight_map()

    def _build_log_highlight_map(self) -> None:
        highlights = self._highlights  # type: ignore[attr-defined]
        for row in range(self.document.line_count):
            line = self.document.get_line(row)
            for pattern, highlight_name in LOG_HIGHLIGHT_PATTERNS:
                for match in pattern.finditer(line):
                    start, end = match.span()
                    highlights[row].append(
                        (
                            _utf8_column(line, start),
                            _utf8_column(line, end),
                            highlight_name,
                        )
                    )

    def _selected_row_range(self) -> tuple[int, int]:
        if self.selection.is_empty:
            row, _column = self.cursor_location
            return row, row

        start, end = sorted(self.selection)
        start_row = start[0]
        end_row = end[0]
        if end[1] == 0 and end_row > start_row:
            end_row -= 1
        return start_row, end_row

    def _target_lines(self) -> tuple[int, int, list[str]]:
        start_row, end_row = self._selected_row_range()
        lines = [
            self.document.get_line(row)
            for row in range(start_row, end_row + 1)
        ]
        return start_row, end_row, lines

    def _shift_target_line_indent(self, spaces: int) -> None:
        start_row, end_row, lines = self._target_lines()
        if spaces > 0:
            updated = [" " * spaces + line for line in lines]
        else:
            updated = [_outdent_line(line, -spaces) for line in lines]
        deltas = [
            len(updated_line) - len(line)
            for line, updated_line in zip(lines, updated, strict=True)
        ]

        cursor_row, cursor_col = self.cursor_location
        if start_row <= cursor_row <= end_row:
            delta = deltas[cursor_row - start_row]
            target_cursor = (cursor_row, max(0, cursor_col + delta))
        else:
            target_cursor = (start_row, 0)
        original_selection = self.selection
        had_selection = not original_selection.is_empty
        self.replace(
            "\n".join(updated),
            (start_row, 0),
            (end_row, len(self.document.get_line(end_row))),
            maintain_selection_offset=False,
        )
        if not had_selection:
            self.move_cursor(target_cursor)
            return

        def shift_selection_endpoint(location: tuple[int, int]) -> tuple[int, int]:
            row, column = location
            if column == 0:
                return location
            if start_row <= row <= end_row:
                return row, max(0, column + deltas[row - start_row])
            return location

        self.selection = type(self.selection)(
            shift_selection_endpoint(original_selection.start),
            shift_selection_endpoint(original_selection.end),
        )

    def _toggle_line_comment(self, marker: str) -> None:
        self._toggle_target_lines(
            lambda line: line.lstrip().startswith(marker),
            lambda line: _comment_line(line, marker),
            lambda line: _uncomment_line(line, marker),
            lambda line, column: _comment_line_column(line, marker, column),
            lambda line, column: _uncomment_line_column(line, marker, column),
        )

    def _toggle_block_comment(self, open_marker: str, close_marker: str) -> None:
        self._toggle_target_lines(
            lambda line: (
                line.lstrip().startswith(open_marker)
                and line.rstrip().endswith(close_marker)
            ),
            lambda line: _comment_block_line(line, open_marker, close_marker),
            lambda line: _uncomment_block_line(line, open_marker, close_marker),
            lambda line, column: _comment_block_line_column(
                line,
                open_marker,
                column,
            ),
            lambda line, column: _uncomment_block_line_column(
                line,
                open_marker,
                close_marker,
                column,
            ),
        )

    def _toggle_target_lines(
        self,
        is_commented: Callable[[str], bool],
        comment: Callable[[str], str],
        uncomment: Callable[[str], str],
        comment_column: Callable[[str, int], int],
        uncomment_column: Callable[[str, int], int],
    ) -> None:
        start_row, end_row, lines = self._target_lines()
        non_blank = [line for line in lines if line.strip()]
        if not non_blank:
            return

        should_uncomment = all(is_commented(line) for line in non_blank)
        shift_column = uncomment_column if should_uncomment else comment_column
        updated = [
            uncomment(line) if should_uncomment else comment(line)
            for line in lines
        ]
        original_cursor = self.cursor_location
        original_selection = self.selection
        had_selection = not original_selection.is_empty
        self.replace(
            "\n".join(updated),
            (start_row, 0),
            (end_row, len(self.document.get_line(end_row))),
            maintain_selection_offset=False,
        )

        def shift_location(location: tuple[int, int]) -> tuple[int, int]:
            row, column = location
            if start_row <= row <= end_row:
                column = shift_column(lines[row - start_row], column)
            return self._clamp_location((row, column))

        if not had_selection:
            self.move_cursor(shift_location(original_cursor))
            return

        self.selection = type(self.selection)(
            shift_location(original_selection.start),
            shift_location(original_selection.end),
        )

    def action_ignore(self) -> None:
        pass


def _leading_spaces(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _outdent_line(line: str, spaces: int) -> str:
    leading_spaces = len(line) - len(line.lstrip(" "))
    return line[min(spaces, leading_spaces):]


def _comment_line(line: str, marker: str) -> str:
    if not line.strip():
        return line
    indent = _leading_spaces(line)
    return f"{indent}{marker} {line[len(indent):]}"


def _uncomment_line(line: str, marker: str) -> str:
    if not line.strip():
        return line
    indent = _leading_spaces(line)
    rest = line[len(indent):]
    if not rest.startswith(marker):
        return line
    rest = rest[len(marker):]
    if rest.startswith(" "):
        rest = rest[1:]
    return f"{indent}{rest}"


def _comment_line_column(line: str, marker: str, column: int) -> int:
    return _insert_prefix_column(line, f"{marker} ", column)


def _uncomment_line_column(line: str, marker: str, column: int) -> int:
    if not line.strip():
        return column
    indent = _leading_spaces(line)
    rest = line[len(indent):]
    if not rest.startswith(marker):
        return column
    removed = len(marker)
    if rest[removed:].startswith(" "):
        removed += 1
    return _remove_prefix_column(len(indent), removed, column)


def _comment_block_line(line: str, open_marker: str, close_marker: str) -> str:
    if not line.strip():
        return line
    indent = _leading_spaces(line)
    return f"{indent}{open_marker} {line[len(indent):]} {close_marker}"


def _uncomment_block_line(line: str, open_marker: str, close_marker: str) -> str:
    if not line.strip():
        return line
    indent = _leading_spaces(line)
    rest = line[len(indent):].strip()
    if not rest.startswith(open_marker) or not rest.endswith(close_marker):
        return line
    rest = rest[len(open_marker): -len(close_marker)].strip()
    return f"{indent}{rest}"


def _comment_block_line_column(line: str, open_marker: str, column: int) -> int:
    return _insert_prefix_column(line, f"{open_marker} ", column)


def _uncomment_block_line_column(
    line: str,
    open_marker: str,
    close_marker: str,
    column: int,
) -> int:
    if not line.strip():
        return column
    indent = _leading_spaces(line)
    indent_len = len(indent)
    rest = line[indent_len:]
    if not rest.startswith(open_marker) or not rest.rstrip().endswith(close_marker):
        return column

    content_start = indent_len + len(open_marker)
    while content_start < len(line) and line[content_start].isspace():
        content_start += 1

    content_end = len(line.rstrip()) - len(close_marker)
    while content_end > content_start and line[content_end - 1].isspace():
        content_end -= 1

    if column < indent_len:
        return column
    if column < content_start:
        return indent_len
    if column <= content_end:
        return indent_len + column - content_start
    return indent_len + content_end - content_start


def _insert_prefix_column(line: str, prefix: str, column: int) -> int:
    if not line.strip():
        return column
    indent_len = len(_leading_spaces(line))
    if column < indent_len:
        return column
    return column + len(prefix)


def _remove_prefix_column(indent_len: int, removed: int, column: int) -> int:
    if column < indent_len:
        return column
    if column < indent_len + removed:
        return indent_len
    return column - removed


def _utf8_column(text: str, column: int) -> int:
    return len(text[:column].encode())
