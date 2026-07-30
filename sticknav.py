import math
import pygame
import ctypes
import ctypes.wintypes
import time

# --- Setup ---
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    raise RuntimeError("No controller detected.")

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Using controller: {joystick.get_name()}")

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

# --- Config ---
DEAD_ZONE = 0.22
RIGHT_STICK_DEAD_ZONE = 0.18
SCROLL_STEP = 30
BASE_SPEED = 3.0  # starting cursor speed while holding the stick
MAX_SPEED = 20.0  # cap so it does not become too fast
ACCELERATION = 10.0  # speed increase per second while holding the stick
SENSITIVITY_CURVE = 1.35  # makes small stick inputs gentler
LEFT_CLICK_BUTTON_INDEX = 0  # A = left click
RIGHT_CLICK_BUTTON_INDEX = 1  # B = right click
X_BUTTON_INDEX = 2  # X = middle click
Y_BUTTON_INDEX = 3  # Y = Enter / confirm
LB_BUTTON_INDEX = 4  # LB = scroll left / nav left
RB_BUTTON_INDEX = 5  # RB = scroll right / nav right
LT_AXIS_INDEX = 4  # LT trigger for precision mode (common Xbox mapping)
RT_AXIS_INDEX = 5  # RT trigger for fast mode (common Xbox mapping)
TRIGGER_DEAD_ZONE = 0.35
PRECISION_SPEED_FACTOR = 0.35
FAST_SPEED_FACTOR = 1.6
MOUSE_MOVE_ENABLE_BUTTON_INDEX = None  # set to a button index to require hold for left-stick mouse movement
HAT_SELECT_ENABLED = True  # use D-pad/hat for selection navigation
CLICK_HOLD_THRESHOLD = 0.12  # seconds before a press becomes a drag
CLICK_MOVE_THRESHOLD = 4  # pixels before a press becomes a drag
USE_CLOCK = True  # switch between pygame Clock and manual sleep
TARGET_FPS = 100  # desired loop rate when using Clock

# --- Main loop ---
clock = pygame.time.Clock()
left_pressed = False
right_pressed = False
left_click_start = 0.0
left_click_start_pos = None
left_click_dragging = False
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

