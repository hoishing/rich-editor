# rich-editor

`riched` is a Textual TUI editor with syntax highlighting, configurable
shortcuts, and a project file tree.

## Usage

```sh
uv sync
uv run riched hello.txt
uv run ./e2e.py
```

`./riched hello.txt` is kept as a compatibility wrapper for local use.

## Key Bindings

Default app-owned bindings live in `src/riched/bindings.yaml`. User overrides
are saved to `~/.config/riched/keybindings.yaml`. Older
`~/.config/riched/keybindings.json` files are migrated when YAML config does not
already exist.

The in-app keybinding screen edits user-facing app commands such as save, quit,
file menu, and keybindings. Internal editor and modal bindings also come from
the shipped YAML file.

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
