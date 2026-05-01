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
        ("x.py", "def foo():\n    return 1\n", "python"),
        ("x.ts", "interface Foo { bar: number }\n", "typescript"),
        ("x.tsx", "const X = () => <div>hi</div>;\n", "tsx"),
        ("notes.xyz", "plain text", None),
    )
    for name, content, expected in cases:
        _, _, app = _file_app(name, content)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert _editor(app).language == expected, (name, _editor(app).language)


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
        assert "language:javascript" in ids
        assert "language:python" in ids
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
