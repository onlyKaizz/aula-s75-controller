import hid

VENDOR_ID = 0x0C45
PRODUCT_ID = 0x800A

def list_aula_devices():
    """Scan and list all HID endpoints matching AULA S75 Pro."""
    devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    if not devices:
        print("[-] Không tìm thấy AULA S75 Pro. Hãy đảm bảo bàn phím đang cắm dây cáp USB.")
        return []

    print(f"[+] Tìm thấy {len(devices)} endpoint HID của AULA S75 Pro (VID: 0x{VENDOR_ID:04X}, PID: 0x{PRODUCT_ID:04X}):\n")
    for idx, d in enumerate(devices):
        path = d['path'].decode('utf-8', errors='ignore') if isinstance(d['path'], bytes) else d['path']
        print(f"--- Endpoint #{idx + 1} ---")
        print(f"  Path: {path}")
        print(f"  Interface Number: {d.get('interface_number', -1)}")
        print(f"  Usage Page: 0x{d.get('usage_page', 0):04X}")
        print(f"  Usage: 0x{d.get('usage', 0):04X}")
        print(f"  Manufacturer: {d.get('manufacturer_string', 'Unknown')}")
        print(f"  Product: {d.get('product_string', 'Unknown')}")
        print()

    return devices

def test_connection():
    """Try connecting to the configuration endpoint."""
    devices = list_aula_devices()
    if not devices:
        return

    # Find vendor-defined usage page (typically 0xFF00 or interface_number == 1 or 3)
    target = None
    for d in devices:
        # Vendor specific usage page is usually >= 0xFF00
        if d.get('usage_page', 0) >= 0xFF00:
            target = d
            break

    if not target:
        target = devices[0]

    path = target['path']
    print(f"[*] Đang thử mở kết nối tới endpoint: {path} ...")
    try:
        h = hid.device()
        h.open_path(path)
        print("[+] Kết nối thành công tới thiết bị!")
        h.close()
    except Exception as e:
        print(f"[-] Không thể mở endpoint: {e}")

if __name__ == "__main__":
    test_connection()
