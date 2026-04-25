# rich-editor

`riched` is a Textual TUI editor with syntax highlighting and a project file
tree.

## Usage

```sh
uv sync
uv run riched hello.txt
uv run ./e2e.py
```

`./riched hello.txt` is kept as a compatibility wrapper for local use.

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
- `Cmd+Shift+Left/Right`: select to line start/end when the terminal sends it

## Settings

`riched` persists the selected Textual theme in `settings.yaml` under the user
config directory:

- macOS: `~/Library/Application Support/riched/settings.yaml`
- Other platforms: `$XDG_CONFIG_HOME/riched/settings.yaml` or
  `~/.config/riched/settings.yaml`

## Ghostty Cmd-Shift Selection

Ghostty can expose macOS Command as `super` in terminal keybinds. Its default
Cmd-left/right bindings send Ctrl-A/Ctrl-E, which Textual already treats as line
start/end. Cmd-Shift-left/right needs an explicit terminal sequence because
there is no equivalent control character for "select to line start/end".

For Ghostty, add:

```text
keybind = super+shift+arrow_left=csi:1;2H
keybind = super+shift+arrow_right=csi:1;2F
```

`riched` binds both `super+shift+left/right` and `cmd+shift+left/right` to
select from the cursor to line start/end. This is documented as Ghostty-specific
for now because many terminals do not pass Command-modified keys through to TUI
applications.
