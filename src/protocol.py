"""
AULA S75 Pro USB HID Protocol & Thread-Safe Transport
Reverse-engineered from official S75Pro DeviceDriver.exe.

Hardware:
  - Wired USB: VID 0x0C45, PID 0x800A, Interface 3 (UsagePage 0xFF13, Usage 0x0001)
  - 2.4G Dongle: VID 0x0C45, PID 0xFEFE (detection supported)
"""

from __future__ import annotations
import datetime
import threading
import time
from typing import Callable, Dict, Iterable, List, Optional, Tuple
import hid

from .layout_data import ALL_LIGHT_INDICES

VENDOR_ID = 0x0C45
USB_PRODUCT_ID = 0x800A
DONGLE_PRODUCT_ID = 0xFEFE

CMD_DELAY_SEC = 0.035  # Official driver <cmd_delaytime value="35" />

# Mode metadata: id -> (English/Vietnamese display name, supports_color, supports_speed, supports_direction, supports_colorful, category)
LIGHT_MODE_SPECS: Dict[int, Dict] = {
    1:  {"name": "Static (Đơn sắc tĩnh)",        "color": True,  "speed": False, "dir": False, "colorful": False, "cat": "Cơ bản"},
    2:  {"name": "Single On (Sáng khi bấm)",      "color": True,  "speed": True,  "dir": False, "colorful": True,  "cat": "Tương tác"},
    3:  {"name": "Single Off (Tắt khi bấm)",      "color": True,  "speed": True,  "dir": False, "colorful": True,  "cat": "Tương tác"},
    4:  {"name": "Glittering (Lấp lánh)",         "color": True,  "speed": True,  "dir": False, "colorful": True,  "cat": "Chuyển động"},
    5:  {"name": "Fluttering (Bay bổng)",         "color": True,  "speed": True,  "dir": False, "colorful": True,  "cat": "Chuyển động"},
    6:  {"name": "Colourful (Đa sắc chuyển)",     "color": False, "speed": True,  "dir": False, "colorful": False, "cat": "Đa sắc"},
    7:  {"name": "Breathing (Nhịp thở)",          "color": True,  "speed": True,  "dir": False, "colorful": True,  "cat": "Cơ bản"},
    8:  {"name": "Spectrum (Cầu vồng 7 màu)",     "color": False, "speed": True,  "dir": False, "colorful": False, "cat": "Đa sắc"},
    9:  {"name": "Outward (Tỏa ra ngoài)",        "color": True,  "speed": True,  "dir": True,  "colorful": True,  "cat": "Sóng"},
    10: {"name": "Scrolling (Cuộn dòng)",         "color": True,  "speed": True,  "dir": True,  "colorful": True,  "cat": "Sóng"},
    11: {"name": "Rolling (Sóng lượn)",           "color": True,  "speed": True,  "dir": True,  "colorful": True,  "cat": "Sóng"},
    12: {"name": "Rotating (Xoay tròn)",          "color": True,  "speed": True,  "dir": True,  "colorful": True,  "cat": "Sóng"},
    13: {"name": "Explode (Bùng nổ khi bấm)",     "color": True,  "speed": True,  "dir": False, "colorful": True,  "cat": "Tương tác"},
    14: {"name": "Launch (Phóng tia khi bấm)",     "color": True,  "speed": True,  "dir": False, "colorful": True,  "cat": "Tương tác"},
    15: {"name": "Ripples (Gợn sóng khi bấm)",    "color": True,  "speed": True,  "dir": False, "colorful": True,  "cat": "Tương tác"},
    16: {"name": "Flowing (Dòng chảy)",           "color": True,  "speed": True,  "dir": True,  "colorful": True,  "cat": "Sóng"},
    17: {"name": "Pulsating (Nhịp đập)",          "color": True,  "speed": True,  "dir": False, "colorful": True,  "cat": "Chuyển động"},
    18: {"name": "Tilt (Nghiêng dòng)",           "color": True,  "speed": True,  "dir": True,  "colorful": True,  "cat": "Sóng"},
    19: {"name": "Shuttle (Thoi đưa)",            "color": True,  "speed": True,  "dir": False, "colorful": True,  "cat": "Chuyển động"},
    20: {"name": "LED Off (Tắt đèn)",             "color": False, "speed": False, "dir": False, "colorful": False, "cat": "Cơ bản"},
}

