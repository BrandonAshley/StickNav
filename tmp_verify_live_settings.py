from pathlib import Path
import tempfile
from settings_gui import FIELD_DEFINITIONS, SettingsEditor

editor = SettingsEditor.__new__(SettingsEditor)
editor.settings = {"DEAD_ZONE": 0.1, "HAT_SELECT_ENABLED": True}
editor.config_path = str(Path(tempfile.gettempdir()) / "sticknav-live-test.json")
editor.variables = {}

class FakeVar:
    def __init__(self, value):
        self._value = value
    def get(self):
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
editor._apply_settings(persist=True)
print(editor.settings["DEAD_ZONE"])
print(editor.settings["HAT_SELECT_ENABLED"])
print(Path(editor.config_path).read_text(encoding="utf-8").splitlines()[0])
