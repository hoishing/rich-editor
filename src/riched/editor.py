from __future__ import annotations

from textual.widgets import TextArea

from .keybindings import build_static_bindings


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
