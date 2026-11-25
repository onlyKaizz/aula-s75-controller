"""
Custom Studio UI Widgets for AULA S75 Pro Controller
- Smooth HSV Saturation/Value Square + Hue Bar Color Picker (PIL + Canvas)
- Interactive 80-Key AULA S75 Pro Keyboard Canvas (Live Animated Preview + Per-Key Painter)
"""

from __future__ import annotations
import colorsys
import math
import random
import time
import tkinter as tk
from typing import Callable, Dict, Optional, Tuple
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from .layout_data import KEYBOARD_KEYS, LAYOUT_HEIGHT, LAYOUT_WIDTH


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"


def hex_to_rgb(hex_str: str) -> Optional[Tuple[int, int, int]]:
    s = hex_str.strip().lstrip("#")
    if len(s) != 6:
        return None
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        return None


def scale_rgb(rgb: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    return (
        max(0, min(255, int(rgb[0] * factor))),
        max(0, min(255, int(rgb[1] * factor))),
        max(0, min(255, int(rgb[2] * factor))),
    )


def blend_rgb(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


class HSVColorPicker(ctk.CTkFrame):
    """Embedded smooth HSV Color Picker with SV square, Hue bar, Hex input, and RGB readouts."""

    SV_W = 210
    SV_H = 156
    HUE_W = 22

    def __init__(
        self,
        master,
        initial_rgb: Tuple[int, int, int] = (255, 106, 0),
        on_change: Optional[Callable[[int, int, int, bool], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="#141720", corner_radius=12, border_width=1, border_color="#262C3D", **kwargs)
        self.on_change = on_change
        self._suppress = False

        r, g, b = initial_rgb
        self.h, self.s, self.v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        self._sv_tk: Optional[ImageTk.PhotoImage] = None
        self._hue_tk: Optional[ImageTk.PhotoImage] = None

        self._build()
        self._render_hue_bar()
        self._render_sv_box()
        self._sync_indicators_and_inputs()

    def _build(self):
        top_area = ctk.CTkFrame(self, fg_color="transparent")
        top_area.pack(padx=14, pady=(14, 10))

        self.sv_canvas = tk.Canvas(
            top_area,
            width=self.SV_W,
            height=self.SV_H,
            bg="#0E1015",
            highlightthickness=1,
            highlightbackground="#2E364D",
            cursor="crosshair",
        )
        self.sv_canvas.pack(side="left", padx=(0, 10))
        self.sv_canvas.bind("<Button-1>", self._on_sv_drag)
        self.sv_canvas.bind("<B1-Motion>", self._on_sv_drag)
        self.sv_canvas.bind("<ButtonRelease-1>", self._on_sv_release)

        self.hue_canvas = tk.Canvas(
            top_area,
            width=self.HUE_W,
            height=self.SV_H,
            bg="#0E1015",
            highlightthickness=1,
            highlightbackground="#2E364D",
            cursor="sb_v_double_arrow",
        )
        self.hue_canvas.pack(side="left")
        self.hue_canvas.bind("<Button-1>", self._on_hue_drag)
        self.hue_canvas.bind("<B1-Motion>", self._on_hue_drag)
        self.hue_canvas.bind("<ButtonRelease-1>", self._on_hue_release)

        # Preview + Hex + RGB controls
        info_row = ctk.CTkFrame(self, fg_color="#1C202E", corner_radius=8)
        info_row.pack(fill="x", padx=14, pady=(0, 12))

        self.swatch_box = ctk.CTkFrame(info_row, width=40, height=36, corner_radius=8, border_width=1, border_color="#3A4259")
        self.swatch_box.pack(side="left", padx=(10, 8), pady=8)
        self.swatch_box.pack_propagate(False)

        hex_col = ctk.CTkFrame(info_row, fg_color="transparent")
        hex_col.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=6)

        ctk.CTkLabel(hex_col, text="HEX", font=ctk.CTkFont(size=10, weight="bold"), text_color="#7D87A3").pack(anchor="w")
        self.hex_var = ctk.StringVar()
        self.hex_entry = ctk.CTkEntry(
            hex_col,
            textvariable=self.hex_var,
            height=26,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            fg_color="#12151E",
            border_color="#2E364D",
        )
        self.hex_entry.pack(fill="x")
        self.hex_entry.bind("<Return>", self._on_hex_submit)
        self.hex_entry.bind("<FocusOut>", self._on_hex_submit)

        self.rgb_label = ctk.CTkLabel(
            info_row,
            text="255, 106, 0",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#A8B3CF",
            width=84,
        )
        self.rgb_label.pack(side="right", padx=(0, 10))

    def _render_hue_bar(self):
        img = Image.new("RGB", (self.HUE_W, self.SV_H))
        px = img.load()
        for y in range(self.SV_H):
            hue = y / max(1, self.SV_H - 1)
            r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]
            for x in range(self.HUE_W):
                px[x, y] = (r, g, b)
        self._hue_tk = ImageTk.PhotoImage(img)
        self.hue_canvas.delete("bg")
        self.hue_canvas.create_image(0, 0, anchor="nw", image=self._hue_tk, tags="bg")

    def _render_sv_box(self):
        # Fast PIL gradient composition for the Saturation/Value square
        hr, hg, hb = [int(c * 255) for c in colorsys.hsv_to_rgb(self.h, 1.0, 1.0)]
        w, h = self.SV_W, self.SV_H
        img = Image.new("RGB", (w, h))
        px = img.load()
        for y in range(h):
            val = 1.0 - (y / max(1, h - 1))
            v255 = 255.0 * val
            for x in range(w):
                sat = x / max(1, w - 1)
                inv_s = 1.0 - sat
                r = int((inv_s * 255.0 + sat * hr) * val)
                g = int((inv_s * 255.0 + sat * hg) * val)
                b = int((inv_s * 255.0 + sat * hb) * val)
                px[x, y] = (r, g, b)
        self._sv_tk = ImageTk.PhotoImage(img)
        self.sv_canvas.delete("bg")
        self.sv_canvas.create_image(0, 0, anchor="nw", image=self._sv_tk, tags="bg")
        self.sv_canvas.tag_lower("bg")

    def _sync_indicators_and_inputs(self):
        r, g, b = self.get_rgb()
        hx = rgb_to_hex(r, g, b)
        self.swatch_box.configure(fg_color=hx)
        self.rgb_label.configure(text=f"{r}, {g}, {b}")
        self._suppress = True
        self.hex_var.set(hx)
        self._suppress = False

        # SV crosshair
        cx = int(self.s * (self.SV_W - 1))
        cy = int((1.0 - self.v) * (self.SV_H - 1))
        self.sv_canvas.delete("cursor")
        outline = "#FFFFFF" if self.v < 0.6 else "#000000"
        self.sv_canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, outline=outline, width=2, tags="cursor")

        # Hue indicator
        hy = int(self.h * (self.SV_H - 1))
        self.hue_canvas.delete("cursor")
        self.hue_canvas.create_rectangle(1, max(1, hy - 2), self.HUE_W - 1, min(self.SV_H - 1, hy + 2), outline="#FFFFFF", width=2, tags="cursor")

    def get_rgb(self) -> Tuple[int, int, int]:
        r, g, b = colorsys.hsv_to_rgb(self.h, self.s, self.v)
        return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))

    def set_rgb(self, r: int, g: int, b: int, notify: bool = False):
        self.h, self.s, self.v = colorsys.rgb_to_hsv(
            max(0, min(255, r)) / 255.0,
            max(0, min(255, g)) / 255.0,
            max(0, min(255, b)) / 255.0,
        )
        self._render_sv_box()
        self._sync_indicators_and_inputs()
        if notify and self.on_change:
            rr, gg, bb = self.get_rgb()
            self.on_change(rr, gg, bb, True)

    def _on_sv_drag(self, event):
        self.s = max(0.0, min(1.0, event.x / max(1, self.SV_W - 1)))
        self.v = max(0.0, min(1.0, 1.0 - (event.y / max(1, self.SV_H - 1))))
        self._sync_indicators_and_inputs()
        if self.on_change:
            r, g, b = self.get_rgb()
            self.on_change(r, g, b, False)

    def _on_sv_release(self, event):
        self._on_sv_drag(event)
        if self.on_change:
            r, g, b = self.get_rgb()
            self.on_change(r, g, b, True)

    def _on_hue_drag(self, event):
        self.h = max(0.0, min(1.0, event.y / max(1, self.SV_H - 1)))
        self._render_sv_box()
        self._sync_indicators_and_inputs()
        if self.on_change:
            r, g, b = self.get_rgb()
            self.on_change(r, g, b, False)

    def _on_hue_release(self, event):
        self._on_hue_drag(event)
        if self.on_change:
            r, g, b = self.get_rgb()
            self.on_change(r, g, b, True)

    def _on_hex_submit(self, _event=None):
        if self._suppress:
            return
        parsed = hex_to_rgb(self.hex_var.get())
        if parsed:
            self.set_rgb(*parsed, notify=True)


