from __future__ import annotations

import json

import yaml
from textual.widgets import DataTable, TextArea

from .helpers import _fresh_env, _make_app, mod

# ---------------------------------------------------- keybindings (config) --


async def test_keybindings_default_load_no_file() -> None:
    _fresh_env()
    assert mod.load_bindings() == mod.DEFAULT_BINDINGS


async def test_keybindings_corrupt_yaml_fallback() -> None:
    _, cfg = _fresh_env()
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("{not valid")
    assert mod.load_bindings() == mod.DEFAULT_BINDINGS


async def test_keybindings_persist_roundtrip() -> None:
    _, cfg = _fresh_env()
    m = dict(mod.DEFAULT_BINDINGS)
    m["save"] = "ctrl+g"
    mod.save_bindings(m)
    assert mod.load_bindings()["save"] == "ctrl+g"
    data = yaml.safe_load(cfg.read_text())
    assert data["save"] == "ctrl+g"
    assert data["quit_check"] == "ctrl+q"


async def test_keybindings_legacy_json_migrates_to_yaml() -> None:
    tmp, cfg = _fresh_env()
    legacy = tmp / "keybindings.json"
    legacy.write_text(json.dumps({"save": "ctrl+g"}))
    assert mod.load_bindings()["save"] == "ctrl+g"
    data = yaml.safe_load(cfg.read_text())
    assert data["save"] == "ctrl+g", data
    assert data["quit_check"] == "ctrl+q", data


async def test_custom_bindings_active_in_app() -> None:
    tmp, _ = _fresh_env()
    m = dict(mod.DEFAULT_BINDINGS)
    m["save"] = "ctrl+g"
    mod.save_bindings(m)
    f = tmp / "custom.txt"
    app = _make_app(f, mod.load_bindings())
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#editor", TextArea).load_text("via ctrl+g")
        await pilot.pause()
        await pilot.press("ctrl+g")
        await pilot.pause()
    assert f.read_text() == "via ctrl+g"


# ---------------------------------------------------- keybindings (UI) -----


async def test_keybindings_screen_opens_via_ctrl_k() -> None:
    tmp, _ = _fresh_env()
    f = tmp / "k.txt"
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+k")
        await pilot.pause()
        assert isinstance(app.screen, mod.KeybindingsScreen)
        table = app.screen.query_one(DataTable)
        assert table.row_count == len(mod.COMMANDS), table.row_count
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, mod.KeybindingsScreen)


async def test_keybindings_edit_via_capture_screen_persists_to_disk() -> None:
    tmp, cfg = _fresh_env()
    f = tmp / "k.txt"
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+k")
        await pilot.pause()
        assert isinstance(app.screen, mod.KeybindingsScreen)
        # DataTable cursor on row 0 ("save"). Press Enter to open KeyCaptureScreen.
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, mod.KeyCaptureScreen), type(app.screen).__name__
        await pilot.press("ctrl+g")
        await pilot.pause()
        assert isinstance(app.screen, mod.KeybindingsScreen)
    data = yaml.safe_load(cfg.read_text())
    assert data["save"] == "ctrl+g", data
    # Other defaults preserved.
    assert data["quit_check"] == "ctrl+q"


async def test_keybindings_capture_escape_cancels() -> None:
    tmp, cfg = _fresh_env()
    f = tmp / "k.txt"
    app = _make_app(f)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+k")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, mod.KeyCaptureScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, mod.KeybindingsScreen)
    # No config file written because nothing changed.
    assert not cfg.exists()


async def test_keybindings_reset_to_defaults() -> None:
    tmp, cfg = _fresh_env()
    m = dict(mod.DEFAULT_BINDINGS)
    m["save"] = "ctrl+w"
    mod.save_bindings(m)
    f = tmp / "k.txt"
    app = _make_app(f, mod.load_bindings())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+k")
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
    data = yaml.safe_load(cfg.read_text())
    assert data == mod.DEFAULT_BINDINGS, data


