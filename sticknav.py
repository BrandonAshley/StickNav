import argparse
import ctypes
import ctypes.wintypes
import math
import threading
import time
from pathlib import Path

import pygame

from sticknav_config import CONFIG_PATH, load_settings, save_settings


# --- Mouse control via Win32 API (low latency) ---
user32 = ctypes.windll.user32


def get_cursor_pos():
    pt = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def move_cursor(dx, dy):
    x, y = get_cursor_pos()
    user32.SetCursorPos(int(x + dx), int(y + dy))


def press_button(button="left"):
    if button == "left":
        user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
    elif button == "right":
        user32.mouse_event(0x0008, 0, 0, 0, 0)  # RIGHTDOWN
    elif button == "middle":
        user32.mouse_event(0x0020, 0, 0, 0, 0)  # MIDDLEDOWN


def release_button(button="left"):
    if button == "left":
        user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
    elif button == "right":
        user32.mouse_event(0x0010, 0, 0, 0, 0)  # RIGHTUP
    elif button == "middle":
        user32.mouse_event(0x0040, 0, 0, 0, 0)  # MIDDLEUP


def click(button="left"):
    press_button(button)
    release_button(button)


def scroll_wheel(delta_y=0, delta_x=0):
    if delta_y != 0:
        user32.mouse_event(0x0800, 0, 0, int(delta_y), 0)  # vertical wheel
    if delta_x != 0:
        user32.mouse_event(0x01000, 0, 0, int(delta_x), 0)  # horizontal wheel


# Key mapping for D-pad selection navigation
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002


def press_key(vk):
    user32.keybd_event(vk, 0, 0, 0)


def release_key(vk):
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def send_virtual_key(vk, pressed):
    flags = 0x0001 if vk in {0x12, 0x5B, 0x5C} else 0
    if not pressed:
        flags |= KEYEVENTF_KEYUP
    user32.keybd_event(vk, 0, flags, 0)


def resolve_axis_index(value, default_index):
    if value is None:
        return default_index
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in {"LT", "LEFT_TRIGGER", "LEFTTRIGGER"}:
            return 4
        if normalized in {"RT", "RIGHT_TRIGGER", "RIGHTTRIGGER"}:
            return 5
        try:
            return int(normalized)
        except ValueError:
            return default_index
    return int(value)


BUTTON_INDEX_BY_FIELD = {
    "LEFT_CLICK_BUTTON_INDEX": 0,
    "RIGHT_CLICK_BUTTON_INDEX": 1,
    "X_BUTTON_INDEX": 2,
    "Y_BUTTON_INDEX": 3,
    "LB_BUTTON_INDEX": 4,
    "RB_BUTTON_INDEX": 5,
    "SELECT_BUTTON_INDEX": 6,
    "L3_BUTTON_INDEX": 8,
    "R3_BUTTON_INDEX": 9,
    "DPAD_UP_BUTTON_INDEX": None,
    "DPAD_DOWN_BUTTON_INDEX": None,
    "DPAD_LEFT_BUTTON_INDEX": None,
    "DPAD_RIGHT_BUTTON_INDEX": None,
}


def resolve_button_input_index(field_name, configured_value, default_index):
    if isinstance(configured_value, str) and configured_value.strip():
        normalized = configured_value.strip()
        try:
            return int(normalized)
        except ValueError:
            return BUTTON_INDEX_BY_FIELD.get(field_name, default_index)
    if isinstance(configured_value, (int, float)):
        return int(configured_value)
    if configured_value is None:
        return None
    return BUTTON_INDEX_BY_FIELD.get(field_name, default_index)


def resolve_button_action(field_name, configured_value):
    if isinstance(configured_value, str) and configured_value.strip():
        normalized = configured_value.strip().upper()
        if normalized.startswith("KEY_") or normalized.startswith("MOUSE_"):
            return normalized
    if field_name == "LEFT_CLICK_BUTTON_INDEX":
        return "MOUSE_LEFT"
    if field_name == "RIGHT_CLICK_BUTTON_INDEX":
        return "MOUSE_RIGHT"
    if field_name == "X_BUTTON_INDEX":
        return "MOUSE_MIDDLE"
    if field_name == "Y_BUTTON_INDEX":
        return "KEY_RETURN"
    return None


