from pathlib import Path

from sticknav_config import default_settings, load_settings, save_settings
from settings_gui import FIELD_DEFINITIONS, SettingsEditor


def test_settings_round_trip(tmp_path: Path) -> None:
    config_path = tmp_path / "sticknav_settings.json"
    settings = default_settings()
    settings["DEAD_ZONE"] = 0.5
    settings["HAT_SELECT_ENABLED"] = False

    save_settings(config_path, settings)
    reloaded = load_settings(config_path)

    assert reloaded["DEAD_ZONE"] == 0.5
    assert reloaded["HAT_SELECT_ENABLED"] is False


def test_apply_settings_updates_live_settings(tmp_path: Path) -> None:
    editor = SettingsEditor.__new__(SettingsEditor)
    editor.settings = {"DEAD_ZONE": 0.1, "HAT_SELECT_ENABLED": True}
    editor.config_path = str(tmp_path / "sticknav_settings.json")
    editor.variables = {}
    editor.on_change = None

    class FakeVar:
        def __init__(self, value: object) -> None:
            self._value = value

        def get(self) -> object:
            return self._value

    for name, _, kind, default in FIELD_DEFINITIONS:
        if kind is bool:
            editor.variables[name] = FakeVar(bool(default))
        elif kind is int:
            editor.variables[name] = FakeVar(str(int(default) if default is not None else ""))
        elif kind is float:
            editor.variables[name] = FakeVar(str(float(default) if default is not None else ""))
        else:
            editor.variables[name] = FakeVar(str(default))

    editor.variables["DEAD_ZONE"] = FakeVar("0.42")
    editor.variables["HAT_SELECT_ENABLED"] = FakeVar(False)

    editor._apply_settings(persist=False)

    assert editor.settings["DEAD_ZONE"] == 0.42
    assert editor.settings["HAT_SELECT_ENABLED"] is False


def test_toggle_window_switches_visibility() -> None:
    editor = SettingsEditor.__new__(SettingsEditor)

    class FakeRoot:
        def __init__(self) -> None:
            self.visible = True

        def withdraw(self) -> None:
            self.visible = False

        def deiconify(self) -> None:
            self.visible = True

        def lift(self) -> None:
            return None

        def focus_force(self) -> None:
            return None

        def winfo_viewable(self) -> bool:
            return self.visible

        def after(self, _delay: int, callback: object) -> None:
            callback()

    editor.root = FakeRoot()

    editor.toggle_window()
    assert editor.root.visible is False

    editor.toggle_window()
    assert editor.root.visible is True


def test_handle_controller_buttons_adjusts_numeric_field() -> None:
    editor = SettingsEditor.__new__(SettingsEditor)
    editor.active_field = "DEAD_ZONE"
    editor.root = type("FakeRoot", (), {"winfo_viewable": lambda self: True})()
    editor.variables = {"DEAD_ZONE": type("FakeVar", (), {"get": lambda self: "0.2", "set": lambda self, value: setattr(self, "value", value)})()}

    editor.handle_controller_buttons(lb_pressed=True, rb_pressed=False)

    assert editor.variables["DEAD_ZONE"].value == "-0.3"
