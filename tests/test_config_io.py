from pathlib import Path

from sticknav_config import default_settings, load_settings, save_settings
from settings_gui import FIELD_DEFINITIONS, SettingsEditor
from sticknav import apply_button_actions, normalize_action_name, resolve_button_input_index, resolve_vk_name


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


def test_hide_persists_live_settings(tmp_path: Path) -> None:
    editor = SettingsEditor.__new__(SettingsEditor)
    editor.config_path = str(tmp_path / "sticknav_settings.json")
    editor.settings = {"DEAD_ZONE": 0.1, "HAT_SELECT_ENABLED": True}
    editor.variables = {}

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

    class FakeRoot:
        def withdraw(self) -> None:
            return None

    editor.root = FakeRoot()
    editor.hide()

    assert load_settings(editor.config_path)["DEAD_ZONE"] == 0.42
    assert load_settings(editor.config_path)["HAT_SELECT_ENABLED"] is False


def test_handle_controller_buttons_adjusts_numeric_field() -> None:
    editor = SettingsEditor.__new__(SettingsEditor)
    editor.active_field = "DEAD_ZONE"
    editor.root = type("FakeRoot", (), {"winfo_viewable": lambda self: True})()
    editor.variables = {"DEAD_ZONE": type("FakeVar", (), {"get": lambda self: "0.2", "set": lambda self, value: setattr(self, "value", value)})()}

    editor.handle_controller_buttons(lb_pressed=True, rb_pressed=False)

    assert editor.variables["DEAD_ZONE"].value == "-0.3"


def test_capture_mode_assigns_input_value() -> None:
    editor = SettingsEditor.__new__(SettingsEditor)
    editor.pending_capture_field = "LEFT_CLICK_BUTTON_INDEX"
    editor.variables = {"LEFT_CLICK_BUTTON_INDEX": type("FakeVar", (), {"get": lambda self: "0", "set": lambda self, value: setattr(self, "value", value)})()}

    editor.capture_controller_input(3)

    assert editor.variables["LEFT_CLICK_BUTTON_INDEX"].value == "3"


def test_coerce_value_accepts_keyboard_and_mouse_actions() -> None:
    editor = SettingsEditor.__new__(SettingsEditor)
    key_var = type("FakeVar", (), {"get": lambda self: "KEY_SHIFT"})()
    mouse_var = type("FakeVar", (), {"get": lambda self: "MOUSE_LEFT"})()

    assert editor._coerce_value(key_var, int, 0) == "KEY_SHIFT"
    assert editor._coerce_value(mouse_var, int, 0) == "MOUSE_LEFT"


def test_resolve_button_input_index_uses_defaults_for_action_strings() -> None:
    assert resolve_button_input_index("LB_BUTTON_INDEX", "KEY_RIGHT", 4) == 4
    assert resolve_button_input_index("RB_BUTTON_INDEX", "KEY_LEFT", 5) == 5


def test_normalize_action_name_handles_key_and_mouse_actions() -> None:
    assert normalize_action_name("key_windows") == "KEY_WINDOWS"
    assert normalize_action_name("MOUSE_LEFT") == "MOUSE_LEFT"
    assert normalize_action_name("  key_alt  ") == "KEY_ALT"


def test_resolve_vk_name_supports_modifiers() -> None:
    assert resolve_vk_name("windows") == 0x5B
    assert resolve_vk_name("alt") == 0x12
    assert resolve_vk_name("shift") == 0x10


def test_apply_button_actions_dispatches_configured_actions(monkeypatch) -> None:
    calls = []

    def fake_trigger(action: str, pressed: bool) -> None:
        calls.append((action, pressed))

    monkeypatch.setattr("sticknav.trigger_action", fake_trigger)

    class FakeJoystick:
        def get_button(self, button_index: int) -> bool:
            return button_index == 0

    settings = {
        "LEFT_CLICK_BUTTON_INDEX": "MOUSE_LEFT",
        "RIGHT_CLICK_BUTTON_INDEX": "MOUSE_RIGHT",
        "X_BUTTON_INDEX": "KEY_X",
        "Y_BUTTON_INDEX": "KEY_Y",
        "LB_BUTTON_INDEX": "KEY_LEFT",
        "RB_BUTTON_INDEX": "KEY_RIGHT",
    }
    button_states = {
        "LEFT_CLICK_BUTTON_INDEX": False,
        "RIGHT_CLICK_BUTTON_INDEX": False,
        "X_BUTTON_INDEX": False,
        "Y_BUTTON_INDEX": False,
        "LB_BUTTON_INDEX": False,
        "RB_BUTTON_INDEX": False,
        "SELECT_BUTTON_INDEX": False,
        "L3_BUTTON_INDEX": False,
        "R3_BUTTON_INDEX": False,
        "DPAD_UP_BUTTON_INDEX": False,
        "DPAD_DOWN_BUTTON_INDEX": False,
        "DPAD_LEFT_BUTTON_INDEX": False,
        "DPAD_RIGHT_BUTTON_INDEX": False,
    }

    apply_button_actions(settings, FakeJoystick(), button_states)

    assert calls == [("MOUSE_LEFT", True)]