def resolve_vk_name(name):
    if not isinstance(name, str):
        return None
    normalized = name.strip().upper()
    if normalized in {"SHIFT", "LEFTSHIFT", "RIGHTSHIFT"}:
        return 0x10
    if normalized in {"CTRL", "LEFTCTRL", "RIGHTCTRL"}:
        return 0x11
    if normalized in {"ALT", "LEFTALT", "RIGHTALT", "ALTGR"}:
        return 0x12
    if normalized in {"TAB", "ENTER", "BACKSPACE", "ESCAPE", "SPACE", "UP", "DOWN", "LEFT", "RIGHT"}:
        return {
            "TAB": 0x09,
            "ENTER": 0x0D,
            "BACKSPACE": 0x08,
            "ESCAPE": 0x1B,
            "SPACE": 0x20,
            "UP": 0x26,
            "DOWN": 0x28,
            "LEFT": 0x25,
            "RIGHT": 0x27,
        }[normalized]
    if normalized in {"WIN", "WINDOWS", "LEFTWINDOWS", "SUPER", "LEFTSUPER", "META", "LEFTMETA", "CMD", "LEFTCMD"}:
        return 0x5B
    if normalized in {"RIGHTWIN", "RIGHTWINDOWS", "RIGHTSUPER", "RIGHTMETA", "RIGHTCMD"}:
        return 0x5C
    if len(normalized) == 1:
        return ord(normalized)
    return None


def press_named_key(name):
    vk = resolve_vk_name(name)
    if vk is None:
        return
    send_virtual_key(vk, True)


def release_named_key(name):
    vk = resolve_vk_name(name)
    if vk is None:
        return
    send_virtual_key(vk, False)


def trigger_action(action, pressed):
    if action is None:
        return
    normalized = action.strip().upper()
    if normalized.startswith("MOUSE_"):
        button_name = normalized[6:].lower()
        if pressed:
            press_button(button_name)
        else:
            release_button(button_name)
    elif normalized.startswith("KEY_"):
        key_name = normalized[4:]
        if pressed:
            press_named_key(key_name)
        else:
            release_named_key(key_name)


def apply_button_actions(settings, joystick, button_states, settings_editor=None, hat_state=None):
    for field_name in ("LEFT_CLICK_BUTTON_INDEX", "RIGHT_CLICK_BUTTON_INDEX", "X_BUTTON_INDEX", "Y_BUTTON_INDEX", "LB_BUTTON_INDEX", "RB_BUTTON_INDEX", "SELECT_BUTTON_INDEX", "L3_BUTTON_INDEX", "R3_BUTTON_INDEX"):
        configured_value = settings.get(field_name, BUTTON_INDEX_BY_FIELD[field_name])
        button_index = resolve_button_input_index(field_name, configured_value, BUTTON_INDEX_BY_FIELD[field_name])
        if button_index is None:
            continue

        pressed = bool(joystick.get_button(button_index))
        action = resolve_button_action(field_name, configured_value)
        if action is None:
            continue

        if pressed and not button_states[field_name]:
            trigger_action(action, True)
            button_states[field_name] = True
        elif not pressed and button_states[field_name]:
            trigger_action(action, False)
            button_states[field_name] = False

    if hat_state is None and hasattr(joystick, "get_hat"):
        hat_state = joystick.get_hat(0)

    dpad_fields = {
        "DPAD_UP_BUTTON_INDEX": hat_state[1] > 0 if hat_state is not None else False,
        "DPAD_DOWN_BUTTON_INDEX": hat_state[1] < 0 if hat_state is not None else False,
        "DPAD_LEFT_BUTTON_INDEX": hat_state[0] < 0 if hat_state is not None else False,
        "DPAD_RIGHT_BUTTON_INDEX": hat_state[0] > 0 if hat_state is not None else False,
    }
    for field_name, pressed in dpad_fields.items():
        configured_value = settings.get(field_name, None)
        action = resolve_button_action(field_name, configured_value)
        if action is None:
            continue

        if pressed and not button_states[field_name]:
            trigger_action(action, True)
            button_states[field_name] = True
        elif not pressed and button_states[field_name]:
            trigger_action(action, False)
            button_states[field_name] = False