class KeyboardPreviewCanvas(ctk.CTkFrame):
    """
    Visual 80-Key AULA S75 Pro Chassis & Interactive RGB Simulator / Per-Key Painter.
    """

    def __init__(
        self,
        master,
        interactive_paint: bool = False,
        on_paint_key: Optional[Callable[[int, str], None]] = None,
        scale: float = 1.15,
        **kwargs,
    ):
        super().__init__(master, fg_color="#12151E", corner_radius=14, border_width=1, border_color="#252B3D", **kwargs)
        self.interactive_paint = interactive_paint
        self.on_paint_key = on_paint_key
        self.scale = scale

        pad_x = 24
        pad_y = 20
        self.pad_x = pad_x
        self.pad_y = pad_y
        self.canvas_w = int(LAYOUT_WIDTH * scale + pad_x * 2)
        self.canvas_h = int(LAYOUT_HEIGHT * scale + pad_y * 2)

        # Header strip above keyboard
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=14, pady=(10, 2))
        self.title_lbl = ctk.CTkLabel(
            top_bar,
            text="AULA S75 PRO — MÔ PHỎNG TRỰC QUAN (80 PHÍM + NÚM XOAY)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#7D87A3",
        )
        self.title_lbl.pack(side="left")

        self.hover_lbl = ctk.CTkLabel(
            top_bar,
            text="Di chuột lên phím để xem chi tiết" if interactive_paint else "Live Hardware Preview",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#00D4FF",
        )
        self.hover_lbl.pack(side="right")

        self.canvas = tk.Canvas(
            self,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#12151E",
            highlightthickness=0,
            cursor="hand2" if interactive_paint else "arrow",
        )
        self.canvas.pack(padx=10, pady=(2, 12))

        # Animation state
        self.anim_mode = 1
        self.anim_rgb = (255, 106, 0)
        self.anim_brightness = 5
        self.anim_speed = 3
        self.anim_direction = 0
        self.anim_colorful = 0
        self.anim_side_mode = 32
        self.per_key_map: Dict[int, Tuple[int, int, int]] = {}
        self.brush_rgb: Tuple[int, int, int] = (255, 106, 0)
        self._anim_running = not interactive_paint
        self._t0 = time.perf_counter()
        self._sparkle_seeds = {k["light_index"]: random.random() * 6.28 for k in KEYBOARD_KEYS}
        self._key_items: Dict[int, Tuple[int, int, int]] = {}  # light_index -> (glow_id, cap_id, text_id)
        self._side_items: list = []  # (is_left, seg_idx, rect_id)
        self._key_boxes: list = []  # (x1, y1, x2, y2, key_dict)

        self._draw_chassis_and_keys()

        if interactive_paint:
            self.canvas.bind("<Button-1>", self._handle_paint)
            self.canvas.bind("<B1-Motion>", self._handle_paint)
            self.canvas.bind("<Motion>", self._handle_hover)
        else:
            self.canvas.bind("<Motion>", self._handle_hover)
            self._schedule_anim()

    def _draw_chassis_and_keys(self):
        c = self.canvas
        w, h = self.canvas_w, self.canvas_h
        # Keyboard frame shadow & metallic body
        c.create_rectangle(6, 6, w - 6, h - 6, fill="#090B10", outline="#262D42", width=2)
        c.create_rectangle(12, 12, w - 12, h - 12, fill="#171B26", outline="#2E364D", width=1)

        # Left & Right AULA S75 Pro Side Light Strips (8 LED segments each)
        strip_top = 24
        strip_bot = h - 24
        seg_h = (strip_bot - strip_top) / 8.0
        for s_i in range(8):
            sy1 = strip_top + s_i * seg_h + 1
            sy2 = strip_top + (s_i + 1) * seg_h - 1
            r_left = c.create_rectangle(8, sy1, 13, sy2, fill="#00D4FF", outline="")
            r_right = c.create_rectangle(w - 13, sy1, w - 8, sy2, fill="#00D4FF", outline="")
            self._side_items.append((True, s_i, r_left))
            self._side_items.append((False, s_i, r_right))

        # Draw each of the 80 keys
        for k in KEYBOARD_KEYS:
            x1 = self.pad_x + k["x"] * self.scale
            y1 = self.pad_y + k["y"] * self.scale
            x2 = x1 + k["w"] * self.scale
            y2 = y1 + k["h"] * self.scale
            idx = k["light_index"]

            glow = c.create_rectangle(x1 - 2, y1 - 2, x2 + 2, y2 + 2, fill="#FF6A00", outline="", width=0)
            cap = c.create_rectangle(x1 + 1, y1 + 1, x2 - 1, y2 - 1, fill="#1E2332", outline="#323B54", width=1)
            label = k["name"]
            if len(label) > 6:
                label = label[:5]
            txt = c.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=label,
                fill="#D8E0F0",
                font=("Segoe UI", 7 if len(label) > 2 else 8, "bold"),
            )
            self._key_items[idx] = (glow, cap, txt)
            self._key_boxes.append((x1, y1, x2, y2, k))

        # Top-right AULA S75 Pro Rotary Knob (x=560..605, y=0..30 approx)
        kx = self.pad_x + 585 * self.scale
        ky = self.pad_y + 15 * self.scale
        kr = 16 * self.scale
        c.create_oval(kx - kr - 2, ky - kr - 2, kx + kr + 2, ky + kr + 2, fill="#0B0D13", outline="#00D4FF", width=1)
        c.create_oval(kx - kr + 2, ky - kr + 2, kx + kr - 2, ky + kr - 2, fill="#242B3D", outline="#4B5675", width=2)
        c.create_text(kx, ky, text="VOL", fill="#98A3C2", font=("Segoe UI", 6, "bold"))

    def set_preview_state(
        self,
        mode: int,
        rgb: Tuple[int, int, int],
        brightness: int,
        speed: int,
        direction: int,
        colorful: int,
        side_mode: int = 32,
    ):
        self.anim_mode = mode
        self.anim_rgb = rgb
        self.anim_brightness = brightness
        self.anim_speed = speed
        self.anim_direction = direction
        self.anim_colorful = colorful
        self.anim_side_mode = side_mode

    def set_per_key_colors(self, mapping: Dict[int, Tuple[int, int, int]]):
        self.per_key_map = dict(mapping)
        self._redraw_per_key_colors()

    def _redraw_per_key_colors(self):
        for idx, (glow, cap, txt) in self._key_items.items():
            rgb = self.per_key_map.get(idx, (28, 33, 46))
            hx = rgb_to_hex(*rgb)
            # Determine readable legend color
            lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
            txt_col = "#FFFFFF" if lum < 145 else "#12151E"
            self.canvas.itemconfigure(glow, fill=hx)
            # Keep RGB hex string valid for cap
            cap_rgb = blend_rgb(rgb, (18, 22, 32), 0.45) if (rgb[0] + rgb[1] + rgb[2]) > 0 else (26, 30, 42)
            self.canvas.itemconfigure(cap, fill=rgb_to_hex(*cap_rgb), outline=hx if sum(rgb) > 20 else "#2E364D")
            self.canvas.itemconfigure(txt, fill=hx if sum(rgb) > 30 else "#7D87A3")

    def _hit_test(self, x: int, y: int) -> Optional[dict]:
        for x1, y1, x2, y2, k in self._key_boxes:
            if x1 - 2 <= x <= x2 + 2 and y1 - 2 <= y <= y2 + 2:
                return k
        return None

    def _handle_hover(self, event):
        k = self._hit_test(event.x, event.y)
        if k:
            idx = k["light_index"]
            if self.interactive_paint:
                rgb = self.per_key_map.get(idx, (0, 0, 0))
                self.hover_lbl.configure(text=f"Phím: {k['name']} (#{idx}) | {rgb_to_hex(*rgb)}")
            else:
                self.hover_lbl.configure(text=f"Phím: {k['name']} (LED #{idx})")

    def _handle_paint(self, event):
        if not self.interactive_paint:
            return
        k = self._hit_test(event.x, event.y)
        if not k:
            return
        idx = k["light_index"]
        if self.per_key_map.get(idx) == self.brush_rgb:
            return
        self.per_key_map[idx] = self.brush_rgb
        self._redraw_per_key_colors()
        self.hover_lbl.configure(text=f"Đã tô: {k['name']} (#{idx}) → {rgb_to_hex(*self.brush_rgb)}")
        if self.on_paint_key:
            self.on_paint_key(idx, k["name"])

    def _schedule_anim(self):
        if not self._anim_running:
            return
        self._render_anim_frame()
        self.after(45, self._schedule_anim)

    def _render_anim_frame(self):
        t = time.perf_counter() - self._t0
        bri_factor = max(0.18, self.anim_brightness / 5.0)
        spd_factor = 0.6 + self.anim_speed * 0.55
        dir_sign = -1.0 if self.anim_direction else 1.0
        mode = self.anim_mode
        base_rgb = self.anim_rgb
        is_rainbow = (self.anim_colorful == 1) or (mode in (6, 8))

        for k in KEYBOARD_KEYS:
            idx = k["light_index"]
            glow, cap, txt = self._key_items[idx]
            nx = k["x"] / max(1, LAYOUT_WIDTH)
            ny = k["y"] / max(1, LAYOUT_HEIGHT)

            if mode == 20:  # LED Off
                rgb = (0, 0, 0)
            elif mode == 1:  # Static
                rgb = scale_rgb(base_rgb, bri_factor)
            elif mode == 7:  # Breathing
                pulse = 0.15 + 0.85 * (0.5 + 0.5 * math.sin(t * spd_factor * 1.8))
                if is_rainbow:
                    hue = ((t * 0.15 * spd_factor) % 1.0)
                    c = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(hue, 1.0, 1.0))
                else:
                    c = base_rgb
                rgb = scale_rgb(c, bri_factor * pulse)
            elif mode == 8 or mode == 6:  # Spectrum / Colourful
                hue = (t * 0.22 * spd_factor + (nx * 0.35 if mode == 6 else 0.0)) % 1.0
                c = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(hue, 1.0, 1.0))
                rgb = scale_rgb(c, bri_factor)
            elif mode in (9, 10, 11, 12, 16, 18):  # Wave / Rolling / Flowing / Outward / Tilt
                phase = (nx * dir_sign * 1.1 + (ny * 0.4 if mode in (16, 18) else 0.0) - t * spd_factor * 0.45)
                if mode == 9:
                    dist = math.hypot(nx - 0.5, ny - 0.5)
                    phase = dist * 2.0 * dir_sign - t * spd_factor * 0.5
                if is_rainbow:
                    hue = phase % 1.0
                    c = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(hue, 1.0, 1.0))
                    rgb = scale_rgb(c, bri_factor)
                else:
                    wave = 0.2 + 0.8 * (0.5 + 0.5 * math.sin(phase * 6.283))
                    rgb = scale_rgb(base_rgb, bri_factor * wave)
            elif mode in (4, 5, 17, 19):  # Glittering / Fluttering / Pulsating / Shuttle
                seed = self._sparkle_seeds[idx]
                twinkle = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(t * spd_factor * 2.5 + seed))
                if is_rainbow:
                    hue = (seed / 6.28 + t * 0.15) % 1.0
                    c = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(hue, 1.0, 1.0))
                    rgb = scale_rgb(c, bri_factor * twinkle)
                else:
                    rgb = scale_rgb(base_rgb, bri_factor * twinkle)
            else:  # Reactive modes (2, 3, 13, 14, 15) -> gentle idle + base color
                pulse = 0.65 + 0.35 * math.sin(t * 2.0 + nx * 3.0)
                c = tuple(int(v * 255) for v in colorsys.hsv_to_rgb((nx + t * 0.1) % 1.0, 1.0, 1.0)) if is_rainbow else base_rgb
                rgb = scale_rgb(c, bri_factor * pulse)

            hx = rgb_to_hex(*rgb)
            if sum(rgb) < 12:
                self.canvas.itemconfigure(glow, fill="#181C28")
                self.canvas.itemconfigure(cap, fill="#181C28", outline="#282F44")
                self.canvas.itemconfigure(txt, fill="#555E78")
            else:
                cap_rgb = blend_rgb(rgb, (16, 20, 30), 0.55)
                self.canvas.itemconfigure(glow, fill=hx)
                self.canvas.itemconfigure(cap, fill=rgb_to_hex(*cap_rgb), outline=hx)
                self.canvas.itemconfigure(txt, fill=rgb_to_hex(*blend_rgb(rgb, (255, 255, 255), 0.35)))

        # Animate Left & Right Side Light Strips (modes 32..36)
        sm = self.anim_side_mode
        for _is_left, seg_i, rect_id in self._side_items:
            if sm == 36:  # Off
                sc = (24, 28, 40)
            elif sm == 34:  # Static Blue
                sc = (0, 120, 255)
            elif sm == 35:  # Breathing cycle
                hue = (t * 0.14) % 1.0
                pulse = 0.15 + 0.85 * (0.5 + 0.5 * math.sin(t * 2.2))
                c = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(hue, 1.0, 1.0))
                sc = scale_rgb(c, pulse)
            elif sm == 33:  # Shift / Neon
                hue = (t * 0.25) % 1.0
                sc = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(hue, 1.0, 1.0))
            else:  # 32: Flowing Rainbow
                hue = (seg_i / 8.0 - t * 0.45) % 1.0
                sc = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(hue, 1.0, 1.0))
            self.canvas.itemconfigure(rect_id, fill=rgb_to_hex(*sc))
