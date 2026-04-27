from __future__ import annotations

from .helpers import _editor, _file_app


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