def run_controller(settings, config_path=None, settings_editor=None):
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        raise RuntimeError("No controller detected.")

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Using controller: {joystick.get_name()}")

    clock = pygame.time.Clock()
    left_pressed = False
    right_pressed = False
    left_click_start = 0.0
    left_click_start_pos = None
    left_click_dragging = False
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
    hold_time_x = 0.0
    hold_time_y = 0.0
    last_dir_x = 0
    last_dir_y = 0
    last_time = time.perf_counter()
    prev_hat = (0, 0)
    x_was_pressed = False
    y_was_pressed = False
    lb_held = False
    rb_held = False
    lb_step_held = False
    rb_step_held = False
    start_was_pressed = False
    capture_button_states = []
    capture_lt_held = False
    capture_rt_held = False

    try:
        while True:
            if config_path is not None:
                settings.update(load_settings(config_path))

            pygame.event.pump()

            if bool(settings.get("USE_CLOCK", True)):
                dt = clock.tick(int(settings.get("TARGET_FPS", 100))) / 1000.0
            else:
                now = time.perf_counter()
                dt = now - last_time
                last_time = now
                time.sleep(0.016)

            x_axis = joystick.get_axis(0)
            y_axis = joystick.get_axis(1)

            dead_zone = float(settings.get("DEAD_ZONE", 0.22))
            if abs(x_axis) < dead_zone:
                x_axis = 0
            if abs(y_axis) < dead_zone:
                y_axis = 0

            right_x = joystick.get_axis(2)
            right_y = joystick.get_axis(3)
            right_stick_dead_zone = float(settings.get("RIGHT_STICK_DEAD_ZONE", 0.18))
            if abs(right_x) < right_stick_dead_zone:
                right_x = 0
            if abs(right_y) < right_stick_dead_zone:
                right_y = 0

            mouse_move_enabled_value = settings.get("MOUSE_MOVE_ENABLE_BUTTON_INDEX")
            mouse_move_enabled = True if mouse_move_enabled_value is None else bool(
                joystick.get_button(
                    resolve_button_input_index("MOUSE_MOVE_ENABLE_BUTTON_INDEX", mouse_move_enabled_value, 0)
                )
            )

            if bool(settings.get("HAT_SELECT_ENABLED", True)) and joystick.get_numhats() > 0:
                hat = joystick.get_hat(0)
            else:
                hat = (0, 0)

            lt_axis_index = resolve_axis_index(settings.get("LT_AXIS_INDEX", 4), 4)
            rt_axis_index = resolve_axis_index(settings.get("RT_AXIS_INDEX", 5), 5)
            lt_axis = joystick.get_axis(lt_axis_index) if joystick.get_numaxes() > lt_axis_index else -1
            rt_axis = joystick.get_axis(rt_axis_index) if joystick.get_numaxes() > rt_axis_index else -1
            lt_value = max(0.0, min(1.0, (lt_axis + 1) / 2))
            rt_value = max(0.0, min(1.0, (rt_axis + 1) / 2))

            if right_x != 0:
                scroll_wheel(delta_x=int(math.copysign(min(int(settings.get("SCROLL_STEP", 30)), abs(right_x) * int(settings.get("SCROLL_STEP", 30))), right_x)))
            if right_y != 0:
                scroll_wheel(delta_y=int(math.copysign(min(int(settings.get("SCROLL_STEP", 30)), abs(right_y) * int(settings.get("SCROLL_STEP", 30))), -right_y)))

            lb_button_index = resolve_button_input_index("LB_BUTTON_INDEX", settings.get("LB_BUTTON_INDEX", 4), 4)
            rb_button_index = resolve_button_input_index("RB_BUTTON_INDEX", settings.get("RB_BUTTON_INDEX", 5), 5)
            lb_pressed = bool(joystick.get_button(lb_button_index))
            rb_pressed = bool(joystick.get_button(rb_button_index))
            if settings_editor is not None and settings_editor.is_visible():
                if settings_editor.is_capturing():
                    pass
                else:
                    if lb_pressed and not lb_step_held:
                        settings_editor.handle_controller_buttons(True, False)
                        lb_step_held = True
                    elif not lb_pressed and lb_step_held:
                        lb_step_held = False

                    if rb_pressed and not rb_step_held:
                        settings_editor.handle_controller_buttons(False, True)
                        rb_step_held = True
                    elif not rb_pressed and rb_step_held:
                        rb_step_held = False
            else:
                if lb_pressed and not lb_held:
                    scroll_wheel(delta_x=-int(settings.get("SCROLL_STEP", 30)))
                    lb_held = True
                elif not lb_pressed and lb_held:
                    lb_held = False

                if rb_pressed and not rb_held:
                    scroll_wheel(delta_x=int(settings.get("SCROLL_STEP", 30)))
                    rb_held = True
                elif not rb_pressed and rb_held:
                    rb_held = False

            if bool(settings.get("HAT_SELECT_ENABLED", True)):
                if hat != prev_hat:
                    if prev_hat[0] < 0:
                        release_key(VK_LEFT)
                    elif prev_hat[0] > 0:
                        release_key(VK_RIGHT)
                    if prev_hat[1] < 0:
                        release_key(VK_DOWN)
                    elif prev_hat[1] > 0:
                        release_key(VK_UP)

                    if hat[0] < 0:
                        press_key(VK_LEFT)
                    elif hat[0] > 0:
                        press_key(VK_RIGHT)
                    if hat[1] < 0:
                        press_key(VK_DOWN)
                    elif hat[1] > 0:
                        press_key(VK_UP)

                    prev_hat = hat

            if mouse_move_enabled:
                if x_axis != 0:
                    current_dir_x = 1 if x_axis > 0 else -1
                    if current_dir_x == last_dir_x:
                        hold_time_x += dt
                    else:
                        hold_time_x = 0.0
                        last_dir_x = current_dir_x
                    speed_x = min(float(settings.get("MAX_SPEED", 20.0)), float(settings.get("BASE_SPEED", 3.0)) + hold_time_x * float(settings.get("ACCELERATION", 10.0)))
                    dx = math.copysign(abs(x_axis) ** float(settings.get("SENSITIVITY_CURVE", 1.35)), x_axis) * speed_x
                else:
                    hold_time_x = 0.0
                    last_dir_x = 0
                    dx = 0

                if y_axis != 0:
                    current_dir_y = 1 if y_axis > 0 else -1
                    if current_dir_y == last_dir_y:
                        hold_time_y += dt
                    else:
                        hold_time_y = 0.0
                        last_dir_y = current_dir_y
                    speed_y = min(float(settings.get("MAX_SPEED", 20.0)), float(settings.get("BASE_SPEED", 3.0)) + hold_time_y * float(settings.get("ACCELERATION", 10.0)))
                    dy = math.copysign(abs(y_axis) ** float(settings.get("SENSITIVITY_CURVE", 1.35)), y_axis) * speed_y
                else:
                    hold_time_y = 0.0
                    last_dir_y = 0
                    dy = 0
            else:
                dx = 0
                dy = 0
                hold_time_x = 0.0
                hold_time_y = 0.0
                last_dir_x = 0
                last_dir_y = 0

            if dx != 0 or dy != 0:
                speed_modifier = 1.0
                if float(settings.get("TRIGGER_DEAD_ZONE", 0.35)) < 0.0:
                    speed_modifier = 1.0
                elif lt_value > float(settings.get("TRIGGER_DEAD_ZONE", 0.35)) and rt_value <= float(settings.get("TRIGGER_DEAD_ZONE", 0.35)):
                    speed_modifier = float(settings.get("PRECISION_SPEED_FACTOR", 0.35))
                elif rt_value > float(settings.get("TRIGGER_DEAD_ZONE", 0.35)) and lt_value <= float(settings.get("TRIGGER_DEAD_ZONE", 0.35)):
                    speed_modifier = float(settings.get("FAST_SPEED_FACTOR", 1.6))
                dx *= speed_modifier
                dy *= speed_modifier
                move_cursor(dx, dy)

            start_pressed = bool(joystick.get_button(7))
            if start_pressed and not start_was_pressed and settings_editor is not None:
                settings_editor.toggle_window()
            start_was_pressed = start_pressed

            if not (settings_editor is not None and settings_editor.is_visible() and settings_editor.is_capturing()):
                apply_button_actions(settings, joystick, button_states, settings_editor, hat)
    except KeyboardInterrupt:
        pygame.quit()


def parse_args():
    parser = argparse.ArgumentParser(description="Run StickNav or edit its settings")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to the JSON settings file")
    parser.add_argument("--gui", action="store_true", help="Open the settings editor GUI")
    parser.add_argument("--no-gui", dest="gui", action="store_false", help="Disable the settings editor GUI")
    parser.set_defaults(gui=True)
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = Path(args.config)
    settings = load_settings(config_path)
    if not config_path.exists():
        save_settings(config_path, settings)

    if args.gui:
        from settings_gui import SettingsEditor

        editor = SettingsEditor(str(config_path))
        controller_thread = threading.Thread(
            target=run_controller,
            args=(editor.settings,),
            kwargs={"config_path": str(config_path), "settings_editor": editor},
            daemon=True,
        )
        controller_thread.start()
        editor.run()
    else:
        run_controller(settings, config_path=config_path)


if __name__ == "__main__":
    main()
