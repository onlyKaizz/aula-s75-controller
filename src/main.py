"""
AULA S75 Pro Controller - Main Entry Point
Launches Desktop GUI and System Tray background integration.
"""

import sys
import threading
import os

# Add root directory to sys.path if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gui import AulaS75App
from src.tray import SystemTrayApp
from src.device import AulaS75Device

def main():
    device = AulaS75Device()
    tray_app = None
    app = None

    def show_window():
        if app:
            app.after(0, lambda: (app.deiconify(), app.lift(), app.focus_force()))

    def quit_app():
        if tray_app:
            tray_app.stop()
        if app:
            app.after(0, app.destroy)
        sys.exit(0)

    def on_minimize_to_tray():
        # Triggered when user closes main window
        pass

    tray_app = SystemTrayApp(
        on_show_window=show_window,
        on_quit=quit_app,
        device=device
    )

    # Start system tray in a background daemon thread
    tray_thread = threading.Thread(target=tray_app.run, daemon=True)
    tray_thread.start()

    # Launch GUI in main thread (Tkinter requires main thread on Windows)
    app = AulaS75App(on_minimize_to_tray=on_minimize_to_tray)
    app.mainloop()

if __name__ == "__main__":
    main()
