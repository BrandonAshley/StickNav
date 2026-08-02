import argparse
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Tuple

try:
    from pynput import keyboard as pynput_keyboard
    from pynput import mouse as pynput_mouse
except ImportError:  # pragma: no cover - optional dependency at runtime
    pynput_keyboard = None
    pynput_mouse = None

from sticknav_config import CONFIG_PATH, load_settings, save_settings

BUTTON_FIELD_NAMES = (
    "LEFT_CLICK_BUTTON_INDEX",
    "RIGHT_CLICK_BUTTON_INDEX",
    "X_BUTTON_INDEX",
    "Y_BUTTON_INDEX",
    "LB_BUTTON_INDEX",
    "RB_BUTTON_INDEX",
    "SELECT_BUTTON_INDEX",
    "L3_BUTTON_INDEX",
    "R3_BUTTON_INDEX",
    "DPAD_UP_BUTTON_INDEX",
    "DPAD_DOWN_BUTTON_INDEX",
    "DPAD_LEFT_BUTTON_INDEX",
    "DPAD_RIGHT_BUTTON_INDEX",
)

SPECIAL_KEY_NAMES = {
    "shift": "KEY_SHIFT",
    "shift_l": "KEY_SHIFT",
    "shift_r": "KEY_SHIFT",
    "ctrl": "KEY_CTRL",
    "ctrl_l": "KEY_CTRL",
    "ctrl_r": "KEY_CTRL",
    "alt": "KEY_ALT",
    "alt_l": "KEY_ALT",
    "alt_gr": "KEY_ALT",
    "alt_r": "KEY_ALT",
    "tab": "KEY_TAB",
    "enter": "KEY_ENTER",
    "backspace": "KEY_BACKSPACE",
    "escape": "KEY_ESCAPE",
    "space": "KEY_SPACE",
    "up": "KEY_UP",
    "down": "KEY_DOWN",
    "left": "KEY_LEFT",
    "right": "KEY_RIGHT",
    "cmd": "KEY_WINDOWS",
    "cmd_l": "KEY_WINDOWS",
    "cmd_r": "KEY_WINDOWS",
    "super": "KEY_WINDOWS",
    "super_l": "KEY_WINDOWS",
    "super_r": "KEY_WINDOWS",
    "win": "KEY_WINDOWS",
    "windows": "KEY_WINDOWS",
    "meta": "KEY_WINDOWS",
}

FIELD_DEFINITIONS: List[Tuple[str, str, type, Any]] = [
    ("DEAD_ZONE", "Dead zone", float, 0.22),
    ("RIGHT_STICK_DEAD_ZONE", "Right stick dead zone", float, 0.18),
    ("SCROLL_STEP", "Scroll step", int, 30),
    ("BASE_SPEED", "Base speed", float, 3.0),
    ("MAX_SPEED", "Max speed", float, 20.0),
    ("ACCELERATION", "Acceleration", float, 10.0),
    ("SENSITIVITY_CURVE", "Sensitivity curve", float, 1.35),
    ("LEFT_CLICK_BUTTON_INDEX", "A Button (Left Click)", int, 0),
    ("RIGHT_CLICK_BUTTON_INDEX", "B Button (Right Click)", int, 1),
    ("X_BUTTON_INDEX", "X Button", int, 2),
    ("Y_BUTTON_INDEX", "Y Button", int, 3),
    ("LB_BUTTON_INDEX", "LB button", int, 4),
    ("RB_BUTTON_INDEX", "RB button", int, 5),
    ("SELECT_BUTTON_INDEX", "Select button", int, None),
    ("L3_BUTTON_INDEX", "L3 button", int, None),
    ("R3_BUTTON_INDEX", "R3 button", int, None),
    ("DPAD_UP_BUTTON_INDEX", "D-pad Up", int, None),
    ("DPAD_DOWN_BUTTON_INDEX", "D-pad Down", int, None),
    ("DPAD_LEFT_BUTTON_INDEX", "D-pad Left", int, None),
    ("DPAD_RIGHT_BUTTON_INDEX", "D-pad Right", int, None),
    ("LT_AXIS_INDEX", "LT axis index", int, 4),
    ("RT_AXIS_INDEX", "RT axis index", int, 5),
    ("TRIGGER_DEAD_ZONE", "Trigger dead zone", float, 0.35),
    ("PRECISION_SPEED_FACTOR", "Precision speed factor", float, 0.35),
    ("FAST_SPEED_FACTOR", "Fast speed factor", float, 1.6),
    ("MOUSE_MOVE_ENABLE_BUTTON_INDEX", "Mouse move enable button index", int, None),
    ("HAT_SELECT_ENABLED", "Hat select enabled", bool, True),
    ("CLICK_HOLD_THRESHOLD", "Click hold threshold", float, 0.12),
    ("CLICK_MOVE_THRESHOLD", "Click move threshold", int, 4),
    ("USE_CLOCK", "Use clock", bool, True),
    ("TARGET_FPS", "Target FPS", int, 100),
]


