from __future__ import annotations

import traceback
from collections.abc import Awaitable, Callable

from .test_dirty_buffers import (
    test_close_buffer_clean_enters_no_buffer_state_via_ctrl_w,
    test_close_buffer_dirty_shows_wide_modal_then_cancel,
    test_close_buffer_dirty_space_discard_enters_no_buffer_state,
    test_quit_clean_exits,
    test_quit_dirty_discard_keeps_file,
    test_quit_dirty_save_writes_and_exits,
    test_quit_dirty_shows_modal_then_cancel,
)
from .test_editor_shortcuts import (
    test_alt_backspace_deletes_word_left,
    test_alt_shift_arrows_select_word_left_and_right,
    test_cmd_l_repeats_expand_line_selection,
    test_cmd_l_selects_current_line_with_newline,
    test_cmd_l_selects_final_line_without_newline,
    test_cmd_shift_left_selects_to_line_start,
    test_cmd_shift_right_selects_to_line_end,
    test_copy_line_down,
    test_copy_line_up,
    test_move_line_at_boundaries_is_noop,
    test_move_line_down,
    test_move_line_up,
    test_parser_order_super_shift_line_selection_aliases,
    test_super_l_selects_current_line_alias,
    test_super_shift_line_selection_aliases,
    test_undo_multiline_insert_that_removes_scrollbar,
)
from .test_file_io import (
    test_open_directory_starts_with_no_buffer,
    test_open_existing_file,
    test_open_missing_file,
    test_save_writes_file,
)
from .test_file_tree import (
    test_file_tree_dirty_switch_prompts_then_discard_opens_file,
    test_file_tree_is_rooted_at_project_dir,
    test_file_tree_switch_opens_selected_file,
)
from .test_syntax import (
    test_python_highlight,
    test_tsx_highlight,
    test_typescript_highlight,
    test_unknown_extension_no_language,
)

TESTS: list[tuple[str, Callable[[], Awaitable[None]]]] = [
    ("open existing file", test_open_existing_file),
    ("open missing file", test_open_missing_file),
    ("open directory starts with no buffer", test_open_directory_starts_with_no_buffer),
    ("save writes file", test_save_writes_file),
    ("quit clean exits", test_quit_clean_exits),
    ("quit dirty: modal + cancel", test_quit_dirty_shows_modal_then_cancel),
    ("quit dirty: save writes & exits", test_quit_dirty_save_writes_and_exits),
    ("quit dirty: discard keeps file", test_quit_dirty_discard_keeps_file),
    (
        "close buffer clean enters no-buffer state via Ctrl+W",
        test_close_buffer_clean_enters_no_buffer_state_via_ctrl_w,
    ),
    (
        "close buffer dirty: wide modal + cancel",
        test_close_buffer_dirty_shows_wide_modal_then_cancel,
    ),
    (
        "close buffer dirty: Space discard enters no-buffer state",
        test_close_buffer_dirty_space_discard_enters_no_buffer_state,
    ),
    ("file tree: rooted at project dir", test_file_tree_is_rooted_at_project_dir),
    ("file tree: switch opens file", test_file_tree_switch_opens_selected_file),
    (
        "file tree: dirty switch prompts then discard",
        test_file_tree_dirty_switch_prompts_then_discard_opens_file,
    ),
    ("syntax: python", test_python_highlight),
    ("syntax: typescript", test_typescript_highlight),
    ("syntax: tsx", test_tsx_highlight),
    ("syntax: unknown extension", test_unknown_extension_no_language),
    ("editor: move line down", test_move_line_down),
    ("editor: move line up", test_move_line_up),
    ("editor: move line at boundaries no-op", test_move_line_at_boundaries_is_noop),
    ("editor: copy line down", test_copy_line_down),
    ("editor: copy line up", test_copy_line_up),
    (
        "editor: undo multiline insert that removes scrollbar",
        test_undo_multiline_insert_that_removes_scrollbar,
    ),
    ("editor: alt+backspace deletes word", test_alt_backspace_deletes_word_left),
    (
        "editor: alt+shift arrows select word",
        test_alt_shift_arrows_select_word_left_and_right,
    ),
    ("editor: cmd+l selects current line", test_cmd_l_selects_current_line_with_newline),
    ("editor: cmd+l repeats expand line selection", test_cmd_l_repeats_expand_line_selection),
    ("editor: super+l selects current line alias", test_super_l_selects_current_line_alias),
    (
        "editor: cmd+l selects final line without newline",
        test_cmd_l_selects_final_line_without_newline,
    ),
    ("editor: cmd+shift+left selects line start", test_cmd_shift_left_selects_to_line_start),
    ("editor: cmd+shift+right selects line end", test_cmd_shift_right_selects_to_line_end),
    ("editor: super+shift line selection aliases", test_super_shift_line_selection_aliases),
    (
        "editor: parser-order super+shift line selection aliases",
        test_parser_order_super_shift_line_selection_aliases,
    ),
]


async def main() -> int:
    passed = 0
    failed: list[tuple[str, str]] = []
    for name, fn in TESTS:
        try:
            await fn()
        except Exception:
            failed.append((name, traceback.format_exc()))
            print(f"FAIL  {name}")
        else:
            passed += 1
            print(f"PASS  {name}")

    print()
    print(f"{passed} passed, {len(failed)} failed, {len(TESTS)} total")
    if failed:
        print()
        for name, tb in failed:
            print(f"--- {name} " + "-" * (60 - len(name)))
            print(tb)
    return 0 if not failed else 1
