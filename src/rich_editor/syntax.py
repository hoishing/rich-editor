from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from importlib.resources import files
from pathlib import Path

from textual.widgets import TextArea

PLAIN_TEXT_ID = "plain-text"
PLAIN_TEXT_LABEL = "Plain text"

_ACTIVE_FILE_TYPE_ATTR = "_rich_editor_file_type"


@dataclass(frozen=True)
class FileType:
    id: str
    label: str
    highlight_language: str | None
    suffixes: tuple[str, ...] = ()
    names: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()


FILE_TYPES = (
    FileType("python", "Python", "python", suffixes=(".py",)),
    FileType("javascript", "JavaScript", "javascript", suffixes=(".js", ".mjs", ".cjs")),
    FileType("typescript", "TypeScript", "typescript", suffixes=(".ts",)),
    FileType("tsx", "TSX", "tsx", suffixes=(".tsx",)),
    FileType(
        "bash",
        "Bash",
        "bash",
        suffixes=(".sh", ".bash", ".zsh"),
        names=(
            ".bashrc",
            ".bash_profile",
            ".bash_aliases",
            ".bash_login",
            ".bash_logout",
            ".profile",
            ".zshrc",
            ".zprofile",
            ".zshenv",
            ".zlogin",
            ".zlogout",
            ".inputrc",
            ".cshrc",
            ".kshrc",
        ),
    ),
    FileType("environment", "Environment", "bash", names=(".env",), patterns=(".env.*",)),
    FileType(
        "ignore",
        "Ignore",
        "bash",
        names=(
            ".gitignore",
            ".gitattributes",
            ".dockerignore",
            ".npmignore",
            ".hgignore",
            ".eslintignore",
            ".prettierignore",
            ".stylelintignore",
            ".rgignore",
        ),
    ),
    FileType("html", "HTML", "html", suffixes=(".html", ".htm")),
    FileType("css", "CSS", "css", suffixes=(".css",)),
    FileType("json", "JSON", "json", suffixes=(".json",)),
    FileType("jsonc", "JSONC", "json", suffixes=(".jsonc",)),
    FileType("json-lines", "JSON Lines", "json", suffixes=(".jsonl", ".ndjson")),
    FileType("markdown", "Markdown", "markdown", suffixes=(".md", ".markdown")),
    FileType("regex", "Regex", "regex"),
    FileType("yaml", "YAML", "yaml", suffixes=(".yaml", ".yml")),
    FileType("toml", "TOML", "toml", suffixes=(".toml",), names=("pipfile",)),
    FileType(
        "ini",
        "INI",
        "toml",
        suffixes=(".ini", ".cfg", ".conf"),
        names=(".editorconfig", ".npmrc", ".yarnrc", ".curlrc", ".wgetrc", ".gitconfig", ".hgrc"),
    ),
    FileType("xml", "XML", "xml", suffixes=(".xml",)),
    FileType("sql", "SQL", "sql", suffixes=(".sql",)),
    FileType("java", "Java", "java", suffixes=(".java",)),
    FileType("go", "Go", "go", suffixes=(".go",)),
    FileType("rust", "Rust", "rust", suffixes=(".rs",)),
    FileType("dockerfile", "Dockerfile", "dockerfile", names=("dockerfile", "containerfile")),
    FileType("makefile", "Makefile", "makefile", suffixes=(".mk",), names=("makefile",)),
    FileType("log", "Log", None, suffixes=(".log",)),
)
FILE_TYPE_BY_ID = {file_type.id: file_type for file_type in FILE_TYPES}
EXT_LANGUAGE = {
    suffix: file_type.highlight_language
    for file_type in FILE_TYPES
    for suffix in file_type.suffixes
    if file_type.highlight_language is not None
}
LANGUAGE_LABELS = {
    "bash": "Bash",
    "css": "CSS",
    "dockerfile": "Dockerfile",
    "go": "Go",
    "html": "HTML",
    "java": "Java",
    "javascript": "JavaScript",
    "json": "JSON",
    "markdown": "Markdown",
    "python": "Python",
    "regex": "Regex",
    "rust": "Rust",
    "sql": "SQL",
    "toml": "TOML",
    "tsx": "TSX",
    "typescript": "TypeScript",
    "xml": "XML",
    "yaml": "YAML",
}


def reset_ts_registration() -> None:
    """Compatibility hook for e2e tests that need fresh editor instances."""


