# Project: riched

Textual TUI editor. Source in `src/rich_editor/`: `app.py` (app + sidebar), `cli.py` (args), `editor.py` (text area), `screens.py` (modals), `keybindings.py` + `bindings.yaml` (shortcuts), `syntax.py` (highlighting), `settings.py` (theme persistence).

## Commands

- `uv run riched <path>` — run the editor
- `uv run python -m tests.runner` — e2e test suite
- `rm -rf dist && uv build` — build wheel + sdist
- `set -a; source .env; set +a; uv publish --token "$PYPI_API"` — publish to PyPI

## Key rules

- Key bindings go in `bindings.yaml`, not hardcoded Python.
- Tests live in `tests/` as e2e only (Textual Pilot). No unit tests.
- Before adding a hotkey, check Ghostty conflicts with `ghostty +list-keybinds --default`. Verify real terminal key names (not just Pilot synthetic names).
- `Ctrl+[` is Escape — never use as a distinct binding.
