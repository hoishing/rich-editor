from __future__ import annotations

from textual.widgets import DirectoryTree, TextArea

from .helpers import _fresh_env, _make_app

# -------------------------------------------------- editor line shortcuts --


async def test_move_line_down() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("aaa\nbbb\nccc")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 1))
        await pilot.pause()
        await pilot.press("alt+down")
        await pilot.pause()
        assert editor.text == "bbb\naaa\nccc", repr(editor.text)
        assert editor.cursor_location == (1, 1), editor.cursor_location


async def test_move_line_up() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("aaa\nbbb\nccc")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((1, 2))
        await pilot.pause()
        await pilot.press("alt+up")
        await pilot.pause()
        assert editor.text == "bbb\naaa\nccc", repr(editor.text)
        assert editor.cursor_location == (0, 2), editor.cursor_location


async def test_move_line_at_boundaries_is_noop() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("aaa\nbbb")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 0))
        await pilot.pause()
        await pilot.press("alt+up")
        await pilot.pause()
        assert editor.text == "aaa\nbbb", repr(editor.text)
        editor.move_cursor((1, 0))
        await pilot.pause()
        await pilot.press("alt+down")
        await pilot.pause()
        assert editor.text == "aaa\nbbb", repr(editor.text)


async def test_copy_line_down() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("aaa\nbbb")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 1))
        await pilot.pause()
        await pilot.press("shift+alt+down")
        await pilot.pause()
        assert editor.text == "aaa\naaa\nbbb", repr(editor.text)
        assert editor.cursor_location == (1, 1), editor.cursor_location


async def test_copy_line_up() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("aaa\nbbb")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((1, 2))
        await pilot.pause()
        await pilot.press("shift+alt+up")
        await pilot.pause()
        assert editor.text == "aaa\nbbb\nbbb", repr(editor.text)
        assert editor.cursor_location == (1, 2), editor.cursor_location


async def test_insert_line_below_aliases() -> None:
    keys = ("cmd+enter", "super+enter")
    for key in keys:
        tmp, _ = _fresh_env()
        f = tmp / "lines.txt"
        f.write_text("aaa\nbbb")
        app = _make_app(f)
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = app.query_one("#editor", TextArea)
            editor.move_cursor((0, 2))
            await pilot.pause()
            await pilot.press(key)
            await pilot.pause()
            assert editor.text == "aaa\n\nbbb", (key, repr(editor.text))
            assert editor.cursor_location == (1, 0), (key, editor.cursor_location)


async def test_insert_line_above_aliases() -> None:
    keys = ("cmd+shift+enter", "super+shift+enter")
    for key in keys:
        tmp, _ = _fresh_env()
        f = tmp / "lines.txt"
        f.write_text("aaa\nbbb")
        app = _make_app(f)
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = app.query_one("#editor", TextArea)
            editor.move_cursor((1, 2))
            await pilot.pause()
            await pilot.press(key)
            await pilot.pause()
            assert editor.text == "aaa\n\nbbb", (key, repr(editor.text))
            assert editor.cursor_location == (1, 0), (key, editor.cursor_location)


async def test_indent_line_aliases() -> None:
    keys = (
        "cmd+]",
        "super+]",
        "cmd+right_square_bracket",
        "super+right_square_bracket",
    )
    for key in keys:
        tmp, _ = _fresh_env()
        f = tmp / "lines.txt"
        f.write_text("aaa\nbbb")
        app = _make_app(f)
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = app.query_one("#editor", TextArea)
            editor.move_cursor((1, 1))
            await pilot.pause()
            await pilot.press(key)
            await pilot.pause()
            assert editor.text == "aaa\n  bbb", (key, repr(editor.text))
            assert editor.cursor_location == (1, 3), (key, editor.cursor_location)


async def test_indent_selected_lines() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("aaa\nbbb\nccc")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.selection = type(editor.selection)((0, 1), (1, 2))
        await pilot.pause()
        await pilot.press("cmd+]")
        await pilot.pause()
        assert editor.text == "  aaa\n  bbb\nccc", repr(editor.text)
        assert editor.cursor_location == (1, 4), editor.cursor_location


