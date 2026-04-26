from __future__ import annotations

import subprocess
from time import monotonic

from textual.widgets import Static

import riched.app as app_mod
from riched.screens import QuickOpenScreen

from .helpers import _fresh_env, _make_app


async def _wait_for_quick_open_index(app: app_mod.RichedApp, pilot) -> None:
    deadline = monotonic() + 5
    while not app._quick_open_complete:
        assert monotonic() < deadline
        await pilot.pause()


async def test_quick_open_screen_opens_before_indexing_completes() -> None:
    tmp, _ = _fresh_env()
    (tmp / "file.txt").write_text("content")
    app = _make_app(tmp, root=tmp)
    started = False

    def fake_start() -> None:
        nonlocal started
        started = True
        app._quick_open_indexing = True

    app._start_quick_open_index = fake_start
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_quick_open()
        await pilot.pause()
        assert started
        assert isinstance(app.screen, QuickOpenScreen)
        status = app.screen.query_one("#status", Static)
        assert str(status.content) == "Indexing 0 files..."


async def test_quick_open_fallback_skips_heavy_directories() -> None:
    tmp, _ = _fresh_env()
    (tmp / "keep.py").write_text("keep")
    for directory in [
        ".cache",
        ".venv",
        "__pycache__",
        "cache",
        "caches",
        "node_modules",
    ]:
        skipped = tmp / directory
        skipped.mkdir()
        (skipped / "hidden.py").write_text("hidden")
    case_check = tmp / "case-check"
    case_check.mkdir()
    mixed_case_cache = case_check / "Caches"
    mixed_case_cache.mkdir()
    (mixed_case_cache / "hidden.py").write_text("hidden")

    app = _make_app(tmp, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_quick_open()
        await _wait_for_quick_open_index(app, pilot)

    relative_paths = {entry.relative_path for entry in app._quick_open_entries}
    assert "keep.py" in relative_paths
    assert all("hidden.py" not in relative_path for relative_path in relative_paths)


async def test_quick_open_fallback_indexes_by_directory_level() -> None:
    tmp, _ = _fresh_env()
    (tmp / "root.txt").write_text("root")
    first = tmp / "first"
    first.mkdir()
    (first / "first.txt").write_text("first")
    second = tmp / "second"
    second.mkdir()
    (second / "second.txt").write_text("second")
    deep = first / "deep"
    deep.mkdir()
    (deep / "deep.txt").write_text("deep")

    app = _make_app(tmp, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_quick_open()
        await _wait_for_quick_open_index(app, pilot)

    relative_paths = [entry.relative_path for entry in app._quick_open_entries]
    assert relative_paths.index("root.txt") < relative_paths.index("first/first.txt")
    assert relative_paths.index("root.txt") < relative_paths.index("second/second.txt")
    assert relative_paths.index("second/second.txt") < relative_paths.index(
        "first/deep/deep.txt"
    )


async def test_quick_open_fallback_follows_symlinks() -> None:
    tmp, _ = _fresh_env()
    outside = tmp / "outside"
    outside.mkdir()
    (outside / "target.txt").write_text("target")
    (outside / "linked-file.txt").write_text("linked file")
    (tmp / "linked-dir").symlink_to(outside, target_is_directory=True)
    (tmp / "file-link.txt").symlink_to(outside / "linked-file.txt")
    (outside / "loop").symlink_to(tmp, target_is_directory=True)

    app = _make_app(tmp, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_quick_open()
        await _wait_for_quick_open_index(app, pilot)

    relative_paths = [entry.relative_path for entry in app._quick_open_entries]
    assert "file-link.txt" in relative_paths
    assert "linked-dir/target.txt" in relative_paths
    assert len(relative_paths) == len(set(relative_paths))


async def test_quick_open_git_index_includes_ignored_files() -> None:
    tmp, _ = _fresh_env()
    subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
    (tmp / ".gitignore").write_text(".env*\n*.log\nnode_modules/\n")
    (tmp / "tracked.py").write_text("tracked")
    (tmp / "untracked.py").write_text("untracked")
    (tmp / ".env").write_text("secret")
    (tmp / ".env.local").write_text("local secret")
    (tmp / "ignored.log").write_text("ignored")
    skipped = tmp / "node_modules"
    skipped.mkdir()
    (skipped / "hidden.py").write_text("hidden")
    subprocess.run(
        ["git", "add", ".gitignore", "tracked.py"],
        cwd=tmp,
        check=True,
        capture_output=True,
    )

    app = _make_app(tmp, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_quick_open()
        await _wait_for_quick_open_index(app, pilot)

    relative_paths = {entry.relative_path for entry in app._quick_open_entries}
    assert "tracked.py" in relative_paths
    assert "untracked.py" in relative_paths
    assert ".env" in relative_paths
    assert ".env.local" in relative_paths
    assert "ignored.log" in relative_paths
    assert "node_modules/hidden.py" not in relative_paths


async def test_quick_open_git_index_limit_is_visible() -> None:
    tmp, _ = _fresh_env()
    subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
    for index in range(5):
        (tmp / f"file-{index}.txt").write_text(str(index))

    old_limit = app_mod.MAX_QUICK_OPEN_INDEX_FILES
    app_mod.MAX_QUICK_OPEN_INDEX_FILES = 3
    try:
        app = _make_app(tmp, root=tmp)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_quick_open()
            await _wait_for_quick_open_index(app, pilot)
            assert isinstance(app.screen, QuickOpenScreen)
            status = app.screen.query_one("#status", Static)
            assert len(app._quick_open_entries) == 3
            assert str(status.content) == "Showing first 3 files; index limit reached."
    finally:
        app_mod.MAX_QUICK_OPEN_INDEX_FILES = old_limit


async def test_quick_open_fallback_limit_is_visible() -> None:
    tmp, _ = _fresh_env()
    for index in range(5):
        (tmp / f"file-{index}.txt").write_text(str(index))

    old_limit = app_mod.MAX_QUICK_OPEN_INDEX_FILES
    app_mod.MAX_QUICK_OPEN_INDEX_FILES = 3
    try:
        app = _make_app(tmp, root=tmp)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_quick_open()
            await _wait_for_quick_open_index(app, pilot)
            assert isinstance(app.screen, QuickOpenScreen)
            status = app.screen.query_one("#status", Static)
            assert str(status.content) == "Showing first 3 files; index limit reached."
    finally:
        app_mod.MAX_QUICK_OPEN_INDEX_FILES = old_limit


async def test_quick_open_exact_hidden_filename_match_wins() -> None:
    tmp, _ = _fresh_env()
    (tmp / ".zshrc").write_text("target")
    nested = tmp / "nested"
    nested.mkdir()
    (nested / ".zshrc").write_text("nested")
    (tmp / ".zshrc.backup").write_text("backup")
    (tmp / "notes-zshrc.txt").write_text("notes")

    app = _make_app(tmp, root=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_quick_open()
        await _wait_for_quick_open_index(app, pilot)
        assert isinstance(app.screen, QuickOpenScreen)
        matches = app.screen._ranked_matches(".zshrc")

    assert matches[0].relative_path == ".zshrc"
