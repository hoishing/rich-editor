# Riched

Terminal Editor with VS Code Keybindings Powered by [Rich](https://github.com/Textualize/rich)

> [!NOTE]
> Riched is designed to work with Ghostty based terminal, eg. [ghostty](https://ghostty.org), [cmux](https://cmux.com/) on macOS only.
> 
> Other terminal / OS are not planned.

<table>
  <tr>
    <td align="center" width="50%">
      <img src="https://raw.githubusercontent.com/hoishing/riched/main/docs/python-buffer.svg" alt="Python buffer showing tests/test_file_io.py" width="400">
      <br>
      <sub>Python buffer: tests/test_file_io.py</sub>
    </td>
    <td align="center" width="50%">
      <img src="https://raw.githubusercontent.com/hoishing/riched/main/docs/markdown-preview.svg" alt="Markdown preview of README.md" width="400">
      <br>
      <sub>Markdown preview: README.md</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="https://raw.githubusercontent.com/hoishing/riched/main/docs/command-palette.svg" alt="Command palette opened with F1" width="400">
      <br>
      <sub>Command palette: F1</sub>
    </td>
    <td align="center" width="50%">
      <img src="https://raw.githubusercontent.com/hoishing/riched/main/docs/search-replace.svg" alt="Search and replace popup in README.md" width="400">
      <br>
      <sub>Search and replace: README.md</sub>
    </td>
  </tr>
</table>

## Key Features

- vscode text editing key bindings
- macOS style key bindings work in ssh session to linux host also
- project sidebar with create, rename, quick refresh, and move-to-trash support
- quick file open with fuzzy search
- in-terminal Markdown preview with table of contents toggle
- mouse select-to-copy in the source editor and Markdown preview
- document formatting through external formatter CLIs
- multiple built-in theme(atom, drcula, nordic ...etc)
- syntax highlighting for major file formats with manual file type override

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

Key bindings are generated from the YAML in `src/rich_editor/bindings.yaml`.

App shortcuts:

| Shortcut      | Action                  |
| ------------- | ----------------------- |
| `⌘S` / `⌃S`   | Save                    |
| `F1`          | Command palette         |
| `⌘B` / `⌃B`   | Toggle sidebar          |
| `⌘P`          | Quick open              |
| `⌃H`          | Replace                 |
| `⌃N`          | Create file             |
| `⌘⇧V` / `⌃⇧V` | Toggle Markdown preview |
| `⌥⇧F`         | Format document         |
| `⌘R`          | Refresh                 |

Editor shortcuts:

| Shortcut     | Action               |
| ------------ | -------------------- |
| `⌥↑`         | Move line up         |
| `⌥↓`         | Move line down       |
| `⌥⇧↑`        | Copy line up         |
| `⌥⇧↓`        | Copy line down       |
| `⌘Enter`     | Insert line below    |
| `⌘⇧Enter`    | Insert line above    |
| `⌘]`         | Indent line          |
| `⌘[`         | Outdent line         |
| `⌥⌫`         | Delete word left     |
| `⌘⌫`         | Delete to line start |
| `⌘Z` / `⌃Z`  | Undo                 |
| `⌘⇧Z` / `⌃Y` | Redo                 |
| `⌘X`         | Cut                  |
| `⌘/`         | Toggle line comment  |
| `⌥Z`         | Toggle word wrap     |
| `⌥⇧←`        | Select word left     |
| `⌥⇧→`        | Select word right    |
| `⌘L`         | Select line          |
| `⌘⇧K`        | Delete line          |
| `⌘⇧←`        | Select to line start |
| `⌘⇧→`        | Select to line end   |

Sidebar shortcuts:

| Shortcut    | Action                                |
| ----------- | ------------------------------------- |
| `←`         | Collapse folder                       |
| `→`         | Expand folder                         |
| `Enter`     | Rename selected file or folder        |
| `Space`     | Open file or toggle folder            |
| `⌘⌫` / `⌃U` | Remove selected file or folder          |
| `Esc`       | Quit                                  |

## Settings

Riched persists the selected Textual theme in `settings.yaml` under the user config directory: `~/Library/Application Support/riched/settings.yaml`

## Markdown Preview

Use `⌘⇧V` (`⌃⇧V` if Ghostty still owns `⌘⇧V`), the `Preview` button in the footer, or `F1` → `Toggle Markdown preview` to toggle an in-terminal rendered preview for Markdown files. The preview uses the current editor buffer, so unsaved edits are shown without writing them to disk.

Drag to select text in the preview to copy the rendered text to the clipboard. The same select-to-copy behavior works in the source editor.

When Markdown preview is open, the header shows a `☰` button on the right. Click it to show or hide the Markdown table of contents. The button is hidden while editing the text buffer.

## Syntax And File Types

Riched detects syntax highlighting from the file extension and shows the active file type in the lower-right footer. Unknown extensions are treated as plain text.

Click the file type label to choose another language for the current buffer. Manual selection updates highlighting and language-aware commands such as toggle comment, but reopening or refreshing the file resets the type from the file extension.

Detected extensions include Python, JavaScript, TypeScript, TSX, Bash, environment files, HTML, CSS, JSON, JSONC, JSON Lines, Markdown, YAML, TOML, INI-style config files, XML, SQL, Java, Go, Rust, Dockerfile, Makefile, and logs.

Dockerfile syntax highlighting uses the optional `tree-sitter-dockerfile` package. If that package is unavailable for your platform, Riched still opens Dockerfiles and supports Dockerfile comment toggling, but leaves Dockerfile tree-sitter highlighting disabled. Install `riched[dockerfile]` on supported platforms to enable it.

## Formatting

The `⌥⇧F` shortcut formats the current buffer with external formatter CLIs:

- Python files use `ruff`.
- TOML files use `taplo`.
- XML files use `prettier` with `@prettier/plugin-xml`.
- Other supported source/config formats use `prettier`.

Install the required tools before using the shortcut:

```sh
bun add --global prettier @prettier/plugin-xml
brew install ruff taplo
```

Files unsupported by these tools are left unchanged and Riched shows a warning.

## Refresh

Use the `↻` title-bar button or `⌘R` to refresh the workspace. Refresh reloads the sidebar and reloads the current buffer from disk. If the buffer has unsaved edits, Riched prompts to save, discard, or cancel before reloading.

## Creating Files

Use `⌃N` to create a file. Riched prompts for the file name and supports nested relative paths such as `notes/today.md`.

When a folder is highlighted in the sidebar, the new file is created inside that folder. Otherwise, the new file is created beside the currently open file. If no file is open, the new file is created in the project root.

If the requested file already exists, Riched opens it without overwriting its contents.

## Renaming Files And Folders

When the sidebar is focused, `Enter` opens a rename prompt for the selected file or folder. Renaming keeps the open buffer connected to the renamed path when the current file, or a folder containing it, is renamed.

The project root cannot be renamed. Empty names, path separators, and duplicate target names are rejected in the prompt.

## Moving Files To Trash

When the sidebar is focused, `⌘⌫` removes the selected file or folder by moving it to Trash. The command palette also shows `Move "<name>" to Trash` for the selected sidebar item. Both paths ask for confirmation before moving the item.

On stock Ghostty, `⌘⌫` is delivered to terminal apps as `⌃U`, so Riched binds both forms for the sidebar.

## Limitations

- [Textual](https://github.com/textualize/textual) textarea limitation:
  - no multi-cursor editing
  - no chord hotkey sequence such as `⌘K ⌘S`

### Ghostty hotkey conflicts

- some hotkeys are bound by Ghostty by default. eg. `⌘Z`, `⌘⇧Z`, `⌘⇧V`, `⌘Enter`, `⌘⇧Enter`, `⌘[`, `⌘]`, `⌘W`, `⌘Q`...etc
- Riched detects conflicted shortcuts at startup.
- Conflicted shortcuts are hidden from the footer until they are unbound in Ghostty config, unless the command has another available alternative.
- The key bindings popup marks conflicted shortcuts with `⚠️` and shows a Ghostty config reminder.
- `F1` is the command palette hotkey. `⌘⇧P` is intentionally not bound.

### Unbind Ghostty default keybindings

Ghostty keybindings can be unbound in the Ghostty config file. On macOS, use one of:

- `~/Library/Application Support/com.mitchellh.ghostty/config.ghostty`
- `~/Library/Application Support/com.mitchellh.ghostty/config`
- `~/.config/ghostty/config.ghostty`
- `~/.config/ghostty/config`

Add one `keybind = <trigger>=unbind` line per conflicted shortcut you want to use in Riched:

```conf
keybind = super+[=unbind
keybind = super+]=unbind
keybind = super+enter=unbind
keybind = super+shift+enter=unbind
keybind = super+z=unbind
keybind = super+shift+z=unbind
keybind = super+shift+v=unbind
```

Then reload Ghostty config with `⌘⇧,` or restart Ghostty. To inspect Ghostty's defaults before changing them:

```sh
ghostty +list-keybinds --default
```

### Disable Ghostty font ligatures

Textual does not expose an app-side font ligature switch. To disable programming ligatures while using Riched, add this to the same Ghostty config file:

```conf
font-feature = -calt
```
