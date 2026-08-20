## Ghostty and hotkeys

Riched only supports Ghostty on macOS. New bindings **must** survive Ghostty interception and real Textual input.

- Before adding a binding: check it is not already bound by Ghostty.
  - Startup **must** detect Ghostty-conflicted hotkeys.
  - Document alternatives as alternatives.
- Verify the real Ghostty/Textual path: do not trust Textual Pilot's synthetic key name.
  - Ghostty interception: `ghostty +list-keybinds --default`.
  - Ctrl punctuation or ambiguous sequences: inspect Textual's ANSI mapping with `uv run python`.
- e2e **must** cover both the requested human spelling and the real Textual key name when they differ.
  - Example: `ctrl+right_square_bracket` for real terminal Ctrl+].
- **Never** use an alternative that collapses to `escape` or another existing semantic key.
  - Ctrl+[ is Escape in terminal input; it is not a distinct alternative.

## Key bindings

Keep bindings in `src/rich_editor/bindings.yaml`, not hardcoded in Python.

- F1 popup: generated from this YAML; user-facing keys come from binding metadata, preferring `cmd` over `super`.
- Command palette: F1-only.
  - **Never** reintroduce `Cmd+Shift+P` as an app binding or documented alternative unless explicitly requested.
- App-level binding changes: test both file-open and no-buffer/directory-start states.
- Command-key regressions: verify both Textual names (`cmd+...` and terminal-normalized `super+...`).
  - Why: Pilot can pass synthetic keys while a real terminal path or missing app state still breaks.
- Alternative-key regressions: verify the real Ghostty/Textual key name, not only the displayed label.
  - Pilot can synthesize impossible keys such as `ctrl+[`; real Ghostty/macOS input arrives as `escape`.
- **Never** patch Command-key behavior with Python-side hardcoded alternatives.
  - Add aliases to `bindings.yaml` and e2e coverage instead.

## Testing

Only e2e tests in `tests/`. **Do not** create unit tests.

- Harness: Textual Pilot.
- Names: `test_<behavior>`.
- Scope: one user-visible behavior per test (file open/save, dirty prompts, sidebar switching, quick-open search/indexing, syntax highlighting).
- Fixtures: temporary files, as existing tests do.
- Hotkey e2e: cover the YAML-declared preferred key, terminal-normalized aliases, and any alternative keys.
  - If the real terminal name differs from the user-facing label, cover the real Textual name too.
- Before accepting an alternative: confirm Ghostty on macOS can produce it distinctly.
  - Ctrl punctuation is especially risky: some combinations are control bytes with legacy meanings.

# PyPi

- use credential in .env file for publishing to PyPi
