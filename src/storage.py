r"""
Personal Config, Profiles & Windows Startup Persistence
Stores data in %LOCALAPPDATA%\AulaS75Controller\config.json for personal desktop use.
"""

from __future__ import annotations
import json
import os
import sys
import winreg
from typing import Any, Dict, List

APP_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "AulaS75Controller",
)
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "AulaS75Controller"

DEFAULT_PROFILES: List[Dict[str, Any]] = [
    {
        "name": "Cam Tĩnh (Orange Studio)",
        "kind": "global",
        "mode": 1,
        "r": 255,
        "g": 106,
        "b": 0,
        "brightness": 5,
        "speed": 3,
        "direction": 0,
        "colorful": 0,
        "side_mode": 32,
    },
    {
        "name": "Cyberpunk Cyan",
        "kind": "global",
        "mode": 1,
        "r": 0,
        "g": 229,
        "b": 255,
        "brightness": 5,
        "speed": 3,
        "direction": 0,
        "colorful": 0,
        "side_mode": 34,
    },
    {
        "name": "Sóng Cầu Vồng (Rainbow Wave)",
        "kind": "global",
        "mode": 11,
        "r": 0,
        "g": 229,
        "b": 255,
        "brightness": 5,
        "speed": 3,
        "direction": 0,
        "colorful": 1,
        "side_mode": 32,
    },
    {
        "name": "Coding Đêm (Dịu mắt)",
        "kind": "global",
        "mode": 7,
        "r": 64,
        "g": 156,
        "b": 255,
        "brightness": 3,
        "speed": 2,
        "direction": 0,
        "colorful": 0,
        "side_mode": 35,
    },
    {
        "name": "Tắt Đèn (Stealth)",
        "kind": "global",
        "mode": 20,
        "r": 0,
        "g": 0,
        "b": 0,
        "brightness": 1,
        "speed": 3,
        "direction": 0,
        "colorful": 0,
        "side_mode": 36,
    },
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "last_state": {
        "mode": 1,
        "r": 255,
        "g": 106,
        "b": 0,
        "brightness": 5,
        "speed": 3,
        "direction": 0,
        "colorful": 0,
        "side_mode": 32,
    },
    "per_key_colors": {},  # str(light_index) -> [r, g, b]
    "profiles": DEFAULT_PROFILES,
    "keyboard_settings": {
        "disable_win": False,
        "disable_alttab": False,
        "disable_altf4": False,
        "fn_switch": False,
        "sleep_time": 1,       # 0=Off, 1=1m, 2=3m, 3=5m, 4=10m, 5=30m
        "key_respondtime": 2,  # 1..5 debounce level
    },
    "app_settings": {
        "auto_apply_sliders": True,
        "apply_on_startup": True,
        "minimize_to_tray": True,
    },
}


def load_config() -> Dict[str, Any]:
    os.makedirs(APP_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return json.loads(json.dumps(DEFAULT_CONFIG))

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return json.loads(json.dumps(DEFAULT_CONFIG))

    # Merge missing keys gracefully
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k].update(v)
        else:
            merged[k] = v
    return merged


def save_config(cfg: Dict[str, Any]) -> None:
    os.makedirs(APP_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled: bool) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                if getattr(sys, "frozen", False):
                    cmd = f'"{sys.executable}" --minimized'
                else:
                    main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
                    pyw = sys.executable.replace("python.exe", "pythonw.exe")
                    if not os.path.exists(pyw):
                        pyw = sys.executable
                    cmd = f'"{pyw}" "{main_script}" --minimized'
                winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False
