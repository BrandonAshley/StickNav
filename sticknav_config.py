import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG_PATH = Path(__file__).with_name("sticknav_settings.json")


def default_settings() -> Dict[str, Any]:
    return {
        "DEAD_ZONE": 0.22,
        "RIGHT_STICK_DEAD_ZONE": 0.18,
        "SCROLL_STEP": 30,
        "BASE_SPEED": 3.0,
        "MAX_SPEED": 20.0,
        "ACCELERATION": 10.0,
        "SENSITIVITY_CURVE": 1.35,
        "LEFT_CLICK_BUTTON_INDEX": 0,
        "RIGHT_CLICK_BUTTON_INDEX": 1,
        "X_BUTTON_INDEX": 2,
        "Y_BUTTON_INDEX": 3,
        "LB_BUTTON_INDEX": 4,
        "RB_BUTTON_INDEX": 5,
        "SELECT_BUTTON_INDEX": None,
        "L3_BUTTON_INDEX": None,
        "R3_BUTTON_INDEX": None,
        "DPAD_UP_BUTTON_INDEX": None,
        "DPAD_DOWN_BUTTON_INDEX": None,
        "DPAD_LEFT_BUTTON_INDEX": None,
        "DPAD_RIGHT_BUTTON_INDEX": None,
        "LT_AXIS_INDEX": 4,
        "RT_AXIS_INDEX": 5,
        "TRIGGER_DEAD_ZONE": 0.35,
        "PRECISION_SPEED_FACTOR": 0.35,
        "FAST_SPEED_FACTOR": 1.6,
        "MOUSE_MOVE_ENABLE_BUTTON_INDEX": None,
        "HAT_SELECT_ENABLED": True,
        "CLICK_HOLD_THRESHOLD": 0.12,
        "CLICK_MOVE_THRESHOLD": 4,
        "USE_CLOCK": True,
        "TARGET_FPS": 100,
    }


def resolve_config_path(path: str | Path | None = None) -> Path:
    if path is None:
        return DEFAULT_CONFIG_PATH
    if isinstance(path, Path):
        return path
    return Path(path)


def load_settings(path: str | Path | None = None) -> Dict[str, Any]:
    settings = default_settings()
    config_path = resolve_config_path(path)

    if not config_path.exists():
        return settings

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return settings

    if isinstance(loaded, dict):
        settings.update(loaded)

    return settings


def save_settings(path: str | Path | None, settings: Dict[str, Any]) -> Path:
    config_path = resolve_config_path(path)
    config_path.write_text(json.dumps(settings, indent=2, sort_keys=True), encoding="utf-8")
    return config_path


CONFIG_PATH = DEFAULT_CONFIG_PATH
