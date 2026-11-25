"""
AULA S75 Pro Controller - System Tray Integration
Dynamic right-click menu with saved personal profiles, LCD clock sync, and quick LED toggle.
"""

from __future__ import annotations
import threading
from typing import Callable, List, Optional
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item


def create_tray_image(width: int = 64, height: int = 64) -> Image.Image:
    """Generate a high-contrast keyboard icon for the Windows notification area."""
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([4, 12, 60, 52], radius=8, fill="#141720", outline="#00D4FF", width=3)

    for x in (10, 22, 34, 46):
        c1 = "#FF6A00" if x == 34 else "#2E364D"
        c2 = "#00D4FF" if x in (10, 46) else "#2E364D"
        draw.rectangle([x, 18, x + 8, 26], fill=c1)
        draw.rectangle([x, 30, x + 8, 38], fill=c2)

    draw.rectangle([16, 42, 48, 47], fill="#FF6A00")
    return image


class SystemTrayApp:
    def __init__(
        self,
        on_show_window: Optional[Callable[[], None]] = None,
        on_apply_profile: Optional[Callable[[dict], None]] = None,
        on_turn_off: Optional[Callable[[], None]] = None,
        on_sync_clock: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        profiles: Optional[List[dict]] = None,
    ):
        self.on_show_window = on_show_window
        self.on_apply_profile = on_apply_profile
        self.on_turn_off = on_turn_off
        self.on_sync_clock = on_sync_clock
        self.on_quit = on_quit
        self.profiles = list(profiles or [])
        self.icon: Optional[pystray.Icon] = None

    def update_profiles(self, profiles: List[dict]):
        self.profiles = list(profiles)
        if self.icon:
            self.icon.menu = self._build_menu()
            self.icon.update_menu()

    def _build_menu(self) -> pystray.Menu:
        menu_items = [
            item("Mở AULA S75 Studio", lambda _ic, _it: self.on_show_window and self.on_show_window(), default=True),
            pystray.Menu.SEPARATOR,
        ]

        if self.profiles:
            profile_items = []
            for p in self.profiles[:8]:
                prof_copy = dict(p)
                profile_items.append(
                    item(prof_copy["name"], lambda _ic, _it, pc=prof_copy: self.on_apply_profile and self.on_apply_profile(pc))
                )
            menu_items.append(item("🎨 Áp dụng Profile nhanh", pystray.Menu(*profile_items)))

        menu_items.extend([
            item("🕒 Đồng bộ giờ LCD", lambda _ic, _it: self.on_sync_clock and self.on_sync_clock()),
            item("🌙 Tắt đèn bàn phím", lambda _ic, _it: self.on_turn_off and self.on_turn_off()),
            pystray.Menu.SEPARATOR,
            item("Thoát hoàn toàn", self._exit_action),
        ])
        return pystray.Menu(*menu_items)

    def _exit_action(self, _icon, _item):
        if self.icon:
            self.icon.stop()
        if self.on_quit:
            self.on_quit()

    def run(self):
        img = create_tray_image()
        self.icon = pystray.Icon("AULA S75 Pro", img, "AULA S75 Pro — Personal RGB Studio", self._build_menu())
        self.icon.run()

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
