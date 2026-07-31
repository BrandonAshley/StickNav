import argparse
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Tuple

from sticknav_config import CONFIG_PATH, load_settings, save_settings

FIELD_DEFINITIONS: List[Tuple[str, str, type, Any]] = [
    ("DEAD_ZONE", "Dead zone", float, 0.22),
    ("RIGHT_STICK_DEAD_ZONE", "Right stick dead zone", float, 0.18),
    ("SCROLL_STEP", "Scroll step", int, 30),
    ("BASE_SPEED", "Base speed", float, 3.0),
    ("MAX_SPEED", "Max speed", float, 20.0),
    ("ACCELERATION", "Acceleration", float, 10.0),
    ("SENSITIVITY_CURVE", "Sensitivity curve", float, 1.35),
    ("LEFT_CLICK_BUTTON_INDEX", "Left click button index", int, 0),
    ("RIGHT_CLICK_BUTTON_INDEX", "Right click button index", int, 1),
    ("X_BUTTON_INDEX", "X button index", int, 2),
    ("Y_BUTTON_INDEX", "Y button index", int, 3),
    ("LB_BUTTON_INDEX", "LB button index", int, 4),
    ("RB_BUTTON_INDEX", "RB button index", int, 5),
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
                    initial_text = str(initial)
                variable = tk.StringVar(value=initial_text)
                entry = ttk.Entry(row, textvariable=variable)
                entry.grid(row=0, column=1, sticky="ew")
                entry.bind("<FocusIn>", lambda _event, field_name=name: self._set_active_field(field_name))

            self.variables[name] = variable

        self._bind_variable_updates()

        actions = ttk.Frame(container, padding=(0, 8))
        actions.pack(fill="x")
        ttk.Button(actions, text="Save", command=self.on_save).pack(side="right")

    def _coerce_value(self, variable: Any, kind: type, default: Any) -> Any:
        if kind is bool:
            return bool(variable.get())

        raw_value = variable.get().strip()
        if raw_value == "" and kind in {int, float}:
            return None
        if kind is int:
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
            self.variables[name].trace_add("write", lambda *_args, name=name: self._apply_settings(persist=True))

    def _set_active_field(self, field_name: str) -> None:
        self.active_field = field_name

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