try:
    while True:
        pygame.event.pump()

        if USE_CLOCK:
            dt = clock.tick(TARGET_FPS) / 1000.0
        else:
            now = time.perf_counter()
            dt = now - last_time
            last_time = now
            time.sleep(0.016)  # ~60Hz polling fallback

        x_axis = joystick.get_axis(0)  # left stick horizontal
        y_axis = joystick.get_axis(1)  # left stick vertical

        # Apply dead zone and soften small inputs
        if abs(x_axis) < DEAD_ZONE:
            x_axis = 0
        if abs(y_axis) < DEAD_ZONE:
            y_axis = 0

        right_x = joystick.get_axis(2)
        right_y = joystick.get_axis(3)
        mouse_move_enabled = True if MOUSE_MOVE_ENABLE_BUTTON_INDEX is None else joystick.get_button(MOUSE_MOVE_ENABLE_BUTTON_INDEX)

        if HAT_SELECT_ENABLED and joystick.get_numhats() > 0:
            hat = joystick.get_hat(0)
        else:
            hat = (0, 0)

        lt_axis = joystick.get_axis(LT_AXIS_INDEX) if joystick.get_numaxes() > LT_AXIS_INDEX else -1
        rt_axis = joystick.get_axis(RT_AXIS_INDEX) if joystick.get_numaxes() > RT_AXIS_INDEX else -1
        lt_value = max(0.0, min(1.0, (lt_axis + 1) / 2))
        rt_value = max(0.0, min(1.0, (rt_axis + 1) / 2))

        if abs(right_x) < RIGHT_STICK_DEAD_ZONE:
            right_x = 0
        if abs(right_y) < RIGHT_STICK_DEAD_ZONE:
            right_y = 0

        if right_x != 0:
            scroll_wheel(delta_x=int(math.copysign(min(SCROLL_STEP, abs(right_x) * SCROLL_STEP), right_x)))
        if right_y != 0:
            scroll_wheel(delta_y=int(math.copysign(min(SCROLL_STEP, abs(right_y) * SCROLL_STEP), -right_y)))

        # LB/RB horizontal navigation
        lb_pressed = joystick.get_button(LB_BUTTON_INDEX)
        rb_pressed = joystick.get_button(RB_BUTTON_INDEX)
        if lb_pressed and not lb_held:
            scroll_wheel(delta_x=-SCROLL_STEP)
            lb_held = True
        elif not lb_pressed and lb_held:
            lb_held = False

        if rb_pressed and not rb_held:
            scroll_wheel(delta_x=SCROLL_STEP)
            rb_held = True
        elif not rb_pressed and rb_held:
            rb_held = False

        if HAT_SELECT_ENABLED:
            if hat != prev_hat:
                # release old hat keys
                if prev_hat[0] < 0:
                    release_key(VK_LEFT)
                elif prev_hat[0] > 0:
                    release_key(VK_RIGHT)
                if prev_hat[1] < 0:
                    release_key(VK_DOWN)
                elif prev_hat[1] > 0:
                    release_key(VK_UP)

                # press new hat keys
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
                speed_x = min(MAX_SPEED, BASE_SPEED + hold_time_x * ACCELERATION)
                dx = math.copysign(abs(x_axis) ** SENSITIVITY_CURVE, x_axis) * speed_x
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
                speed_y = min(MAX_SPEED, BASE_SPEED + hold_time_y * ACCELERATION)
                dy = math.copysign(abs(y_axis) ** SENSITIVITY_CURVE, y_axis) * speed_y
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
            if lt_value > TRIGGER_DEAD_ZONE and rt_value <= TRIGGER_DEAD_ZONE:
                speed_modifier = PRECISION_SPEED_FACTOR
            elif rt_value > TRIGGER_DEAD_ZONE and lt_value <= TRIGGER_DEAD_ZONE:
                speed_modifier = FAST_SPEED_FACTOR
            dx *= speed_modifier
            dy *= speed_modifier
            move_cursor(dx, dy)

        # Button click handling (B=left, A=right, X=middle, Y=enter)
        left_click_pressed = joystick.get_button(LEFT_CLICK_BUTTON_INDEX)
        right_click_pressed = joystick.get_button(RIGHT_CLICK_BUTTON_INDEX)
        x_pressed = joystick.get_button(X_BUTTON_INDEX)
        y_pressed = joystick.get_button(Y_BUTTON_INDEX)

        if left_click_pressed and not left_pressed:
            left_pressed = True
            left_click_start = time.perf_counter()
            left_click_start_pos = get_cursor_pos()
            left_click_dragging = False
            press_button("left")
        elif left_click_pressed and left_pressed and not left_click_dragging:
            elapsed = time.perf_counter() - left_click_start
            current_pos = get_cursor_pos()
            if elapsed >= CLICK_HOLD_THRESHOLD or (
                left_click_start_pos and
                (abs(current_pos[0] - left_click_start_pos[0]) > CLICK_MOVE_THRESHOLD or abs(current_pos[1] - left_click_start_pos[1]) > CLICK_MOVE_THRESHOLD)
            ):
                left_click_dragging = True
        elif not left_click_pressed and left_pressed:
            release_button("left")
            left_pressed = False
            left_click_start_pos = None
            left_click_dragging = False

        if right_click_pressed and not right_pressed:
            if left_pressed:
                release_button("left")
                left_pressed = False
                left_click_start_pos = None
                left_click_dragging = False
            press_button("right")
            right_pressed = True
        elif not right_click_pressed and right_pressed:
            release_button("right")
            right_pressed = False

        if x_pressed and not x_was_pressed:
            press_button("middle")
            release_button("middle")
            x_was_pressed = True
        elif not x_pressed and x_was_pressed:
            x_was_pressed = False

        if y_pressed and not y_was_pressed:
            press_key(VK_RETURN)
            release_key(VK_RETURN)
            y_was_pressed = True
        elif not y_pressed and y_was_pressed:
            y_was_pressed = False

        # Manual sleep is handled in the fallback branch above when USE_CLOCK is False.

except KeyboardInterrupt:
    pygame.quit()
    
    
