# Repository Guidelines

## Project Structure & Module Organization

This repository is a uv-managed Python project for `riched`, a Textual TUI editor. Application code lives in `src/riched/`: `cli.py` owns argument parsing, `app.py` owns the Textual app and file tree, `editor.py` customizes text editing, `screens.py` contains modal screens, `keybindings.py` loads shortcut config, `bindings.yaml` defines shipped app-owned bindings, and `syntax.py` handles language detection/highlighting. End-to-end tests live in `tests/`; `e2e.py` is a compatibility runner. Root-level `foo.*` and `hello.txt` files are test fixtures/sample content. Avoid committing generated files such as `.venv/`, `__pycache__/`, or build artifacts.

## Build, Test, and Development Commands

- `uv sync`: install project dependencies from `pyproject.toml` and `uv.lock`.
- `uv run riched path/to/file.txt`: open or create a file in the editor.
- `./riched path/to/file.txt`: compatibility wrapper for the same editor command.
- `uv run ./e2e.py`: run the Textual Pilot end-to-end suite.
- `uv add <package>`: add runtime dependencies; do not use `pip`.

## Coding Style & Naming Conventions

Use Python 3.14-compatible code with type hints, `from __future__ import annotations`, `Path`, and small focused helpers. Use 4-space indentation. Keep constants in `UPPER_SNAKE_CASE`, classes in `PascalCase`, functions and methods in `snake_case`, and private helpers prefixed with `_`. Prefer Textual widgets and events over manual terminal control. Keep comments brief and only for non-obvious behavior.

Keep app-owned key bindings in `src/riched/bindings.yaml`, not hardcoded in Python.

## Testing Guidelines

Only add end-to-end tests in `tests/`; do not create unit tests. Tests use Textual's Pilot harness and should be named `test_<behavior>`. Keep each test focused on user-visible behavior such as file open/save, dirty prompts, file tree switching, or syntax highlighting. Use temporary files as existing tests do.

## Commit & Pull Request Guidelines

Use concise imperative commit messages, for example `Add file tree` or `Refactor editor package`. Pull requests should include a short summary, manual/e2e verification steps, related issue links if any, and terminal screenshots or recordings for visible TUI changes. When merging pull requests, use rebase and merge.

## Agent-Specific Instructions

Prefer `uv` for Python tasks. Keep changes scoped to requested behavior. Update `AGENTS.md` when commands, structure, or testing policy changes.
Never change Ghostty settings or configuration, even when investigating Command-key behavior; only document suggested user-side settings when explicitly asked.
