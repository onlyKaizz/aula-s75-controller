import time
import hid

VENDOR_ID = 0x0C45
PRODUCT_ID = 0x800A

def get_keyboard_device():
    """Find and open the configuration HID interface for AULA S75 Pro."""
    devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    if not devices:
        raise RuntimeError("Không tìm thấy bàn phím AULA S75 Pro qua USB!")

    # Prefer interface 3 (usage_page 0xFF13) or vendor interface
    target_path = None
    for d in devices:
        if d.get('usage_page', 0) == 0xFF13 or d.get('interface_number', -1) == 3:
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

def send_feature_packet(dev, payload_64bytes):
    """
    Send a 64-byte payload wrapped in a 65-byte HID feature report (Report ID = 0x00).
    """
    if len(payload_64bytes) < 64:
        payload_64bytes = payload_64bytes + [0] * (64 - len(payload_64bytes))
    elif len(payload_64bytes) > 64:
        payload_64bytes = payload_64bytes[:64]

    report = [0x00] + payload_64bytes
    dev.send_feature_report(report)
    time.sleep(0.015)  # 15ms delay between packets as per driver spec

def set_keyboard_rgb(mode=11, r=255, g=0, b=0, brightness=5, speed=3, direction=0, colorful=0):
    """
    Set lighting mode and color for AULA S75 Pro.
    :param mode: Light mode (1..20, 11 is static single color, 0 is off)
    :param r: Red (0-255)
    :param g: Green (0-255)
    :param b: Blue (0-255)
    :param brightness: 1-5 (5 is max)
    :param speed: 1-5 (3 is normal)
    :param direction: 0 or 1
    :param colorful: 0 = custom RGB color, 1 = rainbow spectrum
    """
    dev = get_keyboard_device()
    try:
        print(f"[*] Đang gửi lệnh đổi màu: Mode={mode}, RGB=({r}, {g}, {b}), Brightness={brightness}...")

        # 1. Handshake Packet 1 (0x04, 0x18)
        p1 = [0x04, 0x18] + [0] * 62
        send_feature_packet(dev, p1)

        # 2. Handshake Packet 2 (0x04, 0x13, offset 8 = 1)
        p2 = [0x04, 0x13, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01] + [0] * 55
        send_feature_packet(dev, p2)

        # 3. Main Lighting Config Packet
        p3 = [0] * 64
        p3[0] = mode & 0xFF
        p3[1] = r & 0xFF
        p3[2] = g & 0xFF
        p3[3] = b & 0xFF
        p3[8] = brightness & 0xFF
        p3[9] = speed & 0xFF
        p3[10] = direction & 0xFF
        p3[11] = colorful & 0xFF
        # Magic word 0x55AA
        p3[14] = 0xAA
        p3[15] = 0x55
        send_feature_packet(dev, p3)

        # 4. Apply Packet (0x04, 0x02)
        p4 = [0x04, 0x02] + [0] * 62
        send_feature_packet(dev, p4)

        # 5. Finish Packet (0x04, 0xF0)
        p5 = [0x04, 0xF0] + [0] * 62
        send_feature_packet(dev, p5)

        print("[+] Gửi lệnh thành công!")
    finally:
        dev.close()

if __name__ == "__main__":
    # Test setting RED color
    set_keyboard_rgb(mode=11, r=255, g=0, b=0, brightness=5, colorful=0)