def file_type_for_path(path: str | Path) -> FileType | None:
    target = Path(path)
    name = target.name.lower()
    suffix = target.suffix.lower()
    for file_type in FILE_TYPES:
        if name in file_type.names or suffix in file_type.suffixes:
            return file_type
        if any(fnmatchcase(name, pattern) for pattern in file_type.patterns):
            return file_type
    return None


def language_for_suffix(suffix: str) -> str | None:
    for file_type in FILE_TYPES:
        if suffix.lower() in file_type.suffixes:
            return file_type.highlight_language
    return None


def apply_language(editor: TextArea, path: str | Path) -> None:
    set_file_type(editor, file_type_for_path(path))


def set_language(editor: TextArea, lang: str | None) -> None:
    set_file_type(editor, _file_type_for_language(lang))


def set_file_type(editor: TextArea, file_type: FileType | str | None) -> None:
    if isinstance(file_type, str):
        file_type = FILE_TYPE_BY_ID[file_type]
    register_extra_languages(editor)
    setattr(editor, _ACTIVE_FILE_TYPE_ATTR, file_type.id if file_type is not None else None)
    editor.language = None
    if file_type is None or file_type.highlight_language is None:
        if hasattr(editor, "_build_highlight_map"):
            editor._build_highlight_map()  # type: ignore[attr-defined]
        return
    lang = file_type.highlight_language
    if lang in ("typescript", "tsx") and "typescript" not in editor.available_languages:
        lang = "javascript"
    if lang in {"dockerfile", "makefile"} and lang not in editor.available_languages:
        lang = None
    editor.language = lang


def active_file_type_id(editor: TextArea) -> str | None:
    value = getattr(editor, _ACTIVE_FILE_TYPE_ATTR, None)
    return value if isinstance(value, str) else None


def active_file_type_label(editor: TextArea) -> str:
    file_type_id = active_file_type_id(editor)
    if file_type_id is None:
        return PLAIN_TEXT_LABEL
    return FILE_TYPE_BY_ID[file_type_id].label


def supported_file_types(editor: TextArea) -> list[FileType]:
    register_extra_languages(editor)
    available = editor.available_languages
    return [
        file_type
        for file_type in FILE_TYPES
        if file_type.highlight_language is None
        or file_type.highlight_language in available
        or (
            file_type.highlight_language in {"typescript", "tsx"}
            and "javascript" in available
        )
    ]


def supported_languages(editor: TextArea) -> list[str]:
    return [file_type.id for file_type in supported_file_types(editor)]


def language_label(lang: str | None) -> str:
    if lang is None:
        return PLAIN_TEXT_LABEL
    if lang in FILE_TYPE_BY_ID:
        return FILE_TYPE_BY_ID[lang].label
    return LANGUAGE_LABELS.get(lang, lang.replace("_", " ").title())


def register_extra_languages(editor: TextArea) -> None:
    _register_ts_family(editor)
    _register_dockerfile(editor)
    _register_makefile(editor)


def _file_type_for_language(lang: str | None) -> FileType | None:
    if lang is None:
        return None
    if lang in FILE_TYPE_BY_ID:
        return FILE_TYPE_BY_ID[lang]
    for file_type in FILE_TYPES:
        if file_type.highlight_language == lang:
            return file_type
    return None


def _register_ts_family(editor: TextArea) -> None:
    """Register both ``typescript`` and ``tsx`` grammars on the editor."""
    try:
        import tree_sitter_typescript as tsts  # type: ignore
        from tree_sitter import Language  # type: ignore
    except Exception:
        return
    try:
        ts_lang = Language(tsts.language_typescript())
        tsx_lang = Language(tsts.language_tsx())
    except Exception:
        return
    try:
        editor.register_language("typescript", ts_lang, _TS_HIGHLIGHTS)
        editor.register_language("tsx", tsx_lang, _TS_HIGHLIGHTS + _JSX_HIGHLIGHTS)
    except Exception:
        return


def _register_dockerfile(editor: TextArea) -> None:
    try:
        import tree_sitter_dockerfile as ts_dockerfile  # type: ignore
        from tree_sitter import Language  # type: ignore
    except Exception:
        return
    try:
        dockerfile_lang = Language(ts_dockerfile.language())
        highlights = (
            files("tree_sitter_dockerfile")
            .joinpath("queries/highlights.scm")
            .read_text()
        )
    except Exception:
        return
    try:
        editor.register_language("dockerfile", dockerfile_lang, highlights)
    except Exception:
        return


