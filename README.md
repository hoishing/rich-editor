# Riched

`riched` is a TUI editor powered by the [Rich](https://github.com/Textualize/rich) package and the [Textual](https://github.com/Textualize/textual) framework, the name is a nod to Rich.

> [!NOTE]
> `riched` targets Ghostty on macOS. Some key bindings, especially shortcuts
> that use the Command key, may not work in other terminals or on other
> operating systems.

## Key Features

- Syntax highlighting
- Resizable project file tree
- VS Code-style text editing key bindings

## Usage

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
| `Ctrl+S` | Save |
| `Ctrl+Q` | Quit |
| `Ctrl+W` | Close buffer |
| `F1` | Key bindings |
| `Cmd+B` / `Super+B` | Toggle file tree |
| `Cmd+P` / `Super+P` | Quick open |

Editor shortcuts:

| Shortcut | Action |
| --- | --- |
| `Alt+Up` | Move line up |
| `Alt+Down` | Move line down |
| `Alt+Shift+Up` / `Shift+Alt+Up` | Copy line up |
| `Alt+Shift+Down` / `Shift+Alt+Down` | Copy line down |
| `Alt+Backspace` | Delete word left |
| `Alt+Shift+Left` / `Shift+Alt+Left` | Select word left |
| `Alt+Shift+Right` / `Shift+Alt+Right` | Select word right |
| `Super+L` / `Cmd+L` | Select line |
| `Shift+Super+Left` / `Super+Shift+Left` / `Shift+Cmd+Left` / `Cmd+Shift+Left` | Select to line start |
| `Shift+Super+Right` / `Super+Shift+Right` / `Shift+Cmd+Right` / `Cmd+Shift+Right` | Select to line end |

## Settings

`riched` persists the selected Textual theme in `settings.yaml` under the user
config directory: `~/Library/Application Support/riched/settings.yaml`

## Won't Implemented

`riched` will not implement key bindings that require users to modify the Ghostty terminal configuration, since terminal-specific configuration makes shortcuts harder to document, test, and support consistently across environments.

