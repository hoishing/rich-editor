from __future__ import annotations

from textual.widgets import OptionList, Static

from .helpers import _editor, _file_app, _press


def _file_type_button(app) -> Static:
    return app.query_one("#file-type-button", Static)


async def _open_file_type_picker(pilot, app) -> OptionList:
    await pilot.click("#file-type-button")
    await pilot.pause()
    return app.query_one("#file-type-picker", OptionList)


def _option_ids(options: OptionList) -> list[str | None]:
    return [
        options.get_option_at_index(index).id
        for index in range(options.option_count)
    ]


async def _choose_file_type(pilot, app, language: str) -> None:
    options = app.query_one("#file-type-picker", OptionList)
    option_id = f"language:{language}"
    options.highlighted = _option_ids(options).index(option_id)
    await _press(pilot, "enter")


async def test_extension_language_detection() -> None:
    cases = (
        ("x.py", "def foo():\n    return 1\n", "python", "Python"),
        ("x.ts", "interface Foo { bar: number }\n", "typescript", "TypeScript"),
        ("x.tsx", "const X = () => <div>hi</div>;\n", "tsx", "TSX"),
        (".env", "APP_ENV=dev\n", "bash", "Environment"),
        (".env.local", "APP_ENV=dev\n", "bash", "Environment"),
        ("settings.ini", "[app]\nname = rich\n", "toml", "INI"),
        ("app.jsonc", '{\n  // ok\n  "a": 1\n}', "json", "JSONC"),
        ("events.jsonl", '{"a": 1}\n{"b": 2}\n', "json", "JSON Lines"),
        ("app.log", "2026-05-14 INFO started\n", None, "Log"),
        ("Dockerfile", "FROM python:3.12\n", "dockerfile", "Dockerfile"),
        ("Makefile", "run:\n\tuv run rich\n", "makefile", "Makefile"),
        ("notes.xyz", "plain text", None, "Plain text"),
    )
    for name, content, expected_language, expected_label in cases:
        _, _, app = _file_app(name, content)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert _editor(app).language == expected_language, (
                name,
                _editor(app).language,
            )
            assert _file_type_button(app).content == expected_label


async def test_footer_file_type_button_shows_detected_language() -> None:
    _, _, app = _file_app("syntax.py", "print('hello')")
    async with app.run_test() as pilot:
        await pilot.pause()
        assert _file_type_button(app).content == "Python"


async def test_footer_file_type_button_shows_plain_text_for_unknown_type() -> None:
    _, _, app = _file_app("notes.xyz", "plain text")
    async with app.run_test() as pilot:
        await pilot.pause()
        assert _file_type_button(app).content == "Plain text"


async def test_file_type_picker_highlights_current_language_and_dismisses() -> None:
    _, _, app = _file_app("syntax.py", "print('hello')")
    async with app.run_test() as pilot:
        await pilot.pause()

        options = await _open_file_type_picker(pilot, app)
        ids = _option_ids(options)
        assert "language:plain-text" in ids
        assert "language:environment" in ids
        assert "language:javascript" in ids
        assert "language:json-lines" in ids
        assert "language:log" in ids
        assert "language:python" in ids
        assert "language:regex" in ids
        assert options.get_option_at_index(options.highlighted or 0).id == (
            "language:python"
        )

        await _press(pilot, "escape")
        assert not app.query("#file-type-picker")


async def test_file_type_selection_changes_highlighting_and_comment_format() -> None:
    _, _, app = _file_app("syntax.py", "console.log('hello')")
    async with app.run_test() as pilot:
        await pilot.pause()

        await _open_file_type_picker(pilot, app)
        await _choose_file_type(pilot, app, "javascript")

        editor = _editor(app)
        assert editor.language == "javascript"
        assert _file_type_button(app).content == "JavaScript"
        await _press(pilot, "cmd+slash")
        assert editor.text == "// console.log('hello')"


async def test_file_type_selection_uses_specific_footer_label() -> None:
    _, _, app = _file_app("notes.txt", '{"a": 1}')
    async with app.run_test() as pilot:
        await pilot.pause()

        await _open_file_type_picker(pilot, app)
        await _choose_file_type(pilot, app, "json-lines")

        editor = _editor(app)
        assert editor.language == "json"
        assert _file_type_button(app).content == "JSON Lines"


async def test_file_type_selection_is_reset_by_reopening_current_file() -> None:
    _, _, app = _file_app("syntax.py", "print('hello')")
    async with app.run_test() as pilot:
        await pilot.pause()

        await _open_file_type_picker(pilot, app)
        await _choose_file_type(pilot, app, "javascript")
        assert _editor(app).language == "javascript"

        await _press(pilot, "cmd+r")
        assert _editor(app).language == "python"
        assert _file_type_button(app).content == "Python"


async def test_added_file_types_comment_behavior() -> None:
    cases = (
        (".env", "APP_ENV=dev", "# APP_ENV=dev"),
        ("settings.ini", "name = rich", "; name = rich"),
        ("app.jsonc", '"debug": true', '// "debug": true'),
        ("Dockerfile", "FROM python:3.12", "# FROM python:3.12"),
        ("Makefile", "run:", "# run:"),
    )
    for name, content, expected in cases:
        _, _, app = _file_app(name, content)
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            await _press(pilot, "cmd+slash")
            assert editor.text == expected


async def test_json_lines_and_log_comment_toggle_warns_without_change() -> None:
    cases = (
        ("events.jsonl", '{"a": 1}'),
        ("app.log", "2026-05-14 INFO started"),
    )
    for name, content in cases:
        _, _, app = _file_app(name, content)
        notifications: list[tuple[str, str | None]] = []
        app.notify = lambda message, **kwargs: notifications.append(
            (str(message), kwargs.get("severity"))
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = _editor(app)
            await _press(pilot, "cmd+slash")
            assert editor.text == content
            assert notifications == [
                ("Line comments are not supported for this file type.", "warning")
            ]


async def test_log_file_adds_custom_highlights() -> None:
    _, _, app = _file_app(
        "app.log",
        "2026-05-14T12:00:00Z INFO /tmp/app started https://example.com",
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = _editor(app)
        assert _file_type_button(app).content == "Log"
        assert editor.language is None
        highlight_names = {
            highlight[2]
            for line_highlights in editor._highlights.values()  # type: ignore[attr-defined]
            for highlight in line_highlights
        }
        assert {"keyword", "number", "string", "string.special"} <= highlight_names