async def test_outdent_line_aliases() -> None:
    keys = (
        "cmd+[",
        "super+[",
        "cmd+left_square_bracket",
        "super+left_square_bracket",
    )
    for key in keys:
        tmp, _ = _fresh_env()
        f = tmp / "lines.txt"
        f.write_text("aaa\n  bbb")
        app = _make_app(f)
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = app.query_one("#editor", TextArea)
            editor.move_cursor((1, 3))
            await pilot.pause()
            await pilot.press(key)
            await pilot.pause()
            assert editor.text == "aaa\nbbb", (key, repr(editor.text))
            assert editor.cursor_location == (1, 1), (key, editor.cursor_location)


async def test_outdent_selected_lines_removes_up_to_two_spaces() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("alpha\n bravo\n  charlie\n\tdelta")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.selection = type(editor.selection)((0, 0), (3, 3))
        await pilot.pause()
        await pilot.press("cmd+[")
        await pilot.pause()
        assert editor.text == "alpha\nbravo\ncharlie\n\tdelta", repr(editor.text)
        assert editor.cursor_location == (3, 3), editor.cursor_location


async def test_cmd_slash_toggles_python_line_comment() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "comment.py"
    f.write_text("  print('hello')")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        await pilot.press("cmd+/")
        await pilot.pause()
        assert editor.text == "  # print('hello')", repr(editor.text)
        await pilot.press("cmd+/")
        await pilot.pause()
        assert editor.text == "  print('hello')", repr(editor.text)


async def test_cmd_slash_normalized_alias_toggles_python_line_comment() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "comment-normalized.py"
    f.write_text("print('hello')")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        await pilot.press("cmd+slash")
        await pilot.pause()
        assert editor.text == "# print('hello')", repr(editor.text)


async def test_super_slash_normalized_alias_toggles_python_line_comment() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "comment-super-normalized.py"
    f.write_text("print('hello')")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        await pilot.press("super+slash")
        await pilot.pause()
        assert editor.text == "# print('hello')", repr(editor.text)


async def test_cmd_slash_toggles_selected_typescript_lines() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "comment.ts"
    f.write_text("const a = 1;\n  const b = 2;\nconst c = 3;")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.selection = type(editor.selection)((0, 0), (2, 0))
        await pilot.pause()
        await pilot.press("cmd+/")
        await pilot.pause()
        assert editor.text == "// const a = 1;\n  // const b = 2;\nconst c = 3;"
        editor.selection = type(editor.selection)((0, 0), (2, 0))
        await pilot.pause()
        await pilot.press("cmd+/")
        await pilot.pause()
        assert editor.text == "const a = 1;\n  const b = 2;\nconst c = 3;"


async def test_cmd_slash_toggles_css_block_comments() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "comment.css"
    f.write_text("body {\n  color: red;\n}")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.selection = type(editor.selection)((0, 0), (2, 1))
        await pilot.pause()
        await pilot.press("cmd+/")
        await pilot.pause()
        assert editor.text == "/* body { */\n  /* color: red; */\n/* } */"
        editor.selection = type(editor.selection)((0, 0), (2, 7))
        await pilot.pause()
        await pilot.press("cmd+/")
        await pilot.pause()
        assert editor.text == "body {\n  color: red;\n}"


