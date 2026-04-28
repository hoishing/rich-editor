# Repository Guidelines

- check if a hotkey is bounded with Ghostty built-in hotkey before adding any new key binding. Add startup detection for Ghostty-conflicted hotkeys and document any alternative hotkeys as alternatives.
- riched only supports Ghostty on macOS. For every new hotkey or alternative, verify the real Ghostty/Textual terminal path, not only Textual Pilot's synthetic key name. Use `ghostty +list-keybinds --default` to check Ghostty interception, then inspect Textual's ANSI mapping with `uv run python` when the key uses Ctrl punctuation or other ambiguous terminal sequences. Add e2e coverage for both the requested human spelling and the real Textual key name when they differ, for example `ctrl+right_square_bracket` for real terminal Ctrl+]. Do not use alternatives that collapse to `escape` or another existing semantic key; Ctrl+[ is Escape in terminal input and must not be used as a distinct alternative.
- if I ask you to bump the version, run this flow: edit the pyproject.toml -> commit all files -> push -> build -> publish to pypi. Do not run tests.

## Project Structure & Module Organization

This repository is a uv-managed Python project for `riched`, a Textual TUI editor. Application code lives in `src/riched/`: `cli.py` owns argument parsing, `app.py` owns the Textual app and file tree, `editor.py` customizes text editing, `screens.py` contains modal screens, `quick_open.py` indexes quick-open candidates, `keybindings.py` loads shipped shortcut config and popup display rows, `bindings.yaml` defines shipped bindings, `settings.py` persists user settings such as theme, and `syntax.py` handles language detection/highlighting. End-to-end tests live in `tests/`. Avoid committing generated files such as `.venv/`, `__pycache__/`, `keys.log`, `dist/`, or build artifacts.

## Build, Test, and Development Commands

- `uv sync`: install project dependencies from `pyproject.toml` and `uv.lock`.
- `uv run riched path/to/file.txt`: open or create a file in the editor.
- `uv run python -m tests.runner`: run the Textual Pilot end-to-end suite.
- `rm -rf dist && uv build`: clear stale artifacts, then build the source distribution and wheel in `dist/`.
- `set -a; source .env; set +a; uv publish --token "$PYPI_API"`: publish built distributions for a release using the PyPI API key from `.env`.
- `uv add <package>`: add runtime dependencies; do not use `pip`.

## Coding Style & Naming Conventions

Use Python 3.12-compatible code with type hints, `from __future__ import annotations`, `Path`, and small focused helpers. Use 4-space indentation. Keep constants in `UPPER_SNAKE_CASE`, classes in `PascalCase`, functions and methods in `snake_case`, and private helpers prefixed with `_`. Prefer Textual widgets and events over manual terminal control. Keep comments brief and only for non-obvious behavior.

Keep key bindings in `src/riched/bindings.yaml`, not hardcoded in Python. The F1 hotkey popup is generated from this YAML and displays user-facing keys from the binding metadata, preferring `cmd` aliases over `super`.

When changing app-level key bindings, test both file-open and no-buffer/directory-start states. For Command-key regressions, verify both Textual names (`cmd+...` and terminal-normalized `super+...`) because Pilot can pass for synthetic keys while a real terminal path or missing app state still breaks. For alternative-key regressions, verify the real Ghostty/Textual key name in addition to the displayed alternative label; Pilot can synthesize impossible keys such as `ctrl+[` even though real Ghostty/macOS terminal input arrives as `escape`. Do not patch Command-key behavior by adding Python-side hardcoded alternatives; add aliases to `bindings.yaml` and e2e coverage instead.

## Testing Guidelines

Only add end-to-end tests in `tests/`; do not create unit tests. Tests use Textual's Pilot harness and should be named `test_<behavior>`. Keep each test focused on user-visible behavior such as file open/save, dirty prompts, file tree switching, quick-open search/indexing, or syntax highlighting. Use temporary files as existing tests do.

For hotkey e2e tests, cover the YAML-declared preferred key, terminal-normalized aliases, and any alternative keys. If the real terminal key name differs from the user-facing label, cover the real Textual name too. Before accepting an alternative, confirm it can be produced distinctly by Ghostty on macOS; Ctrl punctuation is especially risky because some combinations are control bytes with legacy meanings.

## Commit & Pull Request Guidelines

Use concise imperative commit messages, for example `Add file tree` or `Refactor editor package`. Pull requests should include a short summary, manual/e2e verification steps, related issue links if any, and terminal screenshots or recordings for visible TUI changes. When merging pull requests, use rebase and merge.

## Agent-Specific Instructions

Prefer `uv` for Python tasks. Keep changes scoped to requested behavior. Update `AGENTS.md` when commands, structure, or testing policy changes.
Don't change Ghostty settings or configuration unless you are explicitly told to do so. Document the suggested user-side settings in README.md when explicitly asked.
