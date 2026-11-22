"""
AULA S75 Pro Device Manager
Provides high-level abstraction for interacting with AULA S75 Pro keyboard.
"""

import hid
from .protocol import (
    VENDOR_ID,
    PRODUCT_ID,
    LIGHT_MODES,
    open_keyboard_device,
    apply_keyboard_lighting,
)

class AulaS75Device:
    def __init__(self):
        self.vid = VENDOR_ID
        self.pid = PRODUCT_ID

    def is_connected(self) -> bool:
        """Check if keyboard is connected via USB."""
        devs = hid.enumerate(self.vid, self.pid)
        return len(devs) > 0

    def get_info(self) -> dict:
        """Get keyboard connection details."""
        devs = hid.enumerate(self.vid, self.pid)
        if not devs:
            return {"connected": False, "name": "Không phát hiện AULA S75 Pro"}
        
        info = {
            "connected": True,
            "name": "AULA S75 Pro",
            "vid": f"0x{self.vid:04X}",
            "pid": f"0x{self.pid:04X}",
            "endpoints": len(devs),
            "manufacturer": devs[0].get("manufacturer_string", "SONiX"),
            "product": devs[0].get("product_string", "AULA-S75Pro")
        }
        return info

    def apply_lighting(
        self,
        mode: int = 1,
        r: int = 0,
        g: int = 255,
        b: int = 255,
        brightness: int = 5,
        speed: int = 3,
        direction: int = 0,
        colorful: int = 0,
    ) -> bool:
        """Send RGB lighting configuration to the keyboard."""
        return apply_keyboard_lighting(
            mode=mode,
            r=r,
            g=g,
            b=b,
            brightness=brightness,
            speed=speed,
            direction=direction,
            colorful=colorful,
        )

    def set_static_color(self, r: int, g: int, b: int, brightness: int = 5) -> bool:
        """Convenience method to set solid static color."""
        return self.apply_lighting(mode=1, r=r, g=g, b=b, brightness=brightness, colorful=0)

    def turn_off_lighting(self) -> bool:
        """Turn off keyboard backlight."""
        return self.apply_lighting(mode=20, r=0, g=0, b=0, brightness=1)
