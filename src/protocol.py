"""
AULA S75 Pro USB HID Lighting Protocol Implementation
Reverse-engineered from official AULA S75Pro DeviceDriver.exe

Keyboard Vendor ID:  0x0C45 (Sonix / Microdia)
Keyboard Product ID: 0x800A (AULA S75 Pro)
HID Interface:       Interface 3 (UsagePage: 0xFF13, Usage: 0x0001)
"""

import time
import hid

VENDOR_ID = 0x0C45
PRODUCT_ID = 0x800A

# Lighting modes mapped from official driver (1033.lan / t_light_data)
LIGHT_MODES = {
    1: "Static (Tĩnh)",
    2: "Single On (Đơn sáng khi bấm)",
    3: "Single Off (Đơn tắt khi bấm)",
    4: "Glittering (Lấp lánh)",
    5: "Fluttering (Bay bổng)",
    6: "Colourful (Đa sắc)",
    7: "Breathing (Nhịp thở)",
    8: "Spectrum (Cầu vồng chuyển sắc)",
    9: "Outward (Tỏa ra ngoài)",
    10: "Scrolling (Cuộn dòng)",
    11: "Rolling (Sóng lượn)",
    12: "Rotating (Xoay tròn)",
    13: "Explode (Bùng nổ)",
    14: "Launch (Phóng tia)",
    15: "Ripples (Gợn sóng)",
    16: "Flowing (Dòng chảy)",
    17: "Pulsating (Nhịp đập)",
    18: "Tilt (Nghiêng dòng)",
    19: "Shuttle (Thoi đưa)",
    20: "LED Off (Tắt đèn)"
}

# Key indices for 75% AULA S75 Pro layout (from layouts/rgb-keyboard.xml)
# 80 physical keys, indexed up to 120
KEY_INDICES = [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
    15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
    30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44,
    45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
    60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74,
    75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
    90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103,
    104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116,
    117, 118, 119, 120
]

def open_keyboard_device():
    """Find and open the configuration HID interface (interface 3) for AULA S75 Pro."""
    devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    if not devices:
        raise RuntimeError("Không tìm thấy bàn phím AULA S75 Pro qua USB!")

    target_path = None
    for d in devices:
        if d.get('interface_number', -1) == 3 or d.get('usage_page', 0) == 0xFF13:
            target_path = d['path']
            break

    if not target_path:
        for d in devices:
            if d.get('usage_page', 0) >= 0xFF00:
                target_path = d['path']
                break

    if not target_path:
        target_path = devices[0]['path']

    dev = hid.device()
    dev.open_path(target_path)
    return dev

def send_packet(dev, payload_bytes, expect_ack=False, delay=0.035):
    """
    Send a 64-byte payload inside a 65-byte HID feature report (Report ID 0).
    Optionally read back verification report (expect report[4] == 1).
    """
    if len(payload_bytes) < 64:
        payload_bytes = payload_bytes + [0] * (64 - len(payload_bytes))
    elif len(payload_bytes) > 64:
        payload_bytes = payload_bytes[:64]

    report = [0x00] + payload_bytes
    dev.send_feature_report(report)
    time.sleep(delay)

    if expect_ack:
        try:
            ack_rep = dev.get_feature_report(0, 65)
            if ack_rep and len(ack_rep) > 4 and ack_rep[4] == 1:
                return True
        except Exception:
            pass
        return False
    return True

def apply_keyboard_lighting(mode=1, r=0, g=255, b=255, brightness=5, speed=3, direction=0, colorful=0):
    """
    Apply lighting mode and color to AULA S75 Pro.
    Executes the exact 3-step sequence used by official driver:
      Step 1: Set Mode Command (0x80)
      Step 2: Send Per-Key Color Table (576 bytes in 9 chunks)
      Step 3: Send Lighting Properties (Brightness, Speed, Direction, RGB)
    """
    actual_mode = 0 if mode == 20 else mode

    dev = open_keyboard_device()
    try:
        # --- Step 1: Mode Selection (Routine 0x44B7F0) ---
        send_packet(dev, [0x04, 0x18], expect_ack=True)
        send_packet(dev, [0x04, 0x13, 0, 0, 0, 0, 0, 0, 1], expect_ack=True)

        p_mode = [0] * 64
        p_mode[0] = 0x80
        p_mode[9] = actual_mode & 0xFF
        p_mode[14] = 0xAA
        p_mode[15] = 0x55
        send_packet(dev, p_mode, expect_ack=False)

        send_packet(dev, [0x04, 0x02], expect_ack=True)
        send_packet(dev, [0x04, 0xF0], expect_ack=False)

        # --- Step 2: Per-Key Color Table (Routine 0x44B900) ---
        send_packet(dev, [0x04, 0x18], expect_ack=True)
        send_packet(dev, [0x04, 0x23, 0, 0, 0, 0, 0, 0, 9], expect_ack=True)

        table = [0] * 576
        for k_idx in KEY_INDICES:
            offset = k_idx * 4
            if offset + 3 < 574:
                table[offset] = k_idx & 0xFF
                table[offset + 1] = r & 0xFF
                table[offset + 2] = g & 0xFF
                table[offset + 3] = b & 0xFF

        # Magic word at end of table (offsets 574, 575)
        table[574] = 0xAA
        table[575] = 0x55

        # Send 9 x 64-byte chunks
        for chunk_idx in range(9):
            chunk = table[chunk_idx * 64 : (chunk_idx + 1) * 64]
            send_packet(dev, chunk, expect_ack=False)

        send_packet(dev, [0x04, 0x02], expect_ack=True)
        send_packet(dev, [0x04, 0xF0], expect_ack=False)

        # --- Step 3: Global Lighting Config (Routine 0x42B030) ---
        send_packet(dev, [0x04, 0x18], expect_ack=True)
        send_packet(dev, [0x04, 0x13, 0, 0, 0, 0, 0, 0, 1], expect_ack=True)

        p_cfg = [0] * 64
        p_cfg[0] = actual_mode & 0xFF
        p_cfg[1] = r & 0xFF
        p_cfg[2] = g & 0xFF
        p_cfg[3] = b & 0xFF
        p_cfg[8] = max(1, min(5, brightness))
        p_cfg[9] = max(1, min(5, speed))
        p_cfg[10] = direction & 0x01
        p_cfg[11] = colorful & 0x01
        p_cfg[14] = 0xAA
        p_cfg[15] = 0x55
        send_packet(dev, p_cfg, expect_ack=False)

        send_packet(dev, [0x04, 0x02], expect_ack=True)
        send_packet(dev, [0x04, 0xF0], expect_ack=False)

        return True
    finally:
        dev.close()

if __name__ == "__main__":
    import sys
    print("Testing protocol: Setting Static Cyan (0, 255, 255)...")
    res = apply_keyboard_lighting(mode=1, r=0, g=255, b=255, brightness=5, speed=3)
    print("Result:", res)
