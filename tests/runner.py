from __future__ import annotations

import asyncio
import importlib
import inspect
import traceback
from collections.abc import Awaitable, Callable
from pathlib import Path

TestFn = Callable[[], Awaitable[None]]


def _test_name(module_name: str, fn_name: str) -> str:
    module_label = module_name.removeprefix("test_").replace("_", " ")
    fn_label = fn_name.removeprefix("test_").replace("_", " ")
    if fn_label.startswith(f"{module_label} "):
        fn_label = fn_label.removeprefix(f"{module_label} ")
    return f"{module_label}: {fn_label}"


def _discover_tests() -> list[tuple[str, TestFn]]:
    root = Path(__file__).parent
    tests: list[tuple[str, TestFn, str, int]] = []
    for path in sorted(root.glob("test_*.py")):
        module = importlib.import_module(f"{__package__}.{path.stem}")
        for name, fn in vars(module).items():
            if (
                name.startswith("test_")
                and inspect.iscoroutinefunction(fn)
                and getattr(fn, "__module__", None) == module.__name__
            ):
                line = inspect.getsourcelines(fn)[1]
                tests.append((_test_name(path.stem, name), fn, path.name, line))
    return [
        (name, fn)
        for name, fn, _, _ in sorted(tests, key=lambda item: (item[2], item[3]))
    ]


TESTS = _discover_tests()


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
