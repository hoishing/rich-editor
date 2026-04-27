from __future__ import annotations

from textual.widgets import TextArea

from .keybindings import build_static_bindings

LINE_COMMENT_MARKERS = {
    "bash": "#",
    "go": "//",
    "java": "//",
    "javascript": "//",
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


class RichedTextArea(TextArea):
    """TextArea with VS Code-style line-edit shortcuts."""

    BINDINGS = build_static_bindings("editor")

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
        row, col = self.cursor_location
        if row + 1 >= self.document.line_count:
            return
        line_a = self.document.get_line(row)
        line_b = self.document.get_line(row + 1)
        self.replace(
            line_b + "\n" + line_a,
            (row, 0),
            (row + 1, len(line_b)),
            maintain_selection_offset=False,
        )
        self.move_cursor((row + 1, col))

    def action_move_line_up(self) -> None:
        row, col = self.cursor_location
        if row == 0:
            return
        line_a = self.document.get_line(row - 1)
        line_b = self.document.get_line(row)
        self.replace(
            line_b + "\n" + line_a,
            (row - 1, 0),
            (row, len(line_b)),
            maintain_selection_offset=False,
        )
        self.move_cursor((row - 1, col))

    def action_copy_line_down(self) -> None:
        row, col = self.cursor_location
        line = self.document.get_line(row)
        self.insert("\n" + line, (row, len(line)), maintain_selection_offset=False)
        self.move_cursor((row + 1, col))

    def action_copy_line_up(self) -> None:
        row, col = self.cursor_location
        line = self.document.get_line(row)
        self.insert(line + "\n", (row, 0), maintain_selection_offset=False)
        self.move_cursor((row, col))

    def action_insert_line_below(self) -> None:
        row, _col = self.cursor_location
        line = self.document.get_line(row)
        self.insert("\n", (row, len(line)), maintain_selection_offset=False)
        self.move_cursor((row + 1, 0))

    def action_insert_line_above(self) -> None:
        row, _col = self.cursor_location
        self.insert("\n", (row, 0), maintain_selection_offset=False)
        self.move_cursor((row, 0))

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

    def action_toggle_line_comment(self) -> None:
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

    def _replace_target_lines(
        self,
        start_row: int,
        end_row: int,
        lines: list[str],
    ) -> None:
        text = "\n".join(lines)
        self.replace(
            text,
            (start_row, 0),
            (end_row, len(self.document.get_line(end_row))),
            maintain_selection_offset=False,
        )
        self.move_cursor((start_row, 0))

    def _shift_target_line_indent(self, spaces: int) -> None:
        start_row, end_row, lines = self._target_lines()
        if spaces > 0:
            updated = [" " * spaces + line for line in lines]
        else:
            updated = [_outdent_line(line, -spaces) for line in lines]

        cursor_row, cursor_col = self.cursor_location
        if start_row <= cursor_row <= end_row:
            target_line = self.document.get_line(cursor_row)
            updated_cursor_line = updated[cursor_row - start_row]
            delta = len(updated_cursor_line) - len(target_line)
            target_cursor = (cursor_row, max(0, cursor_col + delta))
        else:
            target_cursor = (start_row, 0)
        self.replace(
            "\n".join(updated),
            (start_row, 0),
            (end_row, len(self.document.get_line(end_row))),
            maintain_selection_offset=False,
        )
        self.move_cursor(target_cursor)

    def _toggle_line_comment(self, marker: str) -> None:
        start_row, end_row, lines = self._target_lines()
        non_blank = [line for line in lines if line.strip()]
        if not non_blank:
            return

        should_uncomment = all(
            line.lstrip().startswith(marker)
            for line in non_blank
        )
        updated = [
            _uncomment_line(line, marker)
            if should_uncomment
            else _comment_line(line, marker)
            for line in lines
        ]
        self._replace_target_lines(start_row, end_row, updated)

    def _toggle_block_comment(self, open_marker: str, close_marker: str) -> None:
        start_row, end_row, lines = self._target_lines()
        non_blank = [line for line in lines if line.strip()]
        if not non_blank:
            return

        should_uncomment = all(
            line.lstrip().startswith(open_marker)
            and line.rstrip().endswith(close_marker)
            for line in non_blank
        )
        updated = [
            _uncomment_block_line(line, open_marker, close_marker)
            if should_uncomment
            else _comment_block_line(line, open_marker, close_marker)
            for line in lines
        ]
        self._replace_target_lines(start_row, end_row, updated)

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