async def test_cmd_slash_unsupported_language_notifies_without_change() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "comment.json"
    f.write_text('{"a": 1}')
    app = _make_app(f)
    notifications: list[tuple[str, str | None]] = []
    app.notify = lambda message, **kwargs: notifications.append(
        (str(message), kwargs.get("severity"))
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        await pilot.press("cmd+/")
        await pilot.pause()
        assert editor.text == '{"a": 1}', repr(editor.text)
        assert notifications == [
            ("Line comments are not supported for this file type.", "warning")
        ]


async def test_alt_z_toggles_word_wrap() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "wrap.txt"
    f.write_text("hello")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        assert editor.soft_wrap is False
        await pilot.press("alt+z")
        await pilot.pause()
        assert editor.soft_wrap is True
        await pilot.press("alt+z")
        await pilot.pause()
        assert editor.soft_wrap is False


async def test_cmd_b_toggles_file_tree() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "tree.txt"
    f.write_text("tree")
    app = _make_app(f, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one("#file-tree", DirectoryTree)
        assert tree.styles.display == "block"
        await pilot.press("cmd+b")
        await pilot.pause()
        assert tree.styles.display == "none"
        await pilot.press("cmd+b")
        await pilot.pause()
        assert tree.styles.display == "block"


async def test_cmd_b_toggles_file_tree_without_open_buffer() -> None:
    tmp, _ = _fresh_env()
    app = _make_app(tmp, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one("#file-tree", DirectoryTree)
        assert tree.styles.display == "block"
        await pilot.press("cmd+b")
        await pilot.pause()
        assert tree.styles.display == "none"
        await pilot.press("cmd+b")
        await pilot.pause()
        assert tree.styles.display == "block"


async def test_super_b_toggles_file_tree_alias() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "tree.txt"
    f.write_text("tree")
    app = _make_app(f, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one("#file-tree", DirectoryTree)
        await pilot.press("super+b")
        await pilot.pause()
        assert tree.styles.display == "none"
        await pilot.press("super+b")
        await pilot.pause()
        assert tree.styles.display == "block"


async def test_super_b_toggles_file_tree_without_open_buffer() -> None:
    tmp, _ = _fresh_env()
    app = _make_app(tmp, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one("#file-tree", DirectoryTree)
        assert tree.styles.display == "block"
        await pilot.press("super+b")
        await pilot.pause()
        assert tree.styles.display == "none"
        await pilot.press("super+b")
        await pilot.pause()
        assert tree.styles.display == "block"


async def test_undo_multiline_insert_that_removes_scrollbar() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "undo.txt"
    original = "\n".join(f"line {index}" for index in range(35))
    f.write_text(original)
    app = _make_app(f)
    async with app.run_test(size=(180, 51)) as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((34, 0))
        await pilot.pause()
        inserted = "\n" + "\n".join(f"added {index}" for index in range(14)) + " tail"
        editor.insert(inserted, maintain_selection_offset=False)
        await pilot.pause()
        assert editor.document.line_count == 49, editor.document.line_count
        await pilot.press("ctrl+z")
        await pilot.pause()
        assert editor.text == original, repr(editor.text)
        assert editor.cursor_location == (34, 0), editor.cursor_location


async def test_alt_backspace_deletes_word_left() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "words.txt"
    f.write_text("hello world foo")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 15))
        await pilot.pause()
        await pilot.press("alt+backspace")
        await pilot.pause()
        text = editor.text
        assert "foo" not in text, repr(text)
        assert text.startswith("hello world"), repr(text)


async def test_cmd_backspace_deletes_to_line_start() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "line-start.txt"
    f.write_text("hello world")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 6))
        await pilot.pause()
        await pilot.press("cmd+backspace")
        await pilot.pause()
        assert editor.text == "world", repr(editor.text)
        assert editor.cursor_location == (0, 0), editor.cursor_location


async def test_cmd_backspace_at_line_start_joins_previous_line() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "join.txt"
    f.write_text("alpha\nbeta")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((1, 0))
        await pilot.pause()
        await pilot.press("cmd+backspace")
        await pilot.pause()
        assert editor.text == "alphabeta", repr(editor.text)
        assert editor.cursor_location == (0, 5), editor.cursor_location


async def test_ghostty_cmd_backspace_sequence_at_line_start_joins_previous_line() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "ghostty-join.txt"
    f.write_text("alpha\nbeta")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((1, 0))
        await pilot.pause()
        await pilot.press("ctrl+u")
        await pilot.pause()
        assert editor.text == "alphabeta", repr(editor.text)
        assert editor.cursor_location == (0, 5), editor.cursor_location


async def test_cmd_backspace_deletes_selection() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "selection.txt"
    f.write_text("hello world")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.selection = type(editor.selection)((0, 6), (0, 11))
        await pilot.pause()
        await pilot.press("cmd+backspace")
        await pilot.pause()
        assert editor.text == "hello ", repr(editor.text)
        assert editor.cursor_location == (0, 6), editor.cursor_location


async def test_cmd_z_undoes_edit() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "undo-cmd.txt"
    f.write_text("alpha")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 5))
        editor.insert(" beta", maintain_selection_offset=False)
        await pilot.pause()
        await pilot.press("cmd+z")
        await pilot.pause()
        assert editor.text == "alpha", repr(editor.text)


