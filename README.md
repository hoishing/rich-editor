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
uv run riched hello.txt
uv run python -m tests.runner
```

## Key Bindings

Shipped key bindings live in `src/riched/bindings.yaml`. Press `F1` to show the
hotkey popup; it is generated from the YAML and shows one user-facing shortcut
per binding, preferring `cmd` aliases over `super`.

Common shortcuts:

- `Ctrl+S`: save
- `Ctrl+Q`: quit with dirty-buffer check
- `Ctrl+W`: close buffer
- `Cmd+B`: toggle file tree
- `Cmd+Shift+E`: focus/toggle file tree
- `Cmd+P`: quick open
- `Alt+Up/Down`: move line up/down
- `Alt+Shift+Up/Down`: copy line up/down
- `Cmd+L`: select line
- `Cmd+Shift+Left/Right`: select to line start/end

## Settings

`riched` persists the selected Textual theme in `settings.yaml` under the user
config directory:

- macOS: `~/Library/Application Support/riched/settings.yaml`
- Other platforms: `$XDG_CONFIG_HOME/riched/settings.yaml` or
  `~/.config/riched/settings.yaml`

## Won't Implemented

`riched` will not implement key bindings that require users to modify terminal
emulator configuration. Shortcuts that work through normal terminal keyboard
reporting are allowed; terminal-specific configuration makes shortcuts harder to
document, test, and support consistently across environments.
