from __future__ import annotations

import os
import subprocess
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

MAX_QUICK_OPEN_INDEX_FILES = 10_000
QUICK_OPEN_BATCH_SIZE = 512
QUICK_OPEN_SKIP_DIRS = {
    ".cache",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "cache",
    "caches",
    "dist",
    "node_modules",
}


@dataclass(frozen=True, slots=True)
class QuickOpenEntry:
    """A quick-open candidate with precomputed display text."""

    path: Path
    relative_path: str


def git_quick_open_entries(
    root: Path, limit: int = MAX_QUICK_OPEN_INDEX_FILES
) -> tuple[list[QuickOpenEntry], bool] | None:
    """Return git-aware file candidates, or None when root is not in a repo."""

    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            [
                "git",
                "-C",
                os.fspath(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        return None

    entries: list[QuickOpenEntry] = []
    limited = False
    try:
        assert process.stdout is not None
        for line in process.stdout:
            relative_path = line.strip()
            if not relative_path or _has_skipped_part(relative_path):
                continue
            path = root / relative_path
            try:
                if path.is_dir():
                    if _should_skip_dir(path.name):
                        continue
                    for entry in scan_quick_open_entries(path):
                        if len(entries) >= limit:
                            limited = True
                            break
                        entries.append(
                            QuickOpenEntry(
                                entry.path,
                                _join_relative(relative_path, entry.relative_path),
                            )
                        )
                    if limited:
                        break
                elif path.is_file():
                    if len(entries) >= limit:
                        limited = True
                        break
                    entries.append(QuickOpenEntry(path, relative_path))
            except OSError:
                continue

        if limited:
            process.terminate()
        return_code = process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        return None
    finally:
        if process.stdout is not None:
            process.stdout.close()

    if return_code != 0 and not limited:
        return None
    return sorted(entries, key=lambda entry: entry.relative_path.lower()), limited


def scan_quick_open_entries(root: Path) -> Iterator[QuickOpenEntry]:
    """Yield fallback candidates breadth-first, following symlinks safely."""

    queue: deque[tuple[str, str]] = deque([(os.fspath(root), "")])
    visited_directories: set[str] = set()
    while queue:
        directory, relative_directory = queue.popleft()
        try:
            real_directory = os.path.realpath(directory)
        except OSError:
            continue
        if real_directory in visited_directories:
            continue
        visited_directories.add(real_directory)

        try:
            with os.scandir(directory) as entries:
                directories: list[tuple[str, str]] = []
                files: list[QuickOpenEntry] = []
                for entry in entries:
                    relative_path = _join_relative(relative_directory, entry.name)
                    try:
                        if entry.is_dir(follow_symlinks=True):
                            if not _should_skip_dir(entry.name):
                                directories.append((entry.path, relative_path))
                        elif entry.is_file(follow_symlinks=True):
                            files.append(
                                QuickOpenEntry(Path(entry.path), relative_path)
                            )
                    except OSError:
                        continue
        except OSError:
            continue

        directories.sort(key=lambda item: item[1].lower())
        queue.extend(directories)
        yield from sorted(files, key=lambda entry: entry.relative_path.lower())


def _join_relative(directory: str, name: str) -> str:
    if not directory:
        return name
    return f"{directory}/{name}"


def _has_skipped_part(relative_path: str) -> bool:
    return any(_should_skip_dir(part) for part in relative_path.split("/"))


def _should_skip_dir(name: str) -> bool:
    return name in QUICK_OPEN_SKIP_DIRS or name.lower() in QUICK_OPEN_SKIP_DIRS
