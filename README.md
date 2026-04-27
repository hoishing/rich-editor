# Riched

A [rich](https://github.com/Textualize/rich) library powered editor(hence the name `riched`) that implements VS Code keybindings in TUI

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
| `⌘⇧P` / `F1` | Command palette |
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

`riched` persists the selected Textual theme in `settings.yaml` under the user config directory: `~/Library/Application Support/riched/settings.yaml`

## Limitations

- [Textual](https://github.com/textualize/textual) textarea limitation: 
  - no multi-cursor editing
  - no chord hotkey sequence such as `⌘K ⌘S` 

### Ghostty hotkey conflicts

- some hotkeys are bounded by Ghostty by default. eg. `⌘Enter`, `⌘⇧Enter`, `⌘⇧V`, `⌘[`, `⌘]`, `⌘⇧P`, `⌘W`, `⌘Q`...etc
- `riched` detects conflicted app shortcuts at startup and shows the fallback shortcut in the footer when Ghostty is still intercepting the preferred shortcut.
- need to unbound these hotkeys in Ghostty config in order to use them, fall back hotkeys are listed below:
  - `⌘⇧P` → `F1`
  - `⌘⇧V` → `^⇧V`

### Unbind Ghostty default keybindings

Ghostty keybindings can be unbound in the Ghostty config file. On macOS, use one of:

- `~/Library/Application Support/com.mitchellh.ghostty/config.ghostty`
- `~/Library/Application Support/com.mitchellh.ghostty/config`
- `~/.config/ghostty/config.ghostty`
- `~/.config/ghostty/config`

Add one `keybind = <trigger>=unbind` line per conflicted shortcut:

```conf
keybind = super+shift+v=unbind
keybind = super+[=unbind
keybind = super+]=unbind
keybind = super+shift+p=unbind
```

Then reload Ghostty config with `⌘⇧,` or restart Ghostty. To inspect Ghostty's defaults before changing them:

```sh
ghostty +list-keybinds --default
```