LIGHT_MODES: Dict[int, str] = {k: v["name"] for k, v in LIGHT_MODE_SPECS.items()}


def find_usb_config_path() -> Optional[bytes]:
    """Locate the vendor-defined HID config endpoint (Interface 3 / UsagePage 0xFF13)."""
    devices = hid.enumerate(VENDOR_ID, USB_PRODUCT_ID)
    if not devices:
        return None
    for d in devices:
        if d.get("interface_number") == 3 or d.get("usage_page") == 0xFF13:
            return d["path"]
    for d in devices:
        if d.get("usage_page", 0) >= 0xFF00 and d.get("interface_number") != 2:
            return d["path"]
    return devices[0]["path"]


def detect_connection_mode() -> Tuple[str, Optional[bytes]]:
    """Return ('USB', path), ('2.4G', path), or ('Disconnected', None)."""
    usb_path = find_usb_config_path()
    if usb_path:
        return ("USB", usb_path)
    dongle_devs = hid.enumerate(VENDOR_ID, DONGLE_PRODUCT_ID)
    if dongle_devs:
        for d in dongle_devs:
            if d.get("interface_number") == 3 or d.get("usage_page") == 0xFF13:
                return ("2.4G", d["path"])
        return ("2.4G", dongle_devs[0]["path"])
    return ("Disconnected", None)


def build_global_lighting_packet(
    mode: int,
    r: int,
    g: int,
    b: int,
    brightness: int = 5,
    speed: int = 3,
    direction: int = 0,
    colorful: int = 0,
) -> List[int]:
    """
    Build the 64-byte payload matching DeviceDriver.exe routine 0x42AFD0 / 0x42B030.
    Exact byte layout verified via disassembly:
      [0]     = mode (1..19, or 0 for LED Off)
      [1..3]  = R, G, B (0..255)
      [8]     = colorful (0 = single custom RGB, 1 = 7-color / rainbow)
      [9]     = brightness (1..5)
      [10]    = speed (1..5)
      [11]    = direction (0 = left->right, 1 = right->left)
      [14..15]= 0xAA, 0x55
    """
    actual_mode = 0 if mode == 20 else (mode & 0xFF)
    p = [0] * 64
    p[0] = actual_mode
    if actual_mode != 0:
        p[1] = max(0, min(255, int(r)))
        p[2] = max(0, min(255, int(g)))
        p[3] = max(0, min(255, int(b)))
        p[8] = 1 if colorful else 0
        p[9] = max(1, min(5, int(brightness)))
        p[10] = max(1, min(5, int(speed)))
        p[11] = 1 if direction else 0
    p[14] = 0xAA
    p[15] = 0x55
    return p


def build_per_key_table(key_colors: Dict[int, Tuple[int, int, int]], default_rgb=(0, 0, 0)) -> List[int]:
    """
    Build 576-byte per-key color table matching DeviceDriver.exe routine 0x44B900.
    Each entry at key_index * 4 is [light_index, R, G, B]. Tail [574..575] = [0xAA, 0x55].
    """
    table = [0] * 576
    for idx in ALL_LIGHT_INDICES:
        offset = idx * 4
        if offset + 3 < 574:
            r, g, b = key_colors.get(idx, default_rgb)
            table[offset] = idx & 0xFF
            table[offset + 1] = max(0, min(255, int(r)))
            table[offset + 2] = max(0, min(255, int(g)))
            table[offset + 3] = max(0, min(255, int(b)))
    table[574] = 0xAA
    table[575] = 0x55
    return table


def build_settings_packet(
    disable_win: bool = False,
    disable_alttab: bool = False,
    disable_altf4: bool = False,
    fn_switch: bool = False,
    sleep_time: int = 1,
    key_respondtime: int = 2,
) -> List[int]:
    """
    Build 64-byte payload matching DeviceDriver.exe routine 0x4141A0.
      [0..1]  = 0x00, 0x01
      [2]     = disable_win
      [3]     = disable_alttab
      [4]     = disable_altf4
      [5]     = fn_switch
      [6]     = sleep_time
      [8]     = key_respondtime (debounce level)
      [62..63]= 0xAA, 0x55
    """
    p = [0] * 64
    p[0] = 0x00
    p[1] = 0x01
    p[2] = 1 if disable_win else 0
    p[3] = 1 if disable_alttab else 0
    p[4] = 1 if disable_altf4 else 0
    p[5] = 1 if fn_switch else 0
    p[6] = max(0, min(255, int(sleep_time)))
    p[8] = max(0, min(255, int(key_respondtime)))
    p[62] = 0xAA
    p[63] = 0x55
    return p


