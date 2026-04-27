from __future__ import annotations

import traceback
import asyncio
from collections.abc import Awaitable, Callable

from .test_command_palette import (
    test_command_palette_button_is_hidden,
    test_command_palette_includes_show_key_bindings,
    test_command_palette_omits_maximize,
    test_cmd_shift_p_opens_command_palette,
    test_ctrl_p_does_not_open_command_palette,
    test_f1_opens_command_palette,
    test_keys_help_includes_command_palette_binding,
    test_super_shift_p_opens_command_palette_alias,
)
from .test_cli import (
    test_no_filename_opens_current_folder,
    test_version_flag_prints_current_version,
    test_version_flag_rejects_filename,
)
from .test_dirty_buffers import (
    test_close_buffer_dirty_shows_wide_modal_then_cancel,
    test_close_buffer_dirty_space_discard_enters_no_buffer_state,
    test_ctrl_w_does_not_close_buffer,
    test_file_tree_escape_clean_quit_exits,
    test_file_tree_escape_clean_shows_quit_confirmation_then_cancel,
    test_file_tree_escape_dirty_shows_unsaved_changes,
    test_ctrl_q_does_not_quit,
    test_quit_dirty_discard_keeps_file,
    test_quit_dirty_save_writes_and_exits,
    test_quit_dirty_shows_modal_then_cancel,
)
from .test_editor_shortcuts import (
    test_alt_backspace_deletes_word_left,
    test_alt_z_toggles_word_wrap,
    test_alt_shift_arrows_select_word_left_and_right,
    test_cmd_backspace_at_line_start_joins_previous_line,
    test_cmd_backspace_deletes_selection,
    test_cmd_backspace_deletes_to_line_start,
    test_cmd_b_toggles_file_tree,
    test_cmd_b_toggles_file_tree_without_open_buffer,
    test_cmd_l_repeats_expand_line_selection,
    test_cmd_l_selects_current_line_with_newline,
    test_cmd_l_selects_final_line_without_newline,
    test_cmd_slash_toggles_css_block_comments,
    test_cmd_slash_toggles_python_line_comment,
    test_cmd_slash_toggles_selected_typescript_lines,
    test_cmd_slash_unsupported_language_notifies_without_change,
    test_cmd_shift_k_deletes_current_line,
    test_cmd_shift_left_selects_to_line_start,
    test_cmd_shift_right_selects_to_line_end,
    test_cmd_shift_z_redoes_edit,
    test_cmd_x_cuts_selected_text,
    test_cmd_x_without_selection_cuts_current_line,
    test_cmd_z_undoes_edit,
    test_ctrl_shift_k_does_not_delete_current_line,
    test_copy_line_down,
    test_copy_line_up,
    test_ghostty_cmd_backspace_sequence_at_line_start_joins_previous_line,
    test_move_line_at_boundaries_is_noop,
    test_move_line_down,
    test_move_line_up,
    test_parser_order_super_shift_line_selection_aliases,
    test_super_l_selects_current_line_alias,
    test_super_b_toggles_file_tree_alias,
    test_super_b_toggles_file_tree_without_open_buffer,
    test_super_shift_k_deletes_current_line_alias,
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
from .test_footer import (
    test_footer_defaults_to_markdown_preview_fallback_outside_ghostty,
    test_footer_uses_command_palette_preferred_when_ghostty_unbound,
    test_footer_uses_command_palette_fallback_for_ghostty_conflict,
    test_footer_uses_macos_modifier_symbols_with_preferred_markdown_preview,
    test_footer_uses_markdown_preview_fallback_for_ghostty_conflict,
)
from .test_markdown_preview import (
    test_cmd_shift_v_toggles_markdown_preview,
    test_ctrl_shift_v_toggles_markdown_preview_fallback,
    test_ctrl_shift_v_warns_for_non_markdown_file,
    test_keys_help_includes_markdown_preview_binding,
    test_markdown_preview_external_link_opens_without_navigation,
    test_markdown_preview_uses_unsaved_editor_content,
    test_super_shift_v_toggles_markdown_preview_alias,
    test_switching_files_exits_markdown_preview,
)
from .test_quick_open import (
    test_quick_open_exact_hidden_filename_match_wins,
    test_quick_open_fallback_follows_symlinks,
    test_quick_open_fallback_limit_is_visible,
    test_quick_open_fallback_indexes_by_directory_level,
    test_quick_open_fallback_skips_heavy_directories,
    test_quick_open_git_index_includes_ignored_files,
    test_quick_open_git_index_limit_is_visible,
    test_quick_open_screen_opens_before_indexing_completes,
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
    ("cli: no filename opens current folder", test_no_filename_opens_current_folder),
    ("cli: version flag prints current version", test_version_flag_prints_current_version),
    ("cli: version flag rejects filename", test_version_flag_rejects_filename),
    ("command palette: button hidden", test_command_palette_button_is_hidden),
    ("command palette: omit maximize", test_command_palette_omits_maximize),
    (
        "command palette: includes show key bindings",
        test_command_palette_includes_show_key_bindings,
    ),
    (
        "command palette: keys help includes binding",
        test_keys_help_includes_command_palette_binding,
    ),
    ("command palette: F1 opens palette", test_f1_opens_command_palette),
    (
        "command palette: Cmd+Shift+P opens palette",
        test_cmd_shift_p_opens_command_palette,
    ),
    (
        "command palette: Super+Shift+P opens palette",
        test_super_shift_p_opens_command_palette_alias,
    ),
    (
        "command palette: Ctrl+P does not open palette",
        test_ctrl_p_does_not_open_command_palette,
    ),
    ("Ctrl+Q does not quit", test_ctrl_q_does_not_quit),
    ("quit dirty: modal + cancel", test_quit_dirty_shows_modal_then_cancel),
    ("quit dirty: save writes & exits", test_quit_dirty_save_writes_and_exits),
    ("quit dirty: discard keeps file", test_quit_dirty_discard_keeps_file),
    (
        "file tree Escape clean: modal + cancel",
        test_file_tree_escape_clean_shows_quit_confirmation_then_cancel,
    ),
    ("file tree Escape clean: quit exits", test_file_tree_escape_clean_quit_exits),
    (
        "file tree Escape dirty: unsaved modal",
        test_file_tree_escape_dirty_shows_unsaved_changes,
    ),
    ("close buffer: Ctrl+W does not close buffer", test_ctrl_w_does_not_close_buffer),
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
    (
        "quick open: screen opens before indexing completes",
        test_quick_open_screen_opens_before_indexing_completes,
    ),
    (
        "quick open: fallback skips heavy directories",
        test_quick_open_fallback_skips_heavy_directories,
    ),
    (
        "quick open: fallback indexes by directory level",
        test_quick_open_fallback_indexes_by_directory_level,
    ),
    (
        "quick open: fallback follows symlinks",
        test_quick_open_fallback_follows_symlinks,
    ),
    (
        "quick open: git index includes ignored files",
        test_quick_open_git_index_includes_ignored_files,
    ),
    ("quick open: git index limit is visible", test_quick_open_git_index_limit_is_visible),
    ("quick open: fallback limit is visible", test_quick_open_fallback_limit_is_visible),
    (
        "quick open: exact hidden filename match wins",
        test_quick_open_exact_hidden_filename_match_wins,
    ),
    (
        "footer: macOS modifier symbols",
        test_footer_uses_macos_modifier_symbols_with_preferred_markdown_preview,
    ),
    (
        "footer: command palette fallback for Ghostty conflict",
        test_footer_uses_command_palette_fallback_for_ghostty_conflict,
    ),
    (
        "footer: command palette preferred when Ghostty unbound",
        test_footer_uses_command_palette_preferred_when_ghostty_unbound,
    ),
    (
        "footer: markdown preview fallback for Ghostty conflict",
        test_footer_uses_markdown_preview_fallback_for_ghostty_conflict,
    ),
    (
        "footer: markdown preview fallback outside Ghostty",
        test_footer_defaults_to_markdown_preview_fallback_outside_ghostty,
    ),
    (
        "markdown preview: cmd+shift+v toggles",
        test_cmd_shift_v_toggles_markdown_preview,
    ),
    (
        "markdown preview: super+shift+v alias",
        test_super_shift_v_toggles_markdown_preview_alias,
    ),
    (
        "markdown preview: ctrl+shift+v fallback",
        test_ctrl_shift_v_toggles_markdown_preview_fallback,
    ),
    (
        "markdown preview: uses unsaved editor content",
        test_markdown_preview_uses_unsaved_editor_content,
    ),
    (
        "markdown preview: non-markdown warning",
        test_ctrl_shift_v_warns_for_non_markdown_file,
    ),
    (
        "markdown preview: switching files exits preview",
        test_switching_files_exits_markdown_preview,
    ),
    (
        "markdown preview: external link opens without navigation",
        test_markdown_preview_external_link_opens_without_navigation,
    ),
    (
        "markdown preview: keys help includes binding",
        test_keys_help_includes_markdown_preview_binding,
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
    ("editor: cmd+/ toggles Python line comment", test_cmd_slash_toggles_python_line_comment),
    (
        "editor: cmd+/ toggles selected TypeScript lines",
        test_cmd_slash_toggles_selected_typescript_lines,
    ),
    ("editor: cmd+/ toggles CSS block comments", test_cmd_slash_toggles_css_block_comments),
    (
        "editor: cmd+/ unsupported language notifies",
        test_cmd_slash_unsupported_language_notifies_without_change,
    ),
    ("editor: alt+z toggles word wrap", test_alt_z_toggles_word_wrap),
    ("app: cmd+b toggles file tree", test_cmd_b_toggles_file_tree),
    (
        "app: cmd+b toggles file tree without open buffer",
        test_cmd_b_toggles_file_tree_without_open_buffer,
    ),
    ("app: super+b toggles file tree alias", test_super_b_toggles_file_tree_alias),
    (
        "app: super+b toggles file tree without open buffer",
        test_super_b_toggles_file_tree_without_open_buffer,
    ),
    (
        "editor: undo multiline insert that removes scrollbar",
        test_undo_multiline_insert_that_removes_scrollbar,
    ),
    ("editor: alt+backspace deletes word", test_alt_backspace_deletes_word_left),
    ("editor: cmd+backspace deletes to line start", test_cmd_backspace_deletes_to_line_start),
    (
        "editor: cmd+backspace at line start joins previous line",
        test_cmd_backspace_at_line_start_joins_previous_line,
    ),
    (
        "editor: Ghostty cmd+backspace sequence at line start joins previous line",
        test_ghostty_cmd_backspace_sequence_at_line_start_joins_previous_line,
    ),
    ("editor: cmd+backspace deletes selection", test_cmd_backspace_deletes_selection),
    ("editor: cmd+z undoes edit", test_cmd_z_undoes_edit),
    ("editor: cmd+shift+z redoes edit", test_cmd_shift_z_redoes_edit),
    ("editor: cmd+x cuts selected text", test_cmd_x_cuts_selected_text),
    (
        "editor: cmd+x without selection cuts current line",
        test_cmd_x_without_selection_cuts_current_line,
    ),
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
    ("editor: cmd+shift+k deletes current line", test_cmd_shift_k_deletes_current_line),
    (
        "editor: super+shift+k deletes current line alias",
        test_super_shift_k_deletes_current_line_alias,
    ),
    (
        "editor: ctrl+shift+k does not delete current line",
        test_ctrl_shift_k_does_not_delete_current_line,
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


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
