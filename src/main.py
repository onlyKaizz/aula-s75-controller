"""
AULA S75 Pro Controller - Main Entry Point
Binds the Studio GUI, Serialized USB HID Device Controller, and Windows System Tray.
Supports '--minimized' flag for silent Windows auto-startup.
"""

import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.device import AulaS75Device
from src.gui import AulaS75App
from src.storage import load_config
from src.tray import SystemTrayApp


def main():
    start_minimized = "--minimized" in sys.argv
    cfg = load_config()
    device = AulaS75Device()
    app: AulaS75App | None = None
    tray_app: SystemTrayApp | None = None

    def show_window():
        if app:
            app.after(0, lambda: (app.deiconify(), app.lift(), app.focus_force()))

    def apply_prof_from_tray(prof: dict):
        if app:
            app.after(0, lambda: app.apply_profile(prof))

    def turn_off_from_tray():
        if app:
            app.after(0, app.quick_turn_off)

    def sync_clock_from_tray():
        if app:
            app.after(0, app._on_sync_clock)

    def quit_app():
        if tray_app:
            tray_app.stop()
        if app:
            app.after(0, app.destroy)
        os._exit(0)

    tray_app = SystemTrayApp(
        on_show_window=show_window,
        on_apply_profile=apply_prof_from_tray,
        on_turn_off=turn_off_from_tray,
        on_sync_clock=sync_clock_from_tray,
        on_quit=quit_app,
        profiles=cfg.get("profiles", []),
    )

    threading.Thread(target=tray_app.run, daemon=True).start()

    app = AulaS75App(
        device=device,
        on_minimize_to_tray=lambda: None,
        on_profiles_updated=tray_app.update_profiles,
        start_minimized=start_minimized,
    )
    app.mainloop()


if __name__ == "__main__":
    main()
