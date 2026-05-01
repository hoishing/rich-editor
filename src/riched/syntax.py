from __future__ import annotations

from textual.widgets import TextArea

PLAIN_TEXT_ID = "plain-text"
PLAIN_TEXT_LABEL = "Plain text"

EXT_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".json": "json",
    ".md": "markdown",
    ".markdown": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".sql": "sql",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
}
LANGUAGE_LABELS = {
    "bash": "Bash",
    "css": "CSS",
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

_TS_FAMILY_REGISTERED = False


def reset_ts_registration() -> None:
    global _TS_FAMILY_REGISTERED
    _TS_FAMILY_REGISTERED = False


def language_for_suffix(suffix: str) -> str | None:
    return EXT_LANGUAGE.get(suffix.lower())


def apply_language(editor: TextArea, suffix: str) -> None:
    set_language(editor, language_for_suffix(suffix))


def set_language(editor: TextArea, lang: str | None) -> None:
    editor.language = None
    if lang is None:
        return
    if lang in ("typescript", "tsx") and not _register_ts_family(editor):
        lang = "javascript"
    editor.language = lang


def supported_languages(editor: TextArea) -> list[str]:
    _register_ts_family(editor)
    return sorted(editor.available_languages, key=language_label)


def language_label(lang: str | None) -> str:
    if lang is None:
        return PLAIN_TEXT_LABEL
    return LANGUAGE_LABELS.get(lang, lang.replace("_", " ").title())


def _register_ts_family(editor: TextArea) -> bool:
    """Register both ``typescript`` and ``tsx`` grammars on the editor."""
    global _TS_FAMILY_REGISTERED
    if _TS_FAMILY_REGISTERED:
        return True
    try:
        import tree_sitter_typescript as tsts  # type: ignore
        from tree_sitter import Language  # type: ignore
    except Exception:
        return False
    try:
        ts_lang = Language(tsts.language_typescript())
        tsx_lang = Language(tsts.language_tsx())
    except Exception:
        return False
    try:
        editor.register_language("typescript", ts_lang, _TS_HIGHLIGHTS)
        editor.register_language("tsx", tsx_lang, _TS_HIGHLIGHTS + _JSX_HIGHLIGHTS)
    except Exception:
        return False
    _TS_FAMILY_REGISTERED = True
    return True


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
