# Riched

> TUI editor with VSCode keybindigs

`riched` is a TUI editor powered by the [Rich](https://github.com/Textualize/rich) package and the [Textual](https://github.com/Textualize/textual) framework, the name is a nod to Rich.

> [!NOTE]
> `riched` targets Ghostty on macOS. Some key bindings, especially shortcuts
> that use the Command key, may not work in other terminals or on other
> operating systems.

## Key Features

- VS Code-style text editing key bindings
- Syntax highlighting
- Resizable project file tree
- Quick open with git-aware indexing, bounded large-folder scanning
- fuzzy matching, symlink traversal

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
uv build
uv publish
```

## Key Bindings

Key bindings are generated from the YAML in `src/riched/bindings.yaml`.
Symbols: `⌘` = Command, `⌃` = Control, `⌥` = Option, `⇧` = Shift.

App shortcuts:

| Shortcut | Action |
| --- | --- |
| `⌃S` | Save |
| `⌃Q` | Quit |
| `⌃W` | Close buffer |
| `F1` | Key bindings |
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

## Won't Implemented

`riched` will not implement key bindings that require users to modify the Ghostty terminal configuration, since terminal-specific configuration makes shortcuts harder to document, test, and support consistently across environments.
