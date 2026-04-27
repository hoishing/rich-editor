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
):
    """Replicate `riched.main()`'s dynamic subclass so BINDINGS take effect."""
    cls = type(
        "ConfiguredRichedApp",
        (mod.RichedApp,),
        {"BINDINGS": mod.build_bindings()},
    )
    app = cls(path, root or path.parent)
    if markdown_preview_hotkey_conflicted is not None:
        app._markdown_preview_hotkey_conflicted = markdown_preview_hotkey_conflicted
    return app