class SettingsEditor:
    def __init__(self, config_path: str | None = None) -> None:
        self.config_path = config_path or str(CONFIG_PATH)
        self.settings = load_settings(self.config_path)
        self.root = tk.Tk()
        self.root.title("StickNav Settings")
        self.root.geometry("640x620")
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        self.variables: Dict[str, Any] = {}
        self.active_field: str | None = None
        self.pending_capture_field: str | None = None
        self._keyboard_listener: Any | None = None
        self._mouse_listener: Any | None = None
        self.status_var = tk.StringVar(value="Select a setting and use Capture to assign controller input.")
        self._build_ui()
        self.hide()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Adjust StickNav settings and save them to a JSON file.", wraplength=600).pack(anchor="w", pady=(0, 12))

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable = ttk.Frame(canvas)

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for index, (name, label, kind, default) in enumerate(FIELD_DEFINITIONS):
            row = ttk.Frame(scrollable, padding=(0, 4))
            row.grid(row=index // 1, column=0, sticky="ew")
            row.columnconfigure(1, weight=1)

            ttk.Label(row, text=label).grid(row=0, column=0, sticky="w", padx=(0, 8))

            if kind is bool:
                variable = tk.BooleanVar(value=bool(self.settings.get(name, default)))
                checkbutton = ttk.Checkbutton(row, variable=variable)
                checkbutton.grid(row=0, column=1, sticky="w")
                checkbutton.bind("<FocusIn>", lambda _event, field_name=name: self._set_active_field(field_name))
            else:
                initial = self.settings.get(name, default)
                if initial is None:
                    initial_text = ""
                else:
                    initial_text = self._format_setting_value(name, initial)
                variable = tk.StringVar(value=initial_text)
                entry = ttk.Entry(row, textvariable=variable)
                entry.grid(row=0, column=1, sticky="ew")
                entry.bind("<FocusIn>", lambda _event, field_name=name: self._set_active_field(field_name))

            if name.endswith("_BUTTON_INDEX") or name.endswith("_AXIS_INDEX"):
                capture_button = ttk.Button(row, text="Capture", command=lambda field_name=name: self.start_capture(field_name))
                capture_button.grid(row=0, column=2, padx=(6, 0))

            self.variables[name] = variable

        self._bind_variable_updates()

        actions = ttk.Frame(container, padding=(0, 8))
        actions.pack(fill="x")
        ttk.Label(actions, textvariable=self.status_var).pack(side="left")
        ttk.Button(actions, text="Save", command=self.on_save).pack(side="right")

    def _format_setting_value(self, field_name: str, value: Any) -> str:
        if isinstance(value, str):
            return value
        if field_name in BUTTON_FIELD_NAMES:
            if isinstance(value, (int, float)):
                return str(int(value))
            return str(value)
        return str(value)

    def _coerce_value(self, variable: Any, kind: type, default: Any) -> Any:
        if kind is bool:
            return bool(variable.get())

        raw_value = str(variable.get()).strip()
        if raw_value == "" and kind in {int, float}:
            return None
        if kind is int:
            normalized = raw_value.upper()
            if normalized in {"LT", "LEFT_TRIGGER", "LEFTTRIGGER"}:
                return "LT"
            if normalized in {"RT", "RIGHT_TRIGGER", "RIGHTTRIGGER"}:
                return "RT"
            if normalized.startswith("KEY_") or normalized.startswith("MOUSE_"):
                return raw_value
            return int(float(raw_value))
        if kind is float:
            return float(raw_value)
        return raw_value

    def _apply_settings(self, persist: bool = True) -> bool:
        try:
            updated_settings: Dict[str, Any] = {}
            for name, _, kind, default in FIELD_DEFINITIONS:
                value = self._coerce_value(self.variables[name], kind, default)
                updated_settings[name] = value
        except (ValueError, AttributeError):
            return False

        self.settings.update(updated_settings)
        if persist:
            save_settings(self.config_path, self.settings)
        return True

    def _bind_variable_updates(self) -> None:
        for name in self.variables:
            self.variables[name].trace_add("write", lambda *_args, name=name: self._apply_settings(persist=False))

    def _set_active_field(self, field_name: str) -> None:
        self.active_field = field_name

    def start_capture(self, field_name: str) -> None:
        self.pending_capture_field = field_name
        self._start_capture_listeners()
        label = next((label for name, label, _, _ in FIELD_DEFINITIONS if name == field_name), field_name)
        self.status_var.set(f"Waiting for input for {label}...")

    def clear_capture(self) -> None:
        self.pending_capture_field = None
        self._stop_capture_listeners()
        if getattr(self, "status_var", None) is not None:
            self.status_var.set("Select a setting and use Capture to assign controller input.")

    def capture_controller_input(self, value: Any) -> None:
        if self.pending_capture_field is None:
            return

        variable = self.variables[self.pending_capture_field]
        variable.set(str(value))
        self.clear_capture()

    def _start_capture_listeners(self) -> None:
        self._stop_capture_listeners()
        if pynput_keyboard is None or pynput_mouse is None:
            self.status_var.set("Keyboard and mouse capture requires the pynput package.")
            return

        self._keyboard_listener = pynput_keyboard.Listener(on_press=self._handle_key_press)
        self._mouse_listener = pynput_mouse.Listener(on_click=self._handle_mouse_click)
        self._keyboard_listener.start()
        self._mouse_listener.start()

    def _stop_capture_listeners(self) -> None:
        keyboard_listener = getattr(self, "_keyboard_listener", None)
        mouse_listener = getattr(self, "_mouse_listener", None)
        for listener in (keyboard_listener, mouse_listener):
            if listener is None:
                continue
            try:
                listener.stop()
            except Exception:
                pass
        self._keyboard_listener = None
        self._mouse_listener = None

    def _handle_key_press(self, key: Any) -> None:
        if self.pending_capture_field is None:
            return
        self.root.after(0, self._apply_captured_key, key)

    def _apply_captured_key(self, key: Any) -> None:
        if self.pending_capture_field is None:
            return
        value = self._normalize_key_capture(key)
        if value is None:
            return
        self.capture_controller_input(value)

    def _normalize_key_capture(self, key: Any) -> str | None:
        if hasattr(key, "char") and key.char is not None:
            char = key.char
            if char == " ":
                return "KEY_SPACE"
            if char in {"\n", "\r"}:
                return "KEY_ENTER"
            return f"KEY_{char.upper()}"

        name = str(key).replace("Key.", "").replace("'", "").lower()
        return SPECIAL_KEY_NAMES.get(name)

    def _handle_mouse_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        if not pressed or self.pending_capture_field is None:
            return
        button_name = getattr(button, "name", None) or str(button).split(".")[-1]
        self.root.after(0, self.capture_controller_input, f"MOUSE_{button_name.upper()}")

    def is_capturing(self) -> bool:
        return self.pending_capture_field is not None

    def is_visible(self) -> bool:
        try:
            return bool(self.root.winfo_viewable())
        except tk.TclError:
            return False

    def handle_controller_buttons(self, lb_pressed: bool, rb_pressed: bool) -> None:
        if not self.is_visible() or self.active_field is None:
            return

        field_name = self.active_field
        kind = next((kind for name, _, kind, _ in FIELD_DEFINITIONS if name == field_name), None)
        if kind not in {int, float}:
            return

        if lb_pressed and not rb_pressed:
            delta = -0.5 if kind is float else -1
        elif rb_pressed and not lb_pressed:
            delta = 0.5 if kind is float else 1
        else:
            return

        variable = self.variables[field_name]
        current_value = self._coerce_value(variable, kind, None)
        if current_value is None:
            current_value = 0
        next_value = current_value + delta
        if kind is int:
            next_value = int(next_value)
        else:
            next_value = float(next_value)
        variable.set(str(next_value))

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self) -> None:
        self._apply_settings(persist=True)
        self.clear_capture()
        self.root.withdraw()

    def toggle_window(self) -> None:
        self.root.after(0, self._toggle_window)

    def _toggle_window(self) -> None:
        if self.root.winfo_viewable():
            self.hide()
        else:
            self.show()

    def on_save(self) -> None:
        if self._apply_settings(persist=True):
            messagebox.showinfo("Saved", f"Settings saved to {self.config_path}")
        else:
            messagebox.showerror("Invalid value", "One of the values is invalid.")

    def run(self) -> None:
        self.root.mainloop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Edit StickNav settings")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to the JSON settings file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    editor = SettingsEditor(args.config)
    editor.run()


if __name__ == "__main__":
    main()
