from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from riched import syntax as syntax_mod  # noqa: E402
from riched.app import RichedApp  # noqa: E402
from riched.keybindings import (  # noqa: E402
    COMMANDS,
    DEFAULT_BINDINGS,
    build_bindings,
)
from riched.screens import (  # noqa: E402
    QuitConfirmationScreen,
    UnsavedChangesScreen,
)

mod = SimpleNamespace(
    COMMANDS=COMMANDS,
    DEFAULT_BINDINGS=DEFAULT_BINDINGS,
    RichedApp=RichedApp,
    QuitConfirmationScreen=QuitConfirmationScreen,
    UnsavedChangesScreen=UnsavedChangesScreen,
    build_bindings=build_bindings,
)


def _fresh_env() -> tuple[Path, Path]:
    """Create an isolated tmpdir + reset globals."""
    tmp = Path(tempfile.mkdtemp(prefix="riched-e2e-"))
    cfg = tmp / "config.yaml"
    syntax_mod.reset_ts_registration()
    return tmp, cfg


def _make_app(
    path: Path,
    root: Path | None = None,
    markdown_preview_hotkey_conflicted: bool | None = None,
    ghostty_app_hotkey_conflicts: set[str] | None = None,
):
    """Replicate `riched.main()`'s dynamic subclass so BINDINGS take effect."""
    cls = type(
        "ConfiguredRichedApp",
        (mod.RichedApp,),
        {"BINDINGS": mod.build_bindings()},
    )
    app = cls(path, root or path.parent)
    if ghostty_app_hotkey_conflicts is not None:
        app._ghostty_app_hotkey_conflicts = ghostty_app_hotkey_conflicts
    if markdown_preview_hotkey_conflicted is not None:
        conflicts = set(app._ghostty_app_hotkey_conflicts)
        if markdown_preview_hotkey_conflicted:
            conflicts.add("toggle_markdown_preview")
        else:
            conflicts.discard("toggle_markdown_preview")
        app._ghostty_app_hotkey_conflicts = conflicts
    return app