async def test_cmd_shift_z_redoes_edit() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "redo-cmd.txt"
    f.write_text("alpha")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 5))
        editor.insert(" beta", maintain_selection_offset=False)
        await pilot.pause()
        await pilot.press("cmd+z")
        await pilot.pause()
        await pilot.press("cmd+shift+z")
        await pilot.pause()
        assert editor.text == "alpha beta", repr(editor.text)


async def test_cmd_x_cuts_selected_text() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "cut-selection.txt"
    f.write_text("alpha beta")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.selection = type(editor.selection)((0, 6), (0, 10))
        await pilot.pause()
        await pilot.press("cmd+x")
        await pilot.pause()
        assert editor.text == "alpha ", repr(editor.text)
        assert editor.cursor_location == (0, 6), editor.cursor_location


async def test_cmd_x_without_selection_cuts_current_line() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "cut-line.txt"
    f.write_text("alpha\nbeta\ngamma")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((1, 2))
        await pilot.pause()
        await pilot.press("cmd+x")
        await pilot.pause()
        assert editor.text == "alpha\ngamma", repr(editor.text)
        assert editor.cursor_location == (1, 2), editor.cursor_location


async def test_alt_shift_arrows_select_word_left_and_right() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "words.txt"
    f.write_text("alpha beta gamma")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 10))
        await pilot.pause()
        await pilot.press("alt+shift+left")
        await pilot.pause()
        assert editor.cursor_location == (0, 6), editor.cursor_location
        assert editor.selection.start == (0, 10), editor.selection
        assert editor.selection.end == (0, 6), editor.selection
        assert editor.selected_text == "beta", repr(editor.selected_text)

        editor.move_cursor((0, 6))
        await pilot.pause()
        await pilot.press("alt+shift+right")
        await pilot.pause()
        assert editor.cursor_location == (0, 10), editor.cursor_location
        assert editor.selection.start == (0, 6), editor.selection
        assert editor.selection.end == (0, 10), editor.selection
        assert editor.selected_text == "beta", repr(editor.selected_text)


async def test_cmd_l_selects_current_line_with_newline() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("alpha\nbeta\ngamma\n")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((1, 2))
        await pilot.pause()
        await pilot.press("cmd+l")
        await pilot.pause()
        assert editor.selection.start == (1, 0), editor.selection
        assert editor.selection.end == (2, 0), editor.selection
        assert editor.cursor_location == (2, 0), editor.cursor_location
        assert editor.selected_text == "beta\n", repr(editor.selected_text)


async def test_cmd_l_repeats_expand_line_selection() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("alpha\nbeta\ngamma\n")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 3))
        await pilot.pause()
        await pilot.press("cmd+l")
        await pilot.pause()
        await pilot.press("cmd+l")
        await pilot.pause()
        assert editor.selection.start == (0, 0), editor.selection
        assert editor.selection.end == (2, 0), editor.selection
        assert editor.cursor_location == (2, 0), editor.cursor_location
        assert editor.selected_text == "alpha\nbeta\n", repr(editor.selected_text)


async def test_super_l_selects_current_line_alias() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("alpha\nbeta\n")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 1))
        await pilot.pause()
        await pilot.press("super+l")
        await pilot.pause()
        assert editor.selection.start == (0, 0), editor.selection
        assert editor.selection.end == (1, 0), editor.selection
        assert editor.selected_text == "alpha\n", repr(editor.selected_text)


