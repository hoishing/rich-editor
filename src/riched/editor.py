from __future__ import annotations

from textual.widgets import TextArea

from .keybindings import build_static_bindings


class RichedTextArea(TextArea):
    """TextArea with VS Code-style line-edit shortcuts."""

    BINDINGS = build_static_bindings("editor")

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
