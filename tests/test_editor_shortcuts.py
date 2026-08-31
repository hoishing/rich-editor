from __future__ import annotations

from textual.widgets import DirectoryTree

from .helpers import _directory_app, _editor, _file_app, _press, _press_many, _select


async def _run_editor_case(
    *,
    key: str,
    content: str,
    cursor: tuple[int, int] | None = None,
    selection: tuple[tuple[int, int], tuple[int, int]] | None = None,
    expected_text: str,
    expected_cursor: tuple[int, int] | None = None,
    expected_selection: tuple[tuple[int, int], tuple[int, int]] | None = None,
    expected_selected_text: str | None = None,
    name: str = "lines.txt",
) -> None:
    _, _, app = _file_app(name, content)
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        if cursor is not None:
            editor.move_cursor(cursor)
        if selection is not None:
            _select(editor, *selection)
        await pilot.pause()
        await _press(pilot, key)
        assert editor.text == expected_text, (key, repr(editor.text))
        if expected_cursor is not None:
            assert editor.cursor_location == expected_cursor, (key, editor.cursor_location)
        if expected_selection is not None:
            assert not editor.selection.is_empty, (key, editor.selection)
            assert editor.selection.start == expected_selection[0], (
                key,
                editor.selection,
            )
            assert editor.selection.end == expected_selection[1], (
                key,
                editor.selection,
            )
        if expected_selected_text is not None:
            assert editor.selected_text == expected_selected_text, (
                key,
                repr(editor.selected_text),
            )


async def test_move_line_shortcuts() -> None:
    cases = (
        ("alt+down", "aaa\nbbb\nccc", (0, 1), "bbb\naaa\nccc", (1, 1)),
        ("alt+up", "aaa\nbbb\nccc", (1, 2), "bbb\naaa\nccc", (0, 2)),
    )
    for key, content, cursor, expected_text, expected_cursor in cases:
        await _run_editor_case(
            key=key,
            content=content,
            cursor=cursor,
            expected_text=expected_text,
            expected_cursor=expected_cursor,
        )


async def test_move_line_at_boundaries_is_noop() -> None:
    for key, cursor in (("alt+up", (0, 0)), ("alt+down", (1, 0))):
        await _run_editor_case(
            key=key,
            content="aaa\nbbb",
            cursor=cursor,
            expected_text="aaa\nbbb",
        )


async def test_copy_line_shortcuts() -> None:
    cases = (
        ("shift+alt+down", (0, 1), "aaa\naaa\nbbb", (1, 1)),
        ("shift+alt+up", (1, 2), "aaa\nbbb\nbbb", (1, 2)),
    )
    for key, cursor, expected_text, expected_cursor in cases:
        await _run_editor_case(
            key=key,
            content="aaa\nbbb",
            cursor=cursor,
            expected_text=expected_text,
            expected_cursor=expected_cursor,
        )


async def test_indent_and_outdent_aliases() -> None:
    cases = (
        (
            ("cmd+]", "super+]", "cmd+right_square_bracket", "super+right_square_bracket"),
            "aaa\nbbb",
            (1, 1),
            "aaa\n  bbb",
            (1, 3),
        ),
        (
            ("cmd+[", "super+[", "cmd+left_square_bracket", "super+left_square_bracket"),
            "aaa\n  bbb",
            (1, 3),
            "aaa\nbbb",
            (1, 1),
        ),
    )
    for keys, content, cursor, expected_text, expected_cursor in cases:
        for key in keys:
            await _run_editor_case(
                key=key,
                content=content,
                cursor=cursor,
                expected_text=expected_text,
                expected_cursor=expected_cursor,
            )


