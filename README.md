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
| `⌘⇧V` | Toggle Markdown preview |

Editor shortcuts:

| Shortcut | Action |
| --- | --- |
| `⌥↑` | Move line up |
| `⌥↓` | Move line down |
| `⌥⇧↑` | Copy line up |
| `⌥⇧↓` | Copy line down |
| `⌥⇧F` | Format document |
| `⌘Enter` | Insert line below |
| `⌘⇧Enter` | Insert line above |
| `⌘]` | Indent line |
| `⌘[` | Outdent line |
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

## Formatting

The `⌥⇧F` shortcut formats the current buffer with external formatter CLIs:

- Python files use `ruff`.
- Other supported source/config formats use `prettier`.

Install both tools and make sure they are on `PATH` before using the shortcut:

```sh
bun add --global prettier
uv tool install ruff
```

Files unsupported by both tools are left unchanged and `riched` shows a warning.

## Limitations

- [Textual](https://github.com/textualize/textual) textarea limitation: 
  - no multi-cursor editing
  - no chord hotkey sequence such as `⌘K ⌘S` 

### Ghostty hotkey conflicts

- some hotkeys are bounded by Ghostty by default. eg. `⌘Enter`, `⌘⇧Enter`, `⌘⇧V`, `⌘[`, `⌘]`, `⌘⇧P`, `⌘W`, `⌘Q`...etc
- `riched` detects conflicted shortcuts at startup.
- Conflicted shortcuts are hidden from the footer until they are unbound in Ghostty config, unless the command has another available alternative.
- The key bindings popup marks conflicted shortcuts with `⚠️` and shows a Ghostty config reminder.
- `⌘⇧P` and `F1` are alternative hotkeys for the command palette.

### Unbind Ghostty default keybindings

Ghostty keybindings can be unbound in the Ghostty config file. On macOS, use one of:

- `~/Library/Application Support/com.mitchellh.ghostty/config.ghostty`
- `~/Library/Application Support/com.mitchellh.ghostty/config`
- `~/.config/ghostty/config.ghostty`
- `~/.config/ghostty/config`

Add one `keybind = <trigger>=unbind` line per conflicted shortcut you want to use in `riched`:

```conf
keybind = super+shift+v=unbind
keybind = super+[=unbind
keybind = super+]=unbind
keybind = super+enter=unbind
keybind = super+shift+enter=unbind
```

The command palette can still be opened with `F1`. To use `⌘⇧P` directly, also add:

```conf
keybind = super+shift+p=unbind
```

Then reload Ghostty config with `⌘⇧,` or restart Ghostty. To inspect Ghostty's defaults before changing them:

```sh
ghostty +list-keybinds --default
```

### Disable Ghostty font ligatures

Textual does not expose an app-side font ligature switch. To disable programming ligatures while using `riched`, add this to the same Ghostty config file:

```conf
font-feature = -calt
```