def build_clock_sync_packet(now: Optional[datetime.datetime] = None) -> List[int]:
    """
    Build 64-byte payload matching DeviceDriver.exe routine 0x423A80 (Sync PC clock to keyboard LCD).
    """
    if now is None:
        now = datetime.datetime.now()
    p = [0] * 64
    p[0] = 1
    p[1] = 0x5A
    p[2] = now.year % 2000
    p[3] = now.month
    p[4] = now.day
    p[5] = now.hour
    p[6] = now.minute
    p[7] = now.second
    # Windows SYSTEMTIME wDayOfWeek: Sunday=0 .. Saturday=6
    p[9] = (now.weekday() + 1) % 7
    p[61] = 0xAA
    p[62] = 0x55
    return p


class KeyboardTransport:
    """
    Serialized, retry-capable USB HID transport for AULA S75 Pro.
    Prevents multi-thread HID collisions and verifies firmware ACKs (report[4] == 1).
    """

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self._lock = threading.RLock()
        self._log_cb = log_callback
        self.last_latency_ms: float = 0.0
        self.last_error: str = ""
        self.last_ack_ok: bool = False

    def _log(self, msg: str):
        if self._log_cb:
            try:
                self._log_cb(msg)
            except Exception:
                pass

    def _send_one_packet(
        self,
        dev: hid.device,
        payload: List[int],
        expect_ack: bool = False,
        delay: float = CMD_DELAY_SEC,
        retries: int = 3,
    ) -> bool:
        buf = (payload + [0] * 64)[:64]
        report = [0x00] + buf

        for attempt in range(1, retries + 1):
            try:
                written = dev.send_feature_report(report)
                if written < 0:
                    raise OSError(f"send_feature_report returned {written}")
                time.sleep(delay)

                if not expect_ack:
                    return True

                # Poll feature report if MCU reports busy (0xFF) instead of re-sending command
                for poll in range(6):
                    ack = dev.get_feature_report(0, 65)
                    r4 = ack[4] if (ack and len(ack) > 4) else None
                    if r4 == 1:
                        return True
                    if r4 in (0xFF, 255, 0) and poll < 5:
                        time.sleep(delay)
                        continue
                    self._log(f"ACK mismatch for [{buf[0]:02X} {buf[1]:02X}] (attempt {attempt}/{retries}): r4={r4}")
                    break
            except Exception as exc:
                self._log(f"HID error for [{buf[0]:02X} {buf[1]:02X}] (attempt {attempt}/{retries}): {exc}")
                time.sleep(delay)
        return False

    def execute_transaction(self, steps: List[Tuple[List[int], bool]], label: str = "TX") -> bool:
        """
        Open HID endpoint, execute an atomic list of (payload_64b, expect_ack) packets with retries, and close cleanly.
        If the first full transaction attempt fails on ACK/IO, retries once after re-enumerating.
        """
        with self._lock:
            t0 = time.perf_counter()
            for tx_try in range(2):
                mode, path = detect_connection_mode()
                if mode == "Disconnected" or not path:
                    self.last_error = "Không tìm thấy AULA S75 Pro (kiểm tra cáp USB)."
                    self.last_ack_ok = False
                    self._log(f"[{label}] {self.last_error}")
                    raise RuntimeError(self.last_error)

                if mode == "2.4G":
                    self.last_error = "Đang ở chế độ 2.4G Wireless — vui lòng cắm dây USB để cấu hình ổn định nhất."
                    self.last_ack_ok = False
                    self._log(f"[{label}] {self.last_error}")
                    raise RuntimeError(self.last_error)

                dev = hid.device()
                try:
                    dev.open_path(path)
                    all_ok = True
                    for payload, expect_ack in steps:
                        if not self._send_one_packet(dev, payload, expect_ack=expect_ack):
                            all_ok = False
                            break

                    if all_ok:
                        self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
                        self.last_error = ""
                        self.last_ack_ok = True
                        self._log(f"[{label}] OK ({len(steps)} gói, {self.last_latency_ms:.0f} ms)")
                        return True
                except Exception as exc:
                    self.last_error = str(exc)
                    self._log(f"[{label}] Lỗi giao tiếp (lần {tx_try + 1}/2): {exc}")
                finally:
                    try:
                        dev.close()
                    except Exception:
                        pass

                time.sleep(0.05)

            self.last_ack_ok = False
            if not self.last_error:
                self.last_error = "Bàn phím không phản hồi ACK hợp lệ."
            return False

    def apply_global_lighting(
        self,
        mode: int = 1,
        r: int = 255,
        g: int = 106,
        b: int = 0,
        brightness: int = 5,
        speed: int = 3,
        direction: int = 0,
        colorful: int = 0,
    ) -> bool:
        """Send exact 5-packet Global Light Mode command (Routine 0x42AFD0)."""
        p_cfg = build_global_lighting_packet(
            mode=mode, r=r, g=g, b=b,
            brightness=brightness, speed=speed,
            direction=direction, colorful=colorful,
        )
        steps = [
            ([0x04, 0x18], True),
            ([0x04, 0x13, 0, 0, 0, 0, 0, 0, 1], True),
            (p_cfg, False),
            ([0x04, 0x02], True),
            ([0x04, 0xF0], False),
        ]
        return self.execute_transaction(
            steps,
            label=f"LED Mode={mode} RGB=({r},{g},{b}) Colorful={colorful} Bri={brightness} Spd={speed}",
        )

    def apply_per_key_lighting(
        self,
        key_colors: Dict[int, Tuple[int, int, int]],
        slot: int = 1,
        default_rgb: Tuple[int, int, int] = (0, 0, 0),
    ) -> bool:
        """Send Per-Key UserLight mode switch (0x80) + 576-byte key color table (0x04, 0x23)."""
        p_mode = [0] * 64
        p_mode[0] = 0x80
        p_mode[9] = max(1, min(19, int(slot)))
        p_mode[14] = 0xAA
        p_mode[15] = 0x55

        table = build_per_key_table(key_colors, default_rgb=default_rgb)
        steps: List[Tuple[List[int], bool]] = [
            ([0x04, 0x18], True),
            ([0x04, 0x13, 0, 0, 0, 0, 0, 0, 1], True),
            (p_mode, False),
            ([0x04, 0x02], True),
            ([0x04, 0xF0], False),
            ([0x04, 0x18], True),
            ([0x04, 0x23, 0, 0, 0, 0, 0, 0, 9], True),
        ]
        for chunk_idx in range(9):
            steps.append((table[chunk_idx * 64 : (chunk_idx + 1) * 64], False))
        steps.extend([
            ([0x04, 0x02], True),
            ([0x04, 0xF0], False),
        ])
        return self.execute_transaction(steps, label=f"Per-Key RGB ({len(key_colors)} phím)")

    def apply_keyboard_settings(
        self,
        disable_win: bool = False,
        disable_alttab: bool = False,
        disable_altf4: bool = False,
        fn_switch: bool = False,
        sleep_time: int = 1,
        key_respondtime: int = 2,
    ) -> bool:
        """Send Gaming lock / Sleep / Response time configuration (Routine 0x4141A0)."""
        p_set = build_settings_packet(
            disable_win=disable_win,
            disable_alttab=disable_alttab,
            disable_altf4=disable_altf4,
            fn_switch=fn_switch,
            sleep_time=sleep_time,
            key_respondtime=key_respondtime,
        )
        steps = [
            ([0x04, 0x18], True),
            ([0x04, 0x17, 1, 0, 0, 0, 0, 0, 1], True),
            (p_set, False),
            ([0x04, 0x02], True),
        ]
        return self.execute_transaction(steps, label="Keyboard Settings")

    def sync_lcd_clock(self) -> bool:
        """Sync Windows local date & time to the AULA S75 Pro LCD screen (Routine 0x423A80)."""
        p_time = build_clock_sync_packet()
        steps = [
            ([0x04, 0x18], True),
            ([0x04, 0x28, 0, 0, 0, 0, 0, 0, 1], True),
            (p_time, False),
            ([0x04, 0x02], True),
        ]
        return self.execute_transaction(steps, label="Sync LCD Clock")


# Backwards-compatible helper
def apply_keyboard_lighting(
    mode: int = 1,
    r: int = 255,
    g: int = 106,
    b: int = 0,
    brightness: int = 5,
    speed: int = 3,
    direction: int = 0,
    colorful: int = 0,
) -> bool:
    return KeyboardTransport().apply_global_lighting(
        mode=mode, r=r, g=g, b=b,
        brightness=brightness, speed=speed,
        direction=direction, colorful=colorful,
    )
