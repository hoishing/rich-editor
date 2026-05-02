from __future__ import annotations

import os
import subprocess
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from heapq import nsmallest
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


@dataclass(frozen=True, slots=True)
class QuickOpenIndexUpdate:
    """A main-thread update produced by quick-open indexing."""

    entries: list[QuickOpenEntry]
    complete: bool = False
    limited: bool = False
    replace: bool = False
    error: str | None = None


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


def quick_open_index_updates(
    root: Path,
    *,
    limit: int = MAX_QUICK_OPEN_INDEX_FILES,
    batch_size: int = QUICK_OPEN_BATCH_SIZE,
) -> Iterator[QuickOpenIndexUpdate]:
    git_result = git_quick_open_entries(root, limit)
    if git_result is not None:
        entries, limited = git_result
        yield QuickOpenIndexUpdate(
            entries,
            complete=True,
            limited=limited,
            replace=True,
        )
        return

    batch: list[QuickOpenEntry] = []
    count = 0
    limited = False
    for entry in scan_quick_open_entries(root):
        if count >= limit:
            limited = True
            break
        batch.append(entry)
        count += 1
        if len(batch) >= batch_size:
            yield QuickOpenIndexUpdate(batch)
            batch = []

    if batch:
        yield QuickOpenIndexUpdate(batch)
    yield QuickOpenIndexUpdate([], complete=True, limited=limited)


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


def ranked_matches(
    entries: list[QuickOpenEntry],
    query: str,
    *,
    limit: int,
) -> list[QuickOpenEntry]:
    stripped_query = query.strip()
    if not stripped_query:
        return entries[:limit]

    scored: list[tuple[tuple[int, int, int, int, str], QuickOpenEntry]] = []
    for entry in entries:
        score = _fuzzy_score(stripped_query, entry.relative_path)
        if score is not None:
            scored.append((score, entry))
    return [
        entry
        for _score, entry in nsmallest(
            limit, scored, key=lambda item: item[0]
        )
    ]


def _fuzzy_score(query: str, candidate: str) -> tuple[int, int, int, int, str] | None:
    query_lower = query.lower()
    candidate_lower = candidate.lower()
    basename = Path(candidate_lower).name
    depth = candidate_lower.count("/")

    if candidate_lower == query_lower:
        return (0, depth, 0, len(candidate_lower), candidate_lower)
    if basename == query_lower:
        return (1, depth, 0, len(candidate_lower), candidate_lower)
    if basename.startswith(query_lower):
        return (2, depth, 0, len(candidate_lower), candidate_lower)
    if candidate_lower.startswith(query_lower):
        return (3, depth, 0, len(candidate_lower), candidate_lower)
    if query_lower in basename:
        return (
            4,
            depth,
            basename.index(query_lower),
            len(candidate_lower),
            candidate_lower,
        )
    if query_lower in candidate_lower:
        return (
            5,
            depth,
            candidate_lower.index(query_lower),
            len(candidate_lower),
            candidate_lower,
        )

    basename_score = _fuzzy_positions(query_lower, basename)
    if basename_score is not None:
        first, gaps = basename_score
        return (6, depth, gaps, first, candidate_lower)

    path_score = _fuzzy_positions(query_lower, candidate_lower)
    if path_score is None:
        return None
    first, gaps = path_score
    return (7, depth, gaps, first, candidate_lower)


def _fuzzy_positions(query_lower: str, candidate_lower: str) -> tuple[int, int] | None:
    positions: list[int] = []
    search_from = 0
    for char in query_lower:
        index = candidate_lower.find(char, search_from)
        if index == -1:
            return None
        positions.append(index)
        search_from = index + 1

    first = positions[0]
    last = positions[-1]
    spread = last - first + 1
    gaps = spread - len(query_lower)
    return first, gaps
