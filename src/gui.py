"""
AULA S75 Pro Controller - GUI Module
Modern Dark Mode Desktop Interface using CustomTkinter
"""

import threading
import tkinter as tk
from tkinter import colorchooser, messagebox
import customtkinter as ctk
from PIL import Image

from .protocol import LIGHT_MODES
from .device import AulaS75Device

# Modern Color Presets
PRESET_COLORS = [
    ("#00FFFF", "Cyan"),
    ("#FF0055", "Neon Pink"),
    ("#7B00FF", "Purple"),
    ("#00FF66", "Mint Green"),
    ("#FF8800", "Amber Orange"),
    ("#0088FF", "Sky Blue"),
    ("#FF0000", "Red"),
    ("#FFFFFF", "Pure White"),
    ("#FFD700", "Gold"),
    ("#FF00FF", "Magenta"),
]

class AulaS75App(ctk.CTk):
    def __init__(self, on_minimize_to_tray=None):
        super().__init__()

        self.on_minimize_to_tray = on_minimize_to_tray
        self.device = AulaS75Device()

        # Current Lighting State
        self.current_r = 0
        self.current_g = 255
        self.current_b = 255
        self.current_hex = "#00FFFF"
        self.current_mode = 1
        self.brightness = 5
        self.speed = 3
        self.direction = 0
        self.colorful = 0
        self.auto_apply = True

        self._debounce_timer = None

        # Window Setup
        self.title("AULA S75 Pro Controller")
        self.geometry("780x680")
        self.minsize(720, 620)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Custom close protocol (minimize to tray if callback provided)
        self.protocol("WM_DELETE_WINDOW", self.handle_close)

        self._build_ui()
        self.check_device_status()

    def handle_close(self):
        if self.on_minimize_to_tray:
            self.withdraw()
            self.on_minimize_to_tray()
        else:
            self.destroy()

    def _build_ui(self):
        # Top Header Bar (Device Status & Refresh)
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a1c23")
        header_frame.pack(fill="x", padx=16, pady=(16, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text="AULA S75 Pro Control Center",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff"
        )
        title_label.pack(side="left", padx=16, pady=12)

        self.status_badge = ctk.CTkLabel(
            header_frame,
            text=" Đang kiểm tra... ",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#333333",
            corner_radius=6,
            text_color="#cccccc"
        )
        self.status_badge.pack(side="right", padx=(6, 16), pady=12)

        refresh_btn = ctk.CTkButton(
            header_frame,
            text="🔄 Làm mới",
            width=90,
            height=28,
            font=ctk.CTkFont(size=12),
            command=self.check_device_status
        )
        refresh_btn.pack(side="right", padx=6, pady=12)

        # Main Content Panes (Left: Modes & Effects, Right: Colors & Presets)
        main_pane = ctk.CTkFrame(self, fg_color="transparent")
        main_pane.pack(fill="both", expand=True, padx=16, pady=6)

        left_col = ctk.CTkFrame(main_pane, corner_radius=10, fg_color="#1e212b")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=0)

        right_col = ctk.CTkFrame(main_pane, corner_radius=10, fg_color="#1e212b")
        right_col.pack(side="right", fill="both", expand=True, padx=(8, 0), pady=0)

        # --- LEFT COLUMN: Lighting Modes & Sliders ---
        ctk.CTkLabel(
            left_col,
            text="✨ Hiệu ứng LED (Light Mode)",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#00ffff"
        ).pack(anchor="w", padx=16, pady=(14, 8))

        # Mode Dropdown
        self.mode_var = ctk.StringVar(value=f"1: {LIGHT_MODES[1]}")
        mode_options = [f"{k}: {v}" for k, v in LIGHT_MODES.items()]
        self.mode_dropdown = ctk.CTkOptionMenu(
            left_col,
            values=mode_options,
            variable=self.mode_var,
            width=320,
            height=34,
            command=self.on_mode_change
        )
        self.mode_dropdown.pack(padx=16, pady=(0, 16), fill="x")

        # Sliders Frame
        sliders_box = ctk.CTkFrame(left_col, fg_color="#262936", corner_radius=8)
        sliders_box.pack(fill="x", padx=16, pady=(0, 14))

        # Brightness Slider (1-5)
        b_header = ctk.CTkFrame(sliders_box, fg_color="transparent")
        b_header.pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(b_header, text="Độ sáng (Brightness)", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        self.brightness_label = ctk.CTkLabel(b_header, text="Mức 5 (Tối đa)", text_color="#00ffff")
        self.brightness_label.pack(side="right")

        self.brightness_slider = ctk.CTkSlider(
            sliders_box,
            from_=1,
            to=5,
            number_of_steps=4,
            command=self.on_brightness_change
        )
        self.brightness_slider.set(5)
        self.brightness_slider.pack(fill="x", padx=12, pady=(2, 12))

        # Speed Slider (1-5)
        s_header = ctk.CTkFrame(sliders_box, fg_color="transparent")
        s_header.pack(fill="x", padx=12, pady=(4, 2))
        ctk.CTkLabel(s_header, text="Tốc độ hiệu ứng (Speed)", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        self.speed_label = ctk.CTkLabel(s_header, text="Mức 3", text_color="#00ffff")
        self.speed_label.pack(side="right")

        self.speed_slider = ctk.CTkSlider(
            sliders_box,
            from_=1,
            to=5,
            number_of_steps=4,
            command=self.on_speed_change
        )
        self.speed_slider.set(3)
        self.speed_slider.pack(fill="x", padx=12, pady=(2, 14))

        # Direction Selection
        dir_box = ctk.CTkFrame(left_col, fg_color="#262936", corner_radius=8)
        dir_box.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(dir_box, text="Hướng hiệu ứng (Direction)", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.dir_seg = ctk.CTkSegmentedButton(
            dir_box,
            values=["Trái sang Phải ➡️", "Phải sang Trái ⬅️"],
            command=self.on_direction_change
        )
        self.dir_seg.set("Trái sang Phải ➡️")
        self.dir_seg.pack(fill="x", padx=12, pady=(0, 12))

        # Auto Apply Checkbox
        self.auto_apply_var = ctk.BooleanVar(value=True)
        auto_apply_chk = ctk.CTkSwitch(
            left_col,
            text="Tự động áp dụng khi thay đổi",
            variable=self.auto_apply_var,
            font=ctk.CTkFont(size=13)
        )
        auto_apply_chk.pack(anchor="w", padx=18, pady=(4, 10))

        # --- RIGHT COLUMN: Color Selection & Presets ---
        ctk.CTkLabel(
            right_col,
            text="🎨 Màu sắc (Color Palette)",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#00ffff"
        ).pack(anchor="w", padx=16, pady=(14, 8))

        # Current Color Preview Box
        color_preview_frame = ctk.CTkFrame(right_col, fg_color="#262936", corner_radius=8)
        color_preview_frame.pack(fill="x", padx=16, pady=(0, 14))

        p_inner = ctk.CTkFrame(color_preview_frame, fg_color="transparent")
        p_inner.pack(fill="x", padx=12, pady=12)

        self.color_sample = ctk.CTkLabel(
            p_inner,
            text="",
            width=50,
            height=50,
            corner_radius=8,
            fg_color=self.current_hex
        )
        self.color_sample.pack(side="left", padx=(0, 12))

        labels_frame = ctk.CTkFrame(p_inner, fg_color="transparent")
        labels_frame.pack(side="left", fill="both", expand=True)

        self.color_hex_label = ctk.CTkLabel(
            labels_frame,
            text=f"Mã màu: {self.current_hex}",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        self.color_hex_label.pack(fill="x")

        self.color_rgb_label = ctk.CTkLabel(
            labels_frame,
            text=f"RGB: ({self.current_r}, {self.current_g}, {self.current_b})",
            font=ctk.CTkFont(size=12),
            text_color="#aaaaaa",
            anchor="w"
        )
        self.color_rgb_label.pack(fill="x")

        pick_btn = ctk.CTkButton(
            right_col,
            text="🎨 Mở bảng chọn màu...",
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.open_color_picker
        )
        pick_btn.pack(fill="x", padx=16, pady=(0, 14))

        # Rainbow / Colorful Toggle
        self.colorful_var = ctk.BooleanVar(value=False)
        self.colorful_switch = ctk.CTkSwitch(
            right_col,
            text="🌈 Hiệu ứng đa sắc / Cầu vồng (Rainbow)",
            variable=self.colorful_var,
            command=self.on_colorful_toggle,
            font=ctk.CTkFont(size=13)
        )
        self.colorful_switch.pack(anchor="w", padx=18, pady=(0, 14))

        # Preset Palette Grid
        ctk.CTkLabel(
            right_col,
            text="Màu gợi ý nhanh:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=16, pady=(4, 6))

        palette_grid = ctk.CTkFrame(right_col, fg_color="#262936", corner_radius=8)
        palette_grid.pack(fill="x", padx=16, pady=(0, 14))

        # 2 rows x 5 columns of preset buttons
        for idx, (color_hex, name) in enumerate(PRESET_COLORS):
            row = idx // 5
            col = idx % 5
            btn = ctk.CTkButton(
                palette_grid,
                text="",
                width=34,
                height=34,
                corner_radius=6,
                fg_color=color_hex,
                hover_color="#ffffff",
                command=lambda c=color_hex: self.set_preset_color(c)
            )
            btn.grid(row=row, column=col, padx=8, pady=8)

        # Bottom Action Bar
        bottom_bar = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a1c23")
        bottom_bar.pack(fill="x", padx=16, pady=(8, 16))

        self.status_message = ctk.CTkLabel(
            bottom_bar,
            text="Sẵn sàng tùy chỉnh.",
            font=ctk.CTkFont(size=12),
            text_color="#888888"
        )
        self.status_message.pack(side="left", padx=16, pady=12)

        off_btn = ctk.CTkButton(
            bottom_bar,
            text="🌙 Tắt đèn",
            width=100,
            height=34,
            fg_color="#442222",
            hover_color="#662222",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.turn_off_lights
        )
        off_btn.pack(side="right", padx=12, pady=10)

        apply_btn = ctk.CTkButton(
            bottom_bar,
            text="⚡ ÁP DỤNG NGAY",
            width=140,
            height=34,
            fg_color="#0088cc",
            hover_color="#00aaff",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.apply_current_settings
        )
        apply_btn.pack(side="right", padx=(0, 6), pady=10)

    def check_device_status(self):
        """Check USB connection and update badge."""
        connected = self.device.is_connected()
        if connected:
            self.status_badge.configure(
                text=" ● Đã kết nối AULA S75 Pro ",
                fg_color="#104a25",
                text_color="#00ff66"
            )
            self.set_status("Đã kết nối thành công với AULA S75 Pro qua USB.")
        else:
            self.status_badge.configure(
                text=" ○ Chưa kết nối ",
                fg_color="#4a1a1a",
                text_color="#ff5555"
            )
            self.set_status("Chưa tìm thấy bàn phím. Vui lòng cắm dây cáp USB.")

    def set_status(self, text: str):
        self.status_message.configure(text=text)

    def open_color_picker(self):
        color = colorchooser.askcolor(
            color=self.current_hex,
            title="Chọn màu cho AULA S75 Pro"
        )
        if color and color[0]:
            r, g, b = [int(v) for v in color[0]]
            hex_val = color[1].upper()
            self.update_color(r, g, b, hex_val)
            self.trigger_auto_apply()

    def set_preset_color(self, hex_val: str):
        hex_clean = hex_val.lstrip("#")
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        self.update_color(r, g, b, hex_val)
        self.trigger_auto_apply()

    def update_color(self, r: int, g: int, b: int, hex_val: str):
        self.current_r = r
        self.current_g = g
        self.current_b = b
        self.current_hex = hex_val
        self.color_sample.configure(fg_color=hex_val)
        self.color_hex_label.configure(text=f"Mã màu: {hex_val}")
        self.color_rgb_label.configure(text=f"RGB: ({r}, {g}, {b})")

    def on_mode_change(self, choice: str):
        mode_id = int(choice.split(":")[0])
        self.current_mode = mode_id
        self.trigger_auto_apply()

    def on_brightness_change(self, val: float):
        level = int(round(val))
        self.brightness = level
        desc = " (Tối đa)" if level == 5 else (" (Yếu nhất)" if level == 1 else "")
        self.brightness_label.configure(text=f"Mức {level}{desc}")
        self.trigger_auto_apply()

    def on_speed_change(self, val: float):
        level = int(round(val))
        self.speed = level
        desc = " (Nhanh nhất)" if level == 5 else (" (Chậm nhất)" if level == 1 else "")
        self.speed_label.configure(text=f"Mức {level}{desc}")
        self.trigger_auto_apply()

    def on_direction_change(self, val: str):
        self.direction = 0 if "Trái sang Phải" in val else 1
        self.trigger_auto_apply()

    def on_colorful_toggle(self):
        self.colorful = 1 if self.colorful_var.get() else 0
        self.trigger_auto_apply()

    def trigger_auto_apply(self):
        if not self.auto_apply_var.get():
            return
        # Debounce to prevent flooding USB HID buffer
        if self._debounce_timer:
            self.after_cancel(self._debounce_timer)
        self._debounce_timer = self.after(150, self.apply_current_settings)

    def apply_current_settings(self):
        """Asynchronously send settings to keyboard."""
        mode_id = self.current_mode
        r, g, b = self.current_r, self.current_g, self.current_b
        bright = self.brightness
        spd = self.speed
        direct = self.direction
        colorf = self.colorful

        def worker():
            try:
                success = self.device.apply_lighting(
                    mode=mode_id,
                    r=r,
                    g=g,
                    b=b,
                    brightness=bright,
                    speed=spd,
                    direction=direct,
                    colorful=colorf
                )
                if success:
                    mode_name = LIGHT_MODES.get(mode_id, f"Mode {mode_id}")
                    self.after(0, lambda: self.set_status(f"✓ Đã áp dụng: {mode_name} | Màu: ({r}, {g}, {b})"))
                else:
                    self.after(0, lambda: self.set_status("⚠ Không nhận được phản hồi ACK từ bàn phím."))
            except Exception as e:
                self.after(0, lambda: self.set_status(f"✗ Lỗi khi gửi lệnh: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def turn_off_lights(self):
        def worker():
            try:
                self.device.turn_off_lighting()
                self.after(0, lambda: self.set_status("✓ Đã tắt đèn bàn phím."))
            except Exception as e:
                self.after(0, lambda: self.set_status(f"✗ Lỗi: {e}"))

        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    app = AulaS75App()
    app.mainloop()