async def test_cmd_l_selects_final_line_without_newline() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("alpha\nbeta\ngamma")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((2, 2))
        await pilot.pause()
        await pilot.press("cmd+l")
        await pilot.pause()
        assert editor.selection.start == (2, 0), editor.selection
        assert editor.selection.end == (2, 5), editor.selection
        assert editor.cursor_location == (2, 5), editor.cursor_location
        assert editor.selected_text == "gamma", repr(editor.selected_text)


async def test_cmd_shift_k_deletes_current_line() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("alpha\nbeta\ngamma")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((1, 2))
        await pilot.pause()
        await pilot.press("cmd+shift+k")
        await pilot.pause()
        assert editor.text == "alpha\ngamma", repr(editor.text)
        assert editor.cursor_location == (1, 2), editor.cursor_location


async def test_super_shift_k_deletes_current_line_alias() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("alpha\nbeta\ngamma")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((1, 2))
        await pilot.pause()
        await pilot.press("super+shift+k")
        await pilot.pause()
        assert editor.text == "alpha\ngamma", repr(editor.text)
        assert editor.cursor_location == (1, 2), editor.cursor_location


async def test_ctrl_shift_k_does_not_delete_current_line() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "lines.txt"
    f.write_text("alpha\nbeta\ngamma")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((1, 2))
        await pilot.pause()
        await pilot.press("ctrl+shift+k")
        await pilot.pause()
        assert editor.text == "alpha\nbeta\ngamma", repr(editor.text)
        assert editor.cursor_location == (1, 2), editor.cursor_location


async def test_cmd_shift_left_selects_to_line_start() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "select.txt"
    f.write_text("hello world")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 5))
        await pilot.pause()
        await pilot.press("cmd+shift+left")
        await pilot.pause()
        assert editor.cursor_location == (0, 0), editor.cursor_location
        assert editor.selection.start == (0, 5), editor.selection
        assert editor.selection.end == (0, 0), editor.selection


async def test_cmd_shift_right_selects_to_line_end() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "select.txt"
    f.write_text("hello world")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 5))
        await pilot.pause()
        await pilot.press("cmd+shift+right")
        await pilot.pause()
        assert editor.cursor_location == (0, 11), editor.cursor_location
        assert editor.selection.start == (0, 5), editor.selection
        assert editor.selection.end == (0, 11), editor.selection


async def test_super_shift_line_selection_aliases() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "select.txt"
    f.write_text("hello world")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 5))
        await pilot.pause()
        await pilot.press("super+shift+left")
        await pilot.pause()
        assert editor.selection.start == (0, 5), editor.selection
        assert editor.selection.end == (0, 0), editor.selection
        editor.move_cursor((0, 5))
        await pilot.pause()
        await pilot.press("super+shift+right")
        await pilot.pause()
        assert editor.selection.start == (0, 5), editor.selection
        assert editor.selection.end == (0, 11), editor.selection


async def test_parser_order_super_shift_line_selection_aliases() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "select.txt"
    f.write_text("  hello world")
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.query_one("#editor", TextArea)
        editor.move_cursor((0, 8))
        await pilot.pause()
        await pilot.press("shift+super+left")
        await pilot.pause()
        assert editor.cursor_location == (0, 2), editor.cursor_location
        assert editor.selection.start == (0, 8), editor.selection
        assert editor.selection.end == (0, 2), editor.selection
        assert editor.selected_text == "hello ", repr(editor.selected_text)

        editor.move_cursor((0, 5))
        await pilot.pause()
        await pilot.press("shift+super+right")
        await pilot.pause()
        assert editor.cursor_location == (0, 13), editor.cursor_location
        assert editor.selection.start == (0, 5), editor.selection
        assert editor.selection.end == (0, 13), editor.selection
        assert editor.selected_text == "lo world", repr(editor.selected_text)