async def test_indent_and_outdent_selected_lines() -> None:
    cases = (
        (
            "cmd+]",
            "aaa\nbbb\nccc",
            ((0, 1), (1, 2)),
            "  aaa\n  bbb\nccc",
            (1, 4),
            ((0, 3), (1, 4)),
            "aa\n  bb",
        ),
        (
            "cmd+[",
            "alpha\n bravo\n  charlie\n\tdelta",
            ((1, 1), (2, 4)),
            "alpha\nbravo\ncharlie\n\tdelta",
            (2, 2),
            ((1, 0), (2, 2)),
            "bravo\nch",
        ),
        (
            "cmd+]",
            "aaa\nbbb\nccc",
            ((0, 0), (2, 0)),
            "  aaa\n  bbb\nccc",
            (2, 0),
            ((0, 0), (2, 0)),
            "  aaa\n  bbb\n",
        ),
    )
    for (
        key,
        content,
        selection,
        expected_text,
        expected_cursor,
        expected_selection,
        expected_selected_text,
    ) in cases:
        await _run_editor_case(
            key=key,
            content=content,
            selection=selection,
            expected_text=expected_text,
            expected_cursor=expected_cursor,
            expected_selection=expected_selection,
            expected_selected_text=expected_selected_text,
        )


async def test_comment_shortcuts() -> None:
    for key in ("cmd+/", "cmd+slash", "super+slash"):
        await _run_editor_case(
            key=key,
            name="comment.py",
            content="print('hello')",
            expected_text="# print('hello')",
            expected_cursor=(0, 2),
        )

    _, _, app = _file_app("comment.py", "  print('hello')")
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        await _press_many(pilot, "cmd+/", "cmd+/")
        assert editor.text == "  print('hello')", repr(editor.text)


async def test_comment_shortcuts_preserve_cursor_position() -> None:
    cases = (
        (
            "comment.py",
            "print('hello')",
            (0, 6),
            "# print('hello')",
            (0, 8),
        ),
        (
            "comment.py",
            "# print('hello')",
            (0, 8),
            "print('hello')",
            (0, 6),
        ),
        (
            "comment.py",
            "  print('hello')",
            (0, 1),
            "  # print('hello')",
            (0, 1),
        ),
        (
            "comment.py",
            "  print('hello')",
            (0, 2),
            "  # print('hello')",
            (0, 4),
        ),
        (
            "comment.py",
            "  # print('hello')",
            (0, 3),
            "  print('hello')",
            (0, 2),
        ),
        (
            "comment.css",
            "body {",
            (0, 5),
            "/* body { */",
            (0, 8),
        ),
        (
            "comment.css",
            "/* body { */",
            (0, 8),
            "body {",
            (0, 5),
        ),
    )
    for name, content, cursor, expected_text, expected_cursor in cases:
        await _run_editor_case(
            key="cmd+/",
            name=name,
            content=content,
            cursor=cursor,
            expected_text=expected_text,
            expected_cursor=expected_cursor,
        )


async def test_comment_shortcuts_preserve_selection_position() -> None:
    await _run_editor_case(
        key="cmd+/",
        name="comment.ts",
        content="  alpha beta",
        selection=((0, 2), (0, 7)),
        expected_text="  // alpha beta",
        expected_cursor=(0, 10),
        expected_selection=((0, 5), (0, 10)),
        expected_selected_text="alpha",
    )
    await _run_editor_case(
        key="cmd+/",
        name="comment.ts",
        content="  // alpha beta",
        selection=((0, 5), (0, 10)),
        expected_text="  alpha beta",
        expected_cursor=(0, 7),
        expected_selection=((0, 2), (0, 7)),
        expected_selected_text="alpha",
    )


async def test_comment_selection_and_block_comment_cases() -> None:
    cases = (
        (
            "comment.ts",
            "const a = 1;\n  const b = 2;\nconst c = 3;",
            ((0, 0), (2, 0)),
            "// const a = 1;\n  // const b = 2;\nconst c = 3;",
            ((0, 0), (2, 0)),
            "const a = 1;\n  const b = 2;\nconst c = 3;",
        ),
        (
            "comment.css",
            "body {\n  color: red;\n}",
            ((0, 0), (2, 1)),
            "/* body { */\n  /* color: red; */\n/* } */",
            ((0, 0), (2, 7)),
            "body {\n  color: red;\n}",
        ),
    )
    for name, content, first_selection, commented, second_selection, uncommented in cases:
        _, _, app = _file_app(name, content)
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            _select(editor, *first_selection)
            await pilot.pause()
            await _press(pilot, "cmd+/")
            assert editor.text == commented
            _select(editor, *second_selection)
            await pilot.pause()
            await _press(pilot, "cmd+/")
            assert editor.text == uncommented