def _register_makefile(editor: TextArea) -> None:
    try:
        import tree_sitter_make as ts_make  # type: ignore
        from tree_sitter import Language  # type: ignore
    except Exception:
        return
    try:
        make_lang = Language(ts_make.language())
        highlights = ts_make.HIGHLIGHTS_QUERY
    except Exception:
        return
    try:
        editor.register_language("makefile", make_lang, highlights)
    except Exception:
        return


_TS_HIGHLIGHTS = r"""
; --- JavaScript base ---------------------------------------------------------

(identifier) @variable
(property_identifier) @property

(function_expression
  name: (identifier) @function)
(function_declaration
  name: (identifier) @function)
(method_definition
  name: (property_identifier) @function.method)

(pair
  key: (property_identifier) @function.method
  value: [(function_expression) (arrow_function)])

(assignment_expression
  left: (member_expression
    property: (property_identifier) @function.method)
  right: [(function_expression) (arrow_function)])

(variable_declarator
  name: (identifier) @function
  value: [(function_expression) (arrow_function)])

(assignment_expression
  left: (identifier) @function
  right: [(function_expression) (arrow_function)])

(call_expression
  function: (identifier) @function)

(call_expression
  function: (member_expression
    property: (property_identifier) @function.method))

((identifier) @constructor
 (#match? @constructor "^[A-Z]"))

([
    (identifier)
    (shorthand_property_identifier)
    (shorthand_property_identifier_pattern)
 ] @constant
 (#match? @constant "^[A-Z_][A-Z\\d_]+$"))

((identifier) @variable.builtin
 (#match? @variable.builtin "^(arguments|module|console|window|document)$")
 (#is-not? local))

((identifier) @function.builtin
 (#eq? @function.builtin "require")
 (#is-not? local))

(this) @variable.builtin
(super) @variable.builtin

[
  (true)
  (false)
  (null)
  (undefined)
] @constant.builtin

(comment) @comment

[
  (string)
  (template_string)
] @string

(regex) @string.special
(number) @number

[
  ";"
  (optional_chain)
  "."
  ","
] @punctuation.delimiter

[
  "-" "--" "-=" "+" "++" "+=" "*" "*=" "**" "**=" "/" "/=" "%" "%="
  "<" "<=" "<<" "<<=" "=" "==" "===" "!" "!=" "!==" "=>" ">" ">="
  ">>" ">>=" ">>>" ">>>=" "~" "^" "&" "|" "^=" "&=" "|=" "&&" "||"
  "??" "&&=" "||=" "??="
] @operator

[
  "(" ")" "[" "]" "{" "}"
] @punctuation.bracket

(template_substitution
  "${" @punctuation.special
  "}" @punctuation.special) @embedded

[
  "as" "async" "await" "break" "case" "catch" "class" "const" "continue"
  "debugger" "default" "delete" "do" "else" "export" "extends" "finally"
  "for" "from" "function" "get" "if" "import" "in" "instanceof" "let"
  "new" "of" "return" "set" "static" "switch" "target" "throw" "try"
  "typeof" "var" "void" "while" "with" "yield"
] @keyword

; --- TypeScript additions ----------------------------------------------------

(type_identifier) @type
(predefined_type) @type.builtin

((identifier) @type
 (#match? @type "^[A-Z]"))

(type_arguments
  "<" @punctuation.bracket
  ">" @punctuation.bracket)

(required_parameter (identifier) @variable.parameter)
(optional_parameter (identifier) @variable.parameter)

[ "abstract" "declare" "enum" "implements" "interface" "keyof"
  "namespace" "private" "protected" "public" "type" "readonly"
  "override" "satisfies"
] @keyword
"""


_JSX_HIGHLIGHTS = r"""
; --- JSX ---------------------------------------------------------------------

(jsx_opening_element
  ["<" ">"] @punctuation.bracket)

(jsx_closing_element
  ["</" ">"] @punctuation.bracket)

(jsx_self_closing_element
  ["<" "/>"] @punctuation.bracket)

(jsx_opening_element
  name: (identifier) @tag)

(jsx_closing_element
  name: (identifier) @tag)

(jsx_self_closing_element
  name: (identifier) @tag)

(jsx_opening_element
  (member_expression
    object: (identifier) @tag
    property: (property_identifier) @tag))

(jsx_closing_element
  (member_expression
    object: (identifier) @tag
    property: (property_identifier) @tag))

(jsx_self_closing_element
  (member_expression
    object: (identifier) @tag
    property: (property_identifier) @tag))

(jsx_attribute
  (property_identifier) @property)

(jsx_text) @string
"""
