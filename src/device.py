"""
AULA S75 Pro Device Manager
Provides serialized latest-wins async dispatching so slider drags never drop or collide on USB HID.
"""

from __future__ import annotations
import threading
from typing import Any, Callable, Dict, Optional, Tuple
import hid

from .protocol import (
    VENDOR_ID,
    USB_PRODUCT_ID,
    DONGLE_PRODUCT_ID,
    KeyboardTransport,
    detect_connection_mode,
)


class AulaS75Device:
    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.vid = VENDOR_ID
        self.pid = USB_PRODUCT_ID
        self.transport = KeyboardTransport(log_callback=log_callback)

        # Latest-wins coalescing worker for smooth slider updates
        self._queue_lock = threading.Lock()
        self._pending_task: Optional[Tuple[str, dict, Optional[Callable[[bool, str], None]]]] = None
        self._worker_running = False

    def get_connection_mode(self) -> str:
        mode, _ = detect_connection_mode()
        return mode

    def is_connected(self) -> bool:
        mode, _ = detect_connection_mode()
        return mode != "Disconnected"

    def get_info(self) -> Dict[str, Any]:
        mode, _ = detect_connection_mode()
        if mode == "Disconnected":
            return {"connected": False, "mode": "Disconnected", "name": "Chưa kết nối AULA S75 Pro"}

        pid = USB_PRODUCT_ID if mode == "USB" else DONGLE_PRODUCT_ID
        devs = hid.enumerate(self.vid, pid)
        return {
            "connected": True,
            "mode": mode,
            "name": "AULA S75 Pro",
            "vid": f"0x{self.vid:04X}",
            "pid": f"0x{pid:04X}",
            "endpoints": len(devs),
            "manufacturer": devs[0].get("manufacturer_string", "SONiX") if devs else "SONiX",
            "product": devs[0].get("product_string", "AULA-S75Pro") if devs else "AULA-S75Pro",
            "latency_ms": self.transport.last_latency_ms,
        }

    def enqueue_lighting(
        self,
        params: dict,
        on_done: Optional[Callable[[bool, str], None]] = None,
    ):
        """Queue a global lighting update; coalesces multiple rapid requests to the newest one."""
        with self._queue_lock:
            self._pending_task = ("global", dict(params), on_done)
            if not self._worker_running:
                self._worker_running = True
                threading.Thread(target=self._drain_worker, daemon=True).start()

    def enqueue_per_key(
        self,
        key_colors: Dict[int, Tuple[int, int, int]],
        slot: int = 1,
        on_done: Optional[Callable[[bool, str], None]] = None,
    ):
        """Queue a per-key RGB table update."""
        with self._queue_lock:
            self._pending_task = ("per_key", {"key_colors": dict(key_colors), "slot": slot}, on_done)
            if not self._worker_running:
                self._worker_running = True
                threading.Thread(target=self._drain_worker, daemon=True).start()

    def enqueue_sidelight(
        self,
        side_mode: int,
        on_done: Optional[Callable[[bool, str], None]] = None,
    ):
        """Queue a side LED strip mode update."""
        with self._queue_lock:
            self._pending_task = ("sidelight", {"side_mode": side_mode}, on_done)
            if not self._worker_running:
                self._worker_running = True
                threading.Thread(target=self._drain_worker, daemon=True).start()

    def enqueue_bundle(
        self,
        global_params: dict,
        side_mode: int,
        on_done: Optional[Callable[[bool, str], None]] = None,
    ):
        """Queue both main lighting and side light update sequentially."""
        with self._queue_lock:
            self._pending_task = ("bundle", {"global_params": dict(global_params), "side_mode": side_mode}, on_done)
            if not self._worker_running:
                self._worker_running = True
                threading.Thread(target=self._drain_worker, daemon=True).start()

    def _drain_worker(self):
        while True:
            with self._queue_lock:
                task = self._pending_task
                self._pending_task = None
                if task is None:
                    self._worker_running = False
                    return

            kind, payload, on_done = task
            ok = False
            err = ""
            try:
                if kind == "global":
                    ok = self.transport.apply_global_lighting(**payload)
                elif kind == "per_key":
                    ok = self.transport.apply_per_key_lighting(**payload)
                elif kind == "sidelight":
                    ok = self.transport.apply_sidelight(**payload)
                elif kind == "bundle":
                    ok1 = self.transport.apply_global_lighting(**payload["global_params"])
                    ok2 = self.transport.apply_sidelight(side_mode=payload["side_mode"])
                    ok = ok1 and ok2
                if not ok:
                    err = self.transport.last_error or "Không nhận được phản hồi ACK từ bàn phím."
            except Exception as exc:
                ok = False
                err = str(exc)

            if on_done:
                try:
                    on_done(ok, err)
                except Exception:
                    pass

    def apply_sidelight(self, side_mode: int = 32) -> bool:
        return self.transport.apply_sidelight(side_mode=side_mode)

    def apply_lighting(
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
        return self.transport.apply_global_lighting(
            mode=mode, r=r, g=g, b=b,
            brightness=brightness, speed=speed,
            direction=direction, colorful=colorful,
        )

    def apply_per_key(self, key_colors: Dict[int, Tuple[int, int, int]], slot: int = 1) -> bool:
        return self.transport.apply_per_key_lighting(key_colors=key_colors, slot=slot)

    def apply_settings(self, **kwargs) -> bool:
        return self.transport.apply_keyboard_settings(**kwargs)

    def sync_clock(self) -> bool:
        return self.transport.sync_lcd_clock()

    def turn_off_lighting(self) -> bool:
        return self.transport.apply_global_lighting(mode=20, r=0, g=0, b=0, brightness=1, colorful=0)
