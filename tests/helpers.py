from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from riched import keybindings, syntax as syntax_mod  # noqa: E402
from riched.app import RichedApp  # noqa: E402
from riched.keybindings import (  # noqa: E402
    COMMANDS,
    DEFAULT_BINDINGS,
    build_bindings,
    load_bindings,
    save_bindings,
)
from riched.screens import (  # noqa: E402
    FileMenuScreen,
    KeyCaptureScreen,
    KeybindingsScreen,
    UnsavedChangesScreen,
)

mod = SimpleNamespace(
    COMMANDS=COMMANDS,
    DEFAULT_BINDINGS=DEFAULT_BINDINGS,
    FileMenuScreen=FileMenuScreen,
    KeyCaptureScreen=KeyCaptureScreen,
    KeybindingsScreen=KeybindingsScreen,
    RichedApp=RichedApp,
    UnsavedChangesScreen=UnsavedChangesScreen,
    build_bindings=build_bindings,
    load_bindings=load_bindings,
    save_bindings=save_bindings,
)


def _fresh_env() -> tuple[Path, Path]:
    """Create an isolated tmpdir + redirect riched's config + reset globals."""
    tmp = Path(tempfile.mkdtemp(prefix="riched-e2e-"))
    cfg = tmp / "keybindings.yaml"
    keybindings.CONFIG_PATH = cfg
    keybindings.LEGACY_CONFIG_PATH = tmp / "keybindings.json"
    syntax_mod.reset_ts_registration()
    return tmp, cfg


def _make_app(
    path: Path,
    mapping: dict[str, str] | None = None,
    root: Path | None = None,
):
    """Replicate `riched.main()`'s dynamic subclass so BINDINGS take effect."""
    if mapping is None:
        mapping = dict(mod.DEFAULT_BINDINGS)
    cls = type(
        "ConfiguredRichedApp",
        (mod.RichedApp,),
        {"BINDINGS": mod.build_bindings(mapping)},
    )
    return cls(path, mapping, root or path.parent)