async def test_cmd_slash_unsupported_language_notifies_without_change() -> None:
    _, _, app = _file_app("comment.json", '{"a": 1}')
    notifications: list[tuple[str, str | None]] = []
    app.notify = lambda message, **kwargs: notifications.append(
        (str(message), kwargs.get("severity"))
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        await _press(pilot, "cmd+/")
        assert editor.text == '{"a": 1}', repr(editor.text)
        assert notifications == [
            ("Line comments are not supported for this file type.", "warning")
        ]


async def test_alt_z_toggles_word_wrap() -> None:
    _, _, app = _file_app("wrap.txt", "hello")
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        assert editor.soft_wrap is False
        await _press(pilot, "alt+z")
        assert editor.soft_wrap is True
        await _press(pilot, "alt+z")
        assert editor.soft_wrap is False


async def test_sidebar_toggle_aliases_with_and_without_open_buffer() -> None:
    for key, with_buffer in (
        ("cmd+b", True),
        ("super+b", True),
        ("ctrl+b", True),
        ("cmd+b", False),
        ("super+b", False),
        ("ctrl+b", False),
    ):
        if with_buffer:
            _, _, app = _file_app("tree.txt", "tree", root_is_tmp=True)
        else:
            _, app = _directory_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            tree = app.query_one("#sidebar", DirectoryTree)
            assert tree.styles.display == "block"
            await _press(pilot, key)
            assert tree.styles.display == "none", key
            await _press(pilot, key)
            assert tree.styles.display == "block", key


async def test_undo_multiline_insert_that_removes_scrollbar() -> None:
    original = "\n".join(f"line {index}" for index in range(35))
    _, _, app = _file_app("undo.txt", original)
    async with app.run_test(size=(180, 51)) as pilot:
        await pilot.pause()
        editor = _editor(app)
        editor.move_cursor((34, 0))
        await pilot.pause()
        inserted = "\n" + "\n".join(f"added {index}" for index in range(14)) + " tail"
        editor.insert(inserted, maintain_selection_offset=False)
        await pilot.pause()
        assert editor.document.line_count == 49, editor.document.line_count
        await _press(pilot, "ctrl+z")
        assert editor.text == original, repr(editor.text)
        assert editor.cursor_location == (34, 0), editor.cursor_location


async def test_delete_left_shortcuts() -> None:
    cases = (
        ("alt+backspace", "hello world foo", (0, 15), "hello world ", None),
        ("cmd+backspace", "hello world", (0, 6), "world", (0, 0)),
        ("cmd+backspace", "alpha\nbeta", (1, 0), "alphabeta", (0, 5)),
        ("ctrl+u", "alpha\nbeta", (1, 0), "alphabeta", (0, 5)),
    )
    for key, content, cursor, expected_text, expected_cursor in cases:
        await _run_editor_case(
            key=key,
            content=content,
            cursor=cursor,
            expected_text=expected_text,
            expected_cursor=expected_cursor,
        )


async def test_cmd_backspace_deletes_selection() -> None:
    await _run_editor_case(
        key="cmd+backspace",
        content="hello world",
        selection=((0, 6), (0, 11)),
        expected_text="hello ",
        expected_cursor=(0, 6),
    )


async def test_undo_and_redo_shortcuts() -> None:
    for key, expected in (("cmd+z", "alpha"), ("cmd+shift+z", "alpha beta")):
        _, _, app = _file_app("undo-cmd.txt", "alpha")
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            editor.move_cursor((0, 5))
            editor.insert(" beta", maintain_selection_offset=False)
            await pilot.pause()
            await _press(pilot, "cmd+z")
            if key == "cmd+shift+z":
                await _press(pilot, key)
            assert editor.text == expected, (key, repr(editor.text))


async def test_cut_shortcuts() -> None:
    await _run_editor_case(
        key="cmd+x",
        content="alpha beta",
        selection=((0, 6), (0, 10)),
        expected_text="alpha ",
        expected_cursor=(0, 6),
    )
    await _run_editor_case(
        key="cmd+x",
        content="alpha\nbeta\ngamma",
        cursor=(1, 2),
        expected_text="alpha\ngamma",
        expected_cursor=(1, 2),
    )


async def test_alt_shift_arrows_select_word_left_and_right() -> None:
    _, _, app = _file_app("words.txt", "alpha beta gamma")
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        editor.move_cursor((0, 10))
        await pilot.pause()
        await _press(pilot, "alt+shift+left")
        assert editor.cursor_location == (0, 6), editor.cursor_location
        assert editor.selection.start == (0, 10), editor.selection
        assert editor.selection.end == (0, 6), editor.selection
        assert editor.selected_text == "beta", repr(editor.selected_text)

        editor.move_cursor((0, 6))
        await pilot.pause()
        await _press(pilot, "alt+shift+right")
        assert editor.cursor_location == (0, 10), editor.cursor_location
        assert editor.selection.start == (0, 6), editor.selection
        assert editor.selection.end == (0, 10), editor.selection
        assert editor.selected_text == "beta", repr(editor.selected_text)


async def test_line_selection_shortcuts() -> None:
    cases: tuple[tuple[str, str, tuple[int, int], tuple[int, int], tuple[int, int], str], ...] = (
        ("cmd+l", "alpha\nbeta\ngamma\n", (1, 2), (1, 0), (2, 0), "beta\n"),
        ("super+l", "alpha\nbeta\n", (0, 1), (0, 0), (1, 0), "alpha\n"),
        ("cmd+l", "alpha\nbeta\ngamma", (2, 2), (2, 0), (2, 5), "gamma"),
    )
    for key, content, cursor, start, end, selected in cases:
        _, _, app = _file_app("lines.txt", content)
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            editor.move_cursor(cursor)
            await pilot.pause()
            await _press(pilot, key)
            assert editor.selection.start == start, (key, editor.selection)
            assert editor.selection.end == end, (key, editor.selection)
            assert editor.cursor_location == end, (key, editor.cursor_location)
            assert editor.selected_text == selected, (key, repr(editor.selected_text))


async def test_cmd_l_repeats_expand_line_selection() -> None:
    _, _, app = _file_app("lines.txt", "alpha\nbeta\ngamma\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        editor.move_cursor((0, 3))
        await pilot.pause()
        await _press_many(pilot, "cmd+l", "cmd+l")
        assert editor.selection.start == (0, 0), editor.selection
        assert editor.selection.end == (2, 0), editor.selection
        assert editor.cursor_location == (2, 0), editor.cursor_location
        assert editor.selected_text == "alpha\nbeta\n", repr(editor.selected_text)


async def test_delete_current_line_shortcuts() -> None:
    cases = (
        ("cmd+shift+k", "alpha\ngamma", (1, 2)),
        ("super+shift+k", "alpha\ngamma", (1, 2)),
        ("ctrl+shift+k", "alpha\nbeta\ngamma", (1, 2)),
    )
    for key, expected_text, expected_cursor in cases:
        await _run_editor_case(
            key=key,
            content="alpha\nbeta\ngamma",
            cursor=(1, 2),
            expected_text=expected_text,
            expected_cursor=expected_cursor,
        )


async def test_cmd_shift_selects_to_line_boundaries() -> None:
    cases = (
        ("cmd+shift+left", (0, 0)),
        ("cmd+shift+right", (0, 11)),
        ("super+shift+left", (0, 0)),
        ("super+shift+right", (0, 11)),
    )
    for key, end in cases:
        _, _, app = _file_app("select.txt", "hello world")
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            editor.move_cursor((0, 5))
            await pilot.pause()
            await _press(pilot, key)
            assert editor.cursor_location == end, (key, editor.cursor_location)
            assert editor.selection.start == (0, 5), (key, editor.selection)
            assert editor.selection.end == end, (key, editor.selection)


async def test_parser_order_super_shift_line_selection_aliases() -> None:
    cases: tuple[tuple[str, tuple[int, int], tuple[int, int], str], ...] = (
        ("shift+super+left", (0, 8), (0, 2), "hello "),
        ("shift+super+right", (0, 5), (0, 13), "lo world"),
    )
    for key, cursor, end, selected in cases:
        _, _, app = _file_app("select.txt", "  hello world")
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            editor.move_cursor(cursor)
            await pilot.pause()
            await _press(pilot, key)
            assert editor.cursor_location == end, (key, editor.cursor_location)
            assert editor.selection.start == cursor, (key, editor.selection)
            assert editor.selection.end == end, (key, editor.selection)
            assert editor.selected_text == selected, (key, repr(editor.selected_text))
