"""
AULA S75 Pro Controller - System Tray Integration
Provides a background notification area icon with quick actions.
"""

import threading
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

def create_tray_image(width=64, height=64, color1="#00ffff", color2="#7b00ff"):
    """Generate a clean keyboard-styled tray icon."""
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Outer rounded rectangle (keyboard frame)
    draw.rounded_rectangle([4, 12, 60, 52], radius=8, fill="#1e212b", outline=color1, width=3)

    # Mini keycaps inside
    key_color = "#333b4d"
    # Row 1 keys
    draw.rectangle([10, 18, 18, 26], fill=key_color)
    draw.rectangle([22, 18, 30, 26], fill=key_color)
    draw.rectangle([34, 18, 42, 26], fill=color1)
    draw.rectangle([46, 18, 54, 26], fill=key_color)

    # Row 2 keys
    draw.rectangle([10, 30, 18, 38], fill=color2)
    draw.rectangle([22, 30, 30, 38], fill=key_color)
    draw.rectangle([34, 30, 42, 38], fill=key_color)
    draw.rectangle([46, 30, 54, 38], fill=color2)

    # Spacebar
    draw.rectangle([16, 42, 48, 47], fill=color1)

    return image

class SystemTrayApp:
    def __init__(self, on_show_window=None, on_quit=None, device=None):
        self.on_show_window = on_show_window
        self.on_quit = on_quit
        self.device = device
        self.icon = None

    def _show_window_action(self, icon, item):
        if self.on_show_window:
            self.on_show_window()

    def _quick_turn_off(self, icon, item):
        if self.device:
            threading.Thread(target=self.device.turn_off_lighting, daemon=True).start()

    def _quick_spectrum(self, icon, item):
        if self.device:
            threading.Thread(
                target=lambda: self.device.apply_lighting(mode=8, colorful=1),
                daemon=True
            ).start()

    def _exit_action(self, icon, item):
        if self.icon:
            self.icon.stop()
        if self.on_quit:
            self.on_quit()

    def run(self):
        img = create_tray_image()
        menu = pystray.Menu(
            item("Mở điều khiển AULA S75", self._show_window_action, default=True),
            pystray.Menu.SEPARATOR,
            item("🌈 Bật hiệu ứng Cầu vồng", self._quick_spectrum),
            item("🌙 Tắt đèn bàn phím", self._quick_turn_off),
            pystray.Menu.SEPARATOR,
            item("Thoát", self._exit_action)
        )
        self.icon = pystray.Icon("AULA S75 Pro", img, "AULA S75 Pro Controller", menu)
        self.icon.run()

    def stop(self):
        if self.icon:
            self.icon.stop()
