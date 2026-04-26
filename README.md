# Riched

[Rich](https://github.com/Textualize/rich) powered editor, so the name `riched`, that implement vscode keybinding in TUI with best effort.

> [!NOTE]
> `riched` is designed to work with [ghostty](https://ghostty.org) in macOS only

## Key Features

- vscode text editing key bindings
- macOS style key bindings work in ssh session to linux host also
- multiple built-in theme(atom, drcula, nordic ...etc)
- syntax highlighting for major file formats
- quick file open with fuzzy search

## Usage

```sh
uv tool install riched
riched .
riched --version
```

## Dev

```sh
uv sync
uv run riched .
uv run python -m tests.runner
```

## Key Bindings

Key bindings are generated from the YAML in `src/riched/bindings.yaml`.

App shortcuts:

| Shortcut | Action |
| --- | --- |
| `⌘S` | Save |
| `⌃Q` | Quit |
| `F1` | Command palette |
| `⌘B` | Toggle file tree |
| `⌘P` | Quick open |

Editor shortcuts:

| Shortcut | Action |
| --- | --- |
| `⌥↑` | Move line up |
| `⌥↓` | Move line down |
| `⌥⇧↑` | Copy line up |
| `⌥⇧↓` | Copy line down |
| `⌥⌫` | Delete word left |
| `⌘⌫` | Delete to line start |
| `⌘Z` | Undo |
| `⌘⇧Z` | Redo |
| `⌘X` | Cut |
| `⌘/` | Toggle line comment |
| `⌥Z` | Toggle word wrap |
| `⌥⇧←` | Select word left |
| `⌥⇧→` | Select word right |
| `⌘L` | Select line |
| `⌘⇧K` | Delete line |
| `⌘⇧←` | Select to line start |
| `⌘⇧→` | Select to line end |

## Settings

`riched` persists the selected Textual theme in `settings.yaml` under the user
config directory: `~/Library/Application Support/riched/settings.yaml`

## Release Notes

### 0.2.0

- Quick open now opens immediately while indexing in the background.
- File search prefers git-indexed files when available, follows symlinked files and directories, skips cache/build dependency folders, and caps indexing at 10,000 files.
- Fuzzy ranking now prioritizes exact path and filename matches such as `.zshrc`.

## Limitations

- `riched` does not support multi-cursor editing because Textual `TextArea`
  currently models one active cursor/selection.
- Some Command-key shortcuts can conflict with Ghostty or terminal-level
  bindings, for example `⌘C`, `⌘Enter`, `⌘⇧Enter`, `⌘[`, `⌘]`, `⌘⌫`,
  `⌘Z`, `⌘⇧Z`, `⌘⇧P`, `⌘W`, and `⌘Q`.
- `riched` will not implement key bindings that require users to modify the
  Ghostty terminal configuration, since terminal-specific configuration makes
  shortcuts harder to document, test, and support consistently across
  environments.
