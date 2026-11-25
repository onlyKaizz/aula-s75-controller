"""
AULA S75 Pro Controller - Personal Studio Desktop GUI
Modern dark sidebar studio layout with live 80-key keyboard simulator,
embedded HSV color picker, per-key RGB painter, personal profiles, and USB diagnostics.
"""

from __future__ import annotations
import colorsys
import datetime
import threading
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Tuple
import customtkinter as ctk

from .device import AulaS75Device
from .layout_data import KEYBOARD_KEYS
from .protocol import LIGHT_MODE_SPECS, LIGHT_MODES
from .storage import (
    is_autostart_enabled,
    load_config,
    save_config,
    set_autostart,
)
from .widgets import HSVColorPicker, KeyboardPreviewCanvas, rgb_to_hex

CURATED_SWATCHES: List[Tuple[str, Tuple[int, int, int]]] = [
    ("Cam Studio", (255, 106, 0)),
    ("Cyan Neon",  (0, 229, 255)),
    ("Hồng Neon",  (255, 0, 110)),
    ("Tím Violet", (145, 45, 255)),
    ("Xanh Mint",  (0, 255, 136)),
    ("Đỏ Đậm",     (255, 30, 30)),
    ("Vàng Gold",  (255, 200, 0)),
    ("Trắng Tinh", (255, 255, 255)),
]

SLEEP_OPTIONS = {
    "Không tự tắt": 0,
    "1 phút": 1,
    "3 phút": 2,
    "5 phút": 3,
    "10 phút": 4,
    "30 phút": 5,
}


class AulaS75App(ctk.CTk):
    def __init__(
        self,
        device: Optional[AulaS75Device] = None,
        on_minimize_to_tray: Optional[Callable[[], None]] = None,
        on_profiles_updated: Optional[Callable[[List[dict]], None]] = None,
        start_minimized: bool = False,
    ):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.config_data = load_config()
        self.on_minimize_to_tray = on_minimize_to_tray
        self.on_profiles_updated = on_profiles_updated
        self._log_lines: List[str] = []

        self.device = device or AulaS75Device(log_callback=self._append_log_threadsafe)
        self.device.transport._log_cb = self._append_log_threadsafe

        # Load last state
        st = self.config_data["last_state"]
        self.state_mode: int = int(st.get("mode", 1))
        self.state_rgb: Tuple[int, int, int] = (
            int(st.get("r", 255)),
            int(st.get("g", 106)),
            int(st.get("b", 0)),
        )
        self.state_brightness: int = int(st.get("brightness", 5))
        self.state_speed: int = int(st.get("speed", 3))
        self.state_direction: int = int(st.get("direction", 0))
        self.state_colorful: int = int(st.get("colorful", 0))

        raw_pk = self.config_data.get("per_key_colors", {})
        self.per_key_colors: Dict[int, Tuple[int, int, int]] = {
            int(k): (int(v[0]), int(v[1]), int(v[2]))
            for k, v in raw_pk.items()
            if isinstance(v, list) and len(v) == 3
        }

        self._debounce_id: Optional[str] = None
        self._active_tab = "lighting"
        self._mode_buttons: Dict[int, ctk.CTkButton] = {}
        self._nav_buttons: Dict[str, ctk.CTkButton] = {}
        self._tab_frames: Dict[str, ctk.CTkFrame] = {}

        # Window config
        self.title("AULA S75 Pro — Personal RGB Studio")
        self.geometry("1120x780")
        self.minsize(1020, 720)
        self.configure(fg_color="#0E1015")
        self.protocol("WM_DELETE_WINDOW", self._on_close_window)

        self._build_layout()
        self._sync_ui_from_state()
        self._refresh_connection_status()
        self._poll_connection_loop()

        if start_minimized:
            self.withdraw()
            if self.config_data["app_settings"].get("apply_on_startup", True):
                self.after(600, lambda: self.apply_global_now(save=False))

    # ------------------------------------------------------------------
    # Layout & Navigation
    # ------------------------------------------------------------------
    def _build_layout(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(
            self, width=220, corner_radius=0, fg_color="#12151E", border_width=1, border_color="#1F2433"
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Brand
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(20, 14))
        ctk.CTkLabel(
            brand, text="AULA S75 PRO", font=ctk.CTkFont(size=19, weight="bold"), text_color="#FFFFFF"
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand, text="PERSONAL RGB STUDIO", font=ctk.CTkFont(size=10, weight="bold"), text_color="#00D4FF"
        ).pack(anchor="w")

        # Connection Card in Sidebar
        conn_card = ctk.CTkFrame(self.sidebar, fg_color="#181C28", corner_radius=10, border_width=1, border_color="#262D42")
        conn_card.pack(fill="x", padx=14, pady=(0, 16))
        self.conn_dot_lbl = ctk.CTkLabel(
            conn_card, text="● Đang kiểm tra...", font=ctk.CTkFont(size=12, weight="bold"), text_color="#F5B041"
        )
        self.conn_dot_lbl.pack(anchor="w", padx=12, pady=(10, 2))
        self.conn_detail_lbl = ctk.CTkLabel(
            conn_card, text="VID 0x0C45 | PID 0x800A", font=ctk.CTkFont(family="Consolas", size=10), text_color="#7D87A3"
        )
        self.conn_detail_lbl.pack(anchor="w", padx=12, pady=(0, 8))
        ctk.CTkButton(
            conn_card, text="Kiểm tra kết nối", height=26, font=ctk.CTkFont(size=11),
            fg_color="#23293B", hover_color="#2F3750", command=self._refresh_connection_status
        ).pack(fill="x", padx=10, pady=(0, 10))

        # Navigation Buttons
        nav_items = [
            ("lighting", "🎨  Hiệu ứng LED"),
            ("perkey",   "🎹  Tùy chỉnh từng phím"),
            ("profiles", "💾  Profiles cá nhân"),
            ("settings", "⚙️  Cài đặt & Chuẩn đoán"),
        ]
        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                height=38,
                corner_radius=8,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="transparent",
                hover_color="#1D2230",
                text_color="#A8B3CF",
                command=lambda k=key: self.switch_tab(k),
            )
            btn.pack(fill="x", padx=14, pady=3)
            self._nav_buttons[key] = btn

        # Sidebar bottom quick utilities
        bottom_util = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_util.pack(side="bottom", fill="x", padx=14, pady=16)

        ctk.CTkButton(
            bottom_util, text="🕒 Đồng bộ giờ LCD", height=32, corner_radius=8,
            fg_color="#1C2233", hover_color="#273047", font=ctk.CTkFont(size=12),
            command=self._on_sync_clock,
        ).pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            bottom_util, text="🌙 Tắt đèn nhanh", height=32, corner_radius=8,
            fg_color="#331B20", hover_color="#4D242C", text_color="#FF8A9B", font=ctk.CTkFont(size=12, weight="bold"),
            command=self.quick_turn_off,
        ).pack(fill="x")

        # Main Area Container + Bottom Status Strip
        right_shell = ctk.CTkFrame(self, fg_color="#0E1015", corner_radius=0)
        right_shell.pack(side="right", fill="both", expand=True)

        self.content_area = ctk.CTkFrame(right_shell, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True, padx=16, pady=(14, 6))

        # Status Bar
        status_bar = ctk.CTkFrame(right_shell, height=36, fg_color="#12151E", corner_radius=8, border_width=1, border_color="#1F2433")
        status_bar.pack(fill="x", padx=16, pady=(0, 12))
        status_bar.pack_propagate(False)
        self.status_lbl = ctk.CTkLabel(
            status_bar, text="Sẵn sàng.", font=ctk.CTkFont(size=12), text_color="#A8B3CF"
        )
        self.status_lbl.pack(side="left", padx=12)
        self.latency_lbl = ctk.CTkLabel(
            status_bar, text="", font=ctk.CTkFont(family="Consolas", size=11), text_color="#67728E"
        )
        self.latency_lbl.pack(side="right", padx=12)

        # Build Tabs
        self._build_tab_lighting()
        self._build_tab_perkey()
        self._build_tab_profiles()
        self._build_tab_settings()

        self.switch_tab("lighting")

    def switch_tab(self, tab_key: str):
        self._active_tab = tab_key
        for k, frame in self._tab_frames.items():
            if k == tab_key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
        for k, btn in self._nav_buttons.items():
            if k == tab_key:
                btn.configure(fg_color="#1E273B", text_color="#00D4FF")
            else:
                btn.configure(fg_color="transparent", text_color="#A8B3CF")

    # ------------------------------------------------------------------
    # TAB 1: Lighting Studio
    # ------------------------------------------------------------------
    def _build_tab_lighting(self):
        tab = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self._tab_frames["lighting"] = tab

        # Top: Interactive Animated Keyboard Preview
        self.preview_kbd = KeyboardPreviewCanvas(tab, interactive_paint=False, scale=1.12)
        self.preview_kbd.pack(fill="x", pady=(0, 12))

        # Bottom Split: Left = Modes & Parameters | Right = HSV Picker & Swatches
        bottom = ctk.CTkFrame(tab, fg_color="transparent")
        bottom.pack(fill="both", expand=True)

        # Left Panel: Mode Grid + Sliders
        left_panel = ctk.CTkFrame(bottom, fg_color="#141720", corner_radius=12, border_width=1, border_color="#252B3D")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ctk.CTkLabel(
            left_panel, text="CHỌN CHẾ ĐỘ HIỆU ỨNG (20 MODES)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#00D4FF"
        ).pack(anchor="w", padx=14, pady=(12, 6))

        mode_scroll = ctk.CTkScrollableFrame(left_panel, height=150, fg_color="#0E1017", corner_radius=8)
        mode_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        mode_scroll.grid_columnconfigure((0, 1), weight=1)

        for idx, (m_id, spec) in enumerate(LIGHT_MODE_SPECS.items()):
            r_idx = idx // 2
            c_idx = idx % 2
            btn = ctk.CTkButton(
                mode_scroll,
                text=f"{m_id:02d}. {spec['name']}",
                anchor="w",
                height=30,
                corner_radius=6,
                font=ctk.CTkFont(size=12),
                fg_color="#181C28",
                hover_color="#232A3D",
                text_color="#CBD4EA",
                command=lambda mid=m_id: self._select_mode(mid),
            )
            btn.grid(row=r_idx, column=c_idx, padx=4, pady=3, sticky="ew")
            self._mode_buttons[m_id] = btn

        # Effect Sliders & Options
        ctrl_card = ctk.CTkFrame(left_panel, fg_color="#1A1E2B", corner_radius=10)
        ctrl_card.pack(fill="x", padx=12, pady=(0, 12))

        # Color Mode Switch (Single vs Rainbow)
        cm_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        cm_row.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(cm_row, text="Kiểu phối màu:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        self.color_type_seg = ctk.CTkSegmentedButton(
            cm_row,
            values=["🎨 Đơn sắc RGB", "🌈 7 màu Cầu vồng"],
            command=self._on_color_type_change,
            selected_color="#0088CC",
            selected_hover_color="#00A6F5",
        )
        self.color_type_seg.pack(side="right")

        # Brightness
        b_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        b_row.pack(fill="x", padx=12, pady=(4, 0))
        ctk.CTkLabel(b_row, text="Độ sáng", font=ctk.CTkFont(size=12)).pack(side="left")
        self.bri_val_lbl = ctk.CTkLabel(b_row, text="5 / 5", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="#00D4FF")
        self.bri_val_lbl.pack(side="right")
        self.bri_slider = ctk.CTkSlider(
            ctrl_card, from_=1, to=5, number_of_steps=4, command=self._on_bri_change,
            button_color="#00D4FF", progress_color="#0095B6"
        )
        self.bri_slider.pack(fill="x", padx=12, pady=(2, 6))

        # Speed
        s_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        s_row.pack(fill="x", padx=12, pady=(2, 0))
        ctk.CTkLabel(s_row, text="Tốc độ hiệu ứng", font=ctk.CTkFont(size=12)).pack(side="left")
        self.spd_val_lbl = ctk.CTkLabel(s_row, text="3 / 5", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="#00D4FF")
        self.spd_val_lbl.pack(side="right")
        self.spd_slider = ctk.CTkSlider(
            ctrl_card, from_=1, to=5, number_of_steps=4, command=self._on_spd_change,
            button_color="#00D4FF", progress_color="#0095B6"
        )
        self.spd_slider.pack(fill="x", padx=12, pady=(2, 6))

        # Direction
        d_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        d_row.pack(fill="x", padx=12, pady=(2, 10))
        ctk.CTkLabel(d_row, text="Hướng chạy:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.dir_seg = ctk.CTkSegmentedButton(
            d_row, values=["Trái ➔ Phải", "Phải ➔ Trái"], command=self._on_dir_change,
            selected_color="#0088CC", selected_hover_color="#00A6F5"
        )
        self.dir_seg.pack(side="right")

        # Right Panel: Color Picker + Swatches + Apply
        right_panel = ctk.CTkFrame(bottom, width=320, fg_color="#141720", corner_radius=12, border_width=1, border_color="#252B3D")
        right_panel.pack(side="right", fill="y", padx=(8, 0))
        right_panel.pack_propagate(False)

        ctk.CTkLabel(
            right_panel, text="BẢNG MÀU RGB TÙY CHỌN",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#00D4FF"
        ).pack(anchor="w", padx=14, pady=(12, 6))

        self.color_picker = HSVColorPicker(
            right_panel, initial_rgb=self.state_rgb, on_change=self._on_picker_change
        )
        self.color_picker.pack(padx=12, pady=(0, 10))

        # Curated Swatches (2x4)
        swatch_box = ctk.CTkFrame(right_panel, fg_color="#1A1E2B", corner_radius=8)
        swatch_box.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(swatch_box, text="Màu nhanh (tự chuyển về Đơn sắc):", font=ctk.CTkFont(size=11), text_color="#8C96B2").pack(anchor="w", padx=10, pady=(6, 4))
        sw_grid = ctk.CTkFrame(swatch_box, fg_color="transparent")
        sw_grid.pack(padx=8, pady=(0, 8))
        for idx, (label, rgb) in enumerate(CURATED_SWATCHES):
            hx = rgb_to_hex(*rgb)
            b = ctk.CTkButton(
                sw_grid, text="", width=58, height=24, corner_radius=6,
                fg_color=hx, hover_color=hx, border_width=1, border_color="#3A4259",
                command=lambda c=rgb, n=label: self._pick_swatch(c, n)
            )
            b.grid(row=idx // 4, column=idx % 4, padx=4, pady=4)

        # Auto-apply + Apply Button
        self.auto_apply_var = ctk.BooleanVar(
            value=self.config_data["app_settings"].get("auto_apply_sliders", True)
        )
        ctk.CTkSwitch(
            right_panel, text="Tự áp dụng ngay khi chỉnh", variable=self.auto_apply_var,
            font=ctk.CTkFont(size=12), command=self._on_toggle_auto_apply
        ).pack(anchor="w", padx=14, pady=(0, 8))

        ctk.CTkButton(
            right_panel,
            text="⚡ ÁP DỤNG LÊN BÀN PHÍM",
            height=40,
            corner_radius=10,
            fg_color="#0088CC",
            hover_color="#00A6F5",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.apply_global_now(save=True),
        ).pack(fill="x", padx=12, pady=(0, 12))

    # ------------------------------------------------------------------
    # TAB 2: Per-Key RGB Painter
    # ------------------------------------------------------------------
    def _build_tab_perkey(self):
        tab = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self._tab_frames["perkey"] = tab

        self.perkey_kbd = KeyboardPreviewCanvas(
            tab, interactive_paint=True, on_paint_key=self._on_key_painted, scale=1.12
        )
        self.perkey_kbd.pack(fill="x", pady=(0, 12))
        self.perkey_kbd.set_per_key_colors(self.per_key_colors)

        bottom = ctk.CTkFrame(tab, fg_color="transparent")
        bottom.pack(fill="both", expand=True)

        # Left: Brush Picker
        brush_card = ctk.CTkFrame(bottom, width=300, fg_color="#141720", corner_radius=12, border_width=1, border_color="#252B3D")
        brush_card.pack(side="left", fill="y", padx=(0, 8))
        ctk.CTkLabel(brush_card, text="CỌ VẼ MÀU TỪNG PHÍM", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00D4FF").pack(anchor="w", padx=14, pady=(12, 6))
        self.brush_picker = HSVColorPicker(
            brush_card, initial_rgb=(255, 106, 0), on_change=self._on_brush_change
        )
        self.brush_picker.pack(padx=12, pady=(0, 12))

        # Right: Zone Tools & Apply
        tools_card = ctk.CTkFrame(bottom, fg_color="#141720", corner_radius=12, border_width=1, border_color="#252B3D")
        tools_card.pack(side="right", fill="both", expand=True, padx=(8, 0))
        ctk.CTkLabel(tools_card, text="CÔNG CỤ TÔ NHANH (QUICK ZONES)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00D4FF").pack(anchor="w", padx=16, pady=(12, 8))

        ctk.CTkLabel(
            tools_card,
            text="Mẹo: Nhấp hoặc giữ chuột kéo trực tiếp lên các phím ở hình phía trên để tô màu từng phím riêng lẻ.",
            font=ctk.CTkFont(size=12), text_color="#9AA5C4", wraplength=480, justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 12))

        grid = ctk.CTkFrame(tools_card, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 14))
        grid.grid_columnconfigure((0, 1, 2), weight=1)

        zone_actions = [
            ("🎮 Tô cụm WASD",       self._paint_wasd),
            ("⬆️ Tô phím Mũi tên",   self._paint_arrows),
            ("🔢 Tô hàng F1 - F12",  self._paint_frow),
            ("🖌️ Đổ màu toàn phím",  self._paint_all),
            ("🌈 Tô dải Cầu vồng",   self._paint_rainbow_gradient),
            ("🧹 Xóa hết (Tắt LED)", self._paint_clear),
        ]
        for idx, (lbl, cmd) in enumerate(zone_actions):
            ctk.CTkButton(
                grid, text=lbl, height=34, corner_radius=8,
                fg_color="#1E2436", hover_color="#2B344D", font=ctk.CTkFont(size=12),
                command=cmd
            ).grid(row=idx // 3, column=idx % 3, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(
            tools_card,
            text="⚡ ÁP DỤNG BẢNG MÀU TỪNG PHÍM (USER LIGHT)",
            height=42,
            corner_radius=10,
            fg_color="#0088CC",
            hover_color="#00A6F5",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._apply_perkey_now,
        ).pack(side="bottom", fill="x", padx=16, pady=16)

    # ------------------------------------------------------------------
    # TAB 3: Personal Profiles
    # ------------------------------------------------------------------
    def _build_tab_profiles(self):
        tab = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self._tab_frames["profiles"] = tab

        header_card = ctk.CTkFrame(tab, fg_color="#141720", corner_radius=12, border_width=1, border_color="#252B3D")
        header_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            header_card, text="LƯU CẤU HÌNH HIỆN TẠI THÀNH PROFILE CÁ NHÂN",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#00D4FF"
        ).pack(anchor="w", padx=16, pady=(12, 8))

        row = ctk.CTkFrame(header_card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 14))
        self.new_profile_entry = ctk.CTkEntry(
            row, placeholder_text="Nhập tên profile (vd: Cam Làm Việc, Gaming Tối...)", height=36,
            fg_color="#0E1017", border_color="#2E364D"
        )
        self.new_profile_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(
            row, text="➕ Lưu Profile mới", width=150, height=36,
            fg_color="#0088CC", hover_color="#00A6F5", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_new_profile
        ).pack(side="right")

        self.profiles_list_frame = ctk.CTkScrollableFrame(
            tab, fg_color="#141720", corner_radius=12, border_width=1, border_color="#252B3D"
        )
        self.profiles_list_frame.pack(fill="both", expand=True)
        self._render_profiles_list()

    def _render_profiles_list(self):
        for child in self.profiles_list_frame.winfo_children():
            child.destroy()

        profiles = self.config_data.get("profiles", [])
        if not profiles:
            ctk.CTkLabel(self.profiles_list_frame, text="Chưa có profile nào.", text_color="#7D87A3").pack(pady=30)
            return

        for idx, prof in enumerate(profiles):
            card = ctk.CTkFrame(self.profiles_list_frame, fg_color="#1A1E2B", corner_radius=10, border_width=1, border_color="#282F44")
            card.pack(fill="x", padx=10, pady=6)

            rgb = (prof.get("r", 255), prof.get("g", 106), prof.get("b", 0))
            hx = rgb_to_hex(*rgb) if not prof.get("colorful") else "#8A2BE2"
            dot = ctk.CTkFrame(card, width=32, height=32, corner_radius=8, fg_color=hx)
            dot.pack(side="left", padx=12, pady=10)
            dot.pack_propagate(False)

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=8)
            ctk.CTkLabel(info, text=prof["name"], font=ctk.CTkFont(size=14, weight="bold"), text_color="#FFFFFF").pack(anchor="w")
            m_name = LIGHT_MODES.get(prof.get("mode", 1), "Mode")
            c_txt = "7 màu Cầu vồng" if prof.get("colorful") else f"Đơn sắc {rgb_to_hex(*rgb)}"
            ctk.CTkLabel(
                info,
                text=f"{m_name}  •  {c_txt}  •  Sáng {prof.get('brightness', 5)}/5",
                font=ctk.CTkFont(size=11), text_color="#8C96B2"
            ).pack(anchor="w")

            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.pack(side="right", padx=12)
            ctk.CTkButton(
                btns, text="Áp dụng", width=86, height=30, fg_color="#0088CC", hover_color="#00A6F5",
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda p=prof: self.apply_profile(p)
            ).pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                btns, text="Xóa", width=54, height=30, fg_color="#331B20", hover_color="#4D242C", text_color="#FF8A9B",
                command=lambda i=idx: self._delete_profile(i)
            ).pack(side="left")

    # ------------------------------------------------------------------
    # TAB 4: Hardware Settings & Diagnostics
    # ------------------------------------------------------------------
    def _build_tab_settings(self):
        tab = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self._tab_frames["settings"] = tab

        top_split = ctk.CTkFrame(tab, fg_color="transparent")
        top_split.pack(fill="x", pady=(0, 12))

        # Left: Keyboard Hardware Settings
        hw_card = ctk.CTkFrame(top_split, fg_color="#141720", corner_radius=12, border_width=1, border_color="#252B3D")
        hw_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        ctk.CTkLabel(hw_card, text="CÀI ĐẶT PHẦN CỨNG BÀN PHÍM", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00D4FF").pack(anchor="w", padx=16, pady=(12, 10))

        ks = self.config_data["keyboard_settings"]
        self.win_lock_var = ctk.BooleanVar(value=ks.get("disable_win", False))
        self.alttab_lock_var = ctk.BooleanVar(value=ks.get("disable_alttab", False))
        self.altf4_lock_var = ctk.BooleanVar(value=ks.get("disable_altf4", False))

        ctk.CTkSwitch(hw_card, text="Khóa phím Windows (Gaming Mode)", variable=self.win_lock_var).pack(anchor="w", padx=16, pady=4)
        ctk.CTkSwitch(hw_card, text="Khóa tổ hợp Alt + Tab", variable=self.alttab_lock_var).pack(anchor="w", padx=16, pady=4)
        ctk.CTkSwitch(hw_card, text="Khóa tổ hợp Alt + F4", variable=self.altf4_lock_var).pack(anchor="w", padx=16, pady=4)

        slp_row = ctk.CTkFrame(hw_card, fg_color="transparent")
        slp_row.pack(fill="x", padx=16, pady=(10, 6))
        ctk.CTkLabel(slp_row, text="Tự tắt đèn khi không dùng:").pack(side="left")
        rev_sleep = {v: k for k, v in SLEEP_OPTIONS.items()}
        self.sleep_var = ctk.StringVar(value=rev_sleep.get(ks.get("sleep_time", 1), "1 phút"))
        ctk.CTkOptionMenu(slp_row, values=list(SLEEP_OPTIONS.keys()), variable=self.sleep_var, width=140).pack(side="right")

        deb_row = ctk.CTkFrame(hw_card, fg_color="transparent")
        deb_row.pack(fill="x", padx=16, pady=(4, 10))
        ctk.CTkLabel(deb_row, text="Mức phản hồi phím (Debounce 1-5):").pack(side="left")
        self.debounce_var = ctk.StringVar(value=str(ks.get("key_respondtime", 2)))
        ctk.CTkOptionMenu(deb_row, values=["1", "2", "3", "4", "5"], variable=self.debounce_var, width=80).pack(side="right")

        ctk.CTkButton(
            hw_card, text="💾 Lưu & Gửi cài đặt lên bàn phím", height=34,
            fg_color="#0088CC", hover_color="#00A6F5", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._apply_hw_settings
        ).pack(fill="x", padx=16, pady=(6, 14))

        # Right: Personal Windows App Preferences
        app_card = ctk.CTkFrame(top_split, fg_color="#141720", corner_radius=12, border_width=1, border_color="#252B3D")
        app_card.pack(side="right", fill="both", expand=True, padx=(8, 0))
        ctk.CTkLabel(app_card, text="TÙY CHỌN APP CÁ NHÂN (WINDOWS)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00D4FF").pack(anchor="w", padx=16, pady=(12, 10))

        as_cfg = self.config_data["app_settings"]
        self.autostart_var = ctk.BooleanVar(value=is_autostart_enabled())
        self.apply_start_var = ctk.BooleanVar(value=as_cfg.get("apply_on_startup", True))
        self.tray_close_var = ctk.BooleanVar(value=as_cfg.get("minimize_to_tray", True))

        ctk.CTkSwitch(
            app_card, text="Tự khởi động ẩn cùng Windows", variable=self.autostart_var,
            command=self._on_toggle_autostart
        ).pack(anchor="w", padx=16, pady=6)
        ctk.CTkSwitch(
            app_card, text="Tự áp dụng màu cuối cùng khi mở app", variable=self.apply_start_var,
            command=self._save_app_settings
        ).pack(anchor="w", padx=16, pady=6)
        ctk.CTkSwitch(
            app_card, text="Thu nhỏ xuống khay đồng hồ (Tray) khi bấm X", variable=self.tray_close_var,
            command=self._save_app_settings
        ).pack(anchor="w", padx=16, pady=6)

        ctk.CTkButton(
            app_card, text="🕒 Đồng bộ ngày giờ lên màn hình LCD phím", height=34,
            fg_color="#1E2436", hover_color="#2B344D", command=self._on_sync_clock
        ).pack(fill="x", padx=16, pady=(18, 14))

        # Bottom: Diagnostics Packet Log
        log_card = ctk.CTkFrame(tab, fg_color="#141720", corner_radius=12, border_width=1, border_color="#252B3D")
        log_card.pack(fill="both", expand=True)
        lh = ctk.CTkFrame(log_card, fg_color="transparent")
        lh.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(lh, text="NHẬT KÝ GIAO TIẾP USB HID (CHUẨN ĐOÁN ACK)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00D4FF").pack(side="left")
        ctk.CTkButton(lh, text="Xóa log", width=70, height=24, fg_color="#23293B", command=self._clear_log).pack(side="right")

        self.log_box = ctk.CTkTextbox(
            log_card, fg_color="#0A0C11", text_color="#9EE6B8",
            font=ctk.CTkFont(family="Consolas", size=11), corner_radius=8
        )
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(2, 12))
        self.log_box.configure(state="disabled")

    # ------------------------------------------------------------------
    # State Sync & Event Handlers
    # ------------------------------------------------------------------
    def _sync_ui_from_state(self):
        # Highlight selected mode button
        for m_id, btn in self._mode_buttons.items():
            if m_id == self.state_mode:
                btn.configure(fg_color="#006699", text_color="#FFFFFF")
            else:
                btn.configure(fg_color="#181C28", text_color="#CBD4EA")

        self.bri_slider.set(self.state_brightness)
        self.bri_val_lbl.configure(text=f"{self.state_brightness} / 5")
        self.spd_slider.set(self.state_speed)
        self.spd_val_lbl.configure(text=f"{self.state_speed} / 5")
        self.dir_seg.set("Phải ➔ Trái" if self.state_direction else "Trái ➔ Phải")
        self.color_type_seg.set("🌈 7 màu Cầu vồng" if self.state_colorful else "🎨 Đơn sắc RGB")
        self.color_picker.set_rgb(*self.state_rgb, notify=False)
        self._update_live_preview()

    def _update_live_preview(self):
        self.preview_kbd.set_preview_state(
            mode=self.state_mode,
            rgb=self.state_rgb,
            brightness=self.state_brightness,
            speed=self.state_speed,
            direction=self.state_direction,
            colorful=self.state_colorful,
        )

    def _select_mode(self, mode_id: int):
        self.state_mode = mode_id
        spec = LIGHT_MODE_SPECS.get(mode_id, {})
        # If mode inherently forces rainbow (6, 8), sync toggle cleanly; otherwise keep user's choice
        if not spec.get("colorful", False):
            self.state_colorful = 1 if mode_id in (6, 8) else 0
        self._sync_ui_from_state()
        self._trigger_debounced_apply()

    def _on_color_type_change(self, val: str):
        self.state_colorful = 1 if "Cầu vồng" in val else 0
        self._update_live_preview()
        self._trigger_debounced_apply()

    def _on_bri_change(self, val: float):
        self.state_brightness = int(round(val))
        self.bri_val_lbl.configure(text=f"{self.state_brightness} / 5")
        self._update_live_preview()
        self._trigger_debounced_apply()

    def _on_spd_change(self, val: float):
        self.state_speed = int(round(val))
        self.spd_val_lbl.configure(text=f"{self.state_speed} / 5")
        self._update_live_preview()
        self._trigger_debounced_apply()

    def _on_dir_change(self, val: str):
        self.state_direction = 1 if "Phải ➔ Trái" in val else 0
        self._update_live_preview()
        self._trigger_debounced_apply()

    def _on_picker_change(self, r: int, g: int, b: int, is_final: bool):
        self.state_rgb = (r, g, b)
        # Picking a specific RGB color automatically switches off Rainbow so you actually get that color!
        if self.state_colorful == 1 and self.state_mode not in (6, 8):
            self.state_colorful = 0
            self.color_type_seg.set("🎨 Đơn sắc RGB")
        if self.state_mode == 20:  # Wake from LED Off to Static
            self.state_mode = 1
            self._sync_ui_from_state()
        self._update_live_preview()
        if is_final:
            self._trigger_debounced_apply(delay_ms=60)

    def _pick_swatch(self, rgb: Tuple[int, int, int], _name: str):
        self.state_rgb = rgb
        self.state_colorful = 0
        if self.state_mode in (6, 8, 20):
            self.state_mode = 1
        self._sync_ui_from_state()
        self._trigger_debounced_apply(delay_ms=40)

    def _on_toggle_auto_apply(self):
        self.config_data["app_settings"]["auto_apply_sliders"] = bool(self.auto_apply_var.get())
        save_config(self.config_data)

    def _trigger_debounced_apply(self, delay_ms: int = 120):
        if not self.auto_apply_var.get():
            return
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(delay_ms, lambda: self.apply_global_now(save=True))

    def apply_global_now(self, save: bool = True):
        r, g, b = self.state_rgb
        params = {
            "mode": self.state_mode,
            "r": r,
            "g": g,
            "b": b,
            "brightness": self.state_brightness,
            "speed": self.state_speed,
            "direction": self.state_direction,
            "colorful": self.state_colorful,
        }
        if save:
            self.config_data["last_state"] = dict(params)
            save_config(self.config_data)

        self.set_status("Đang gửi cấu hình LED lên bàn phím...")

        def on_done(ok: bool, err: str):
            def ui_cb():
                if ok:
                    m_name = LIGHT_MODES.get(self.state_mode, f"Mode {self.state_mode}")
                    c_desc = "7 màu" if self.state_colorful else rgb_to_hex(r, g, b)
                    self.set_status(f"✓ Đã áp dụng: {m_name} • {c_desc} • Sáng {self.state_brightness}/5")
                    self.latency_lbl.configure(text=f"ACK OK ({self.device.transport.last_latency_ms:.0f} ms)")
                else:
                    self.set_status(f"✗ Lỗi: {err}", error=True)
                self._refresh_connection_status()

            self.after(0, ui_cb)

        self.device.enqueue_lighting(params, on_done=on_done)

    def quick_turn_off(self):
        self.state_mode = 20
        self._sync_ui_from_state()
        self.apply_global_now(save=True)

    # ------------------------------------------------------------------
    # Per-Key RGB Helpers
    # ------------------------------------------------------------------
    def _on_brush_change(self, r: int, g: int, b: int, _final: bool):
        self.perkey_kbd.brush_rgb = (r, g, b)

    def _on_key_painted(self, light_index: int, _key_name: str):
        self.per_key_colors[light_index] = self.perkey_kbd.brush_rgb

    def _paint_indices(self, indices: List[int], rgb: Optional[Tuple[int, int, int]] = None):
        c = rgb if rgb is not None else self.brush_picker.get_rgb()
        for idx in indices:
            self.per_key_colors[idx] = c
        self.perkey_kbd.set_per_key_colors(self.per_key_colors)

    def _paint_wasd(self):
        names = {"W", "A", "S", "D"}
        self._paint_indices([k["light_index"] for k in KEYBOARD_KEYS if k["name"] in names])

    def _paint_arrows(self):
        names = {"Up", "Down", "Left", "Right"}
        self._paint_indices([k["light_index"] for k in KEYBOARD_KEYS if k["name"] in names])

    def _paint_frow(self):
        self._paint_indices([k["light_index"] for k in KEYBOARD_KEYS if k["row_col"].startswith("0#")])

    def _paint_all(self):
        self._paint_indices([k["light_index"] for k in KEYBOARD_KEYS])

    def _paint_rainbow_gradient(self):
        for k in KEYBOARD_KEYS:
            hue = k["x"] / 605.0
            rgb = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(hue, 1.0, 1.0))
            self.per_key_colors[k["light_index"]] = rgb
        self.perkey_kbd.set_per_key_colors(self.per_key_colors)

    def _paint_clear(self):
        self.per_key_colors = {k["light_index"]: (0, 0, 0) for k in KEYBOARD_KEYS}
        self.perkey_kbd.set_per_key_colors(self.per_key_colors)

    def _apply_perkey_now(self):
        self.config_data["per_key_colors"] = {str(k): list(v) for k, v in self.per_key_colors.items()}
        save_config(self.config_data)
        self.set_status("Đang nạp bảng màu từng phím (576 bytes)...")

        def on_done(ok: bool, err: str):
            def ui_cb():
                if ok:
                    self.set_status(f"✓ Đã áp dụng bảng màu tùy chỉnh cho {len(self.per_key_colors)} phím!")
                    self.latency_lbl.configure(text=f"ACK OK ({self.device.transport.last_latency_ms:.0f} ms)")
                else:
                    self.set_status(f"✗ Lỗi Per-Key: {err}", error=True)
            self.after(0, ui_cb)

        self.device.enqueue_per_key(self.per_key_colors, slot=1, on_done=on_done)

    # ------------------------------------------------------------------
    # Profiles Management
    # ------------------------------------------------------------------
    def _save_new_profile(self):
        name = self.new_profile_entry.get().strip()
        if not name:
            self.set_status("⚠ Vui lòng nhập tên profile trước khi lưu.", error=True)
            return
        r, g, b = self.state_rgb
        prof = {
            "name": name,
            "kind": "global",
            "mode": self.state_mode,
            "r": r,
            "g": g,
            "b": b,
            "brightness": self.state_brightness,
            "speed": self.state_speed,
            "direction": self.state_direction,
            "colorful": self.state_colorful,
        }
        self.config_data.setdefault("profiles", []).append(prof)
        save_config(self.config_data)
        self.new_profile_entry.delete(0, "end")
        self._render_profiles_list()
        if self.on_profiles_updated:
            self.on_profiles_updated(self.config_data["profiles"])
        self.set_status(f"✓ Đã lưu profile mới: {name}")

    def apply_profile(self, prof: dict):
        self.state_mode = int(prof.get("mode", 1))
        self.state_rgb = (int(prof.get("r", 255)), int(prof.get("g", 106)), int(prof.get("b", 0)))
        self.state_brightness = int(prof.get("brightness", 5))
        self.state_speed = int(prof.get("speed", 3))
        self.state_direction = int(prof.get("direction", 0))
        self.state_colorful = int(prof.get("colorful", 0))
        self._sync_ui_from_state()
        self.apply_global_now(save=True)

    def _delete_profile(self, idx: int):
        profiles = self.config_data.get("profiles", [])
        if 0 <= idx < len(profiles):
            removed = profiles.pop(idx)
            save_config(self.config_data)
            self._render_profiles_list()
            if self.on_profiles_updated:
                self.on_profiles_updated(profiles)
            self.set_status(f"Đã xóa profile: {removed['name']}")

    # ------------------------------------------------------------------
    # Settings, Diagnostics & Tray
    # ------------------------------------------------------------------
    def _apply_hw_settings(self):
        ks = {
            "disable_win": bool(self.win_lock_var.get()),
            "disable_alttab": bool(self.alttab_lock_var.get()),
            "disable_altf4": bool(self.altf4_lock_var.get()),
            "fn_switch": False,
            "sleep_time": SLEEP_OPTIONS.get(self.sleep_var.get(), 1),
            "key_respondtime": int(self.debounce_var.get()),
        }
        self.config_data["keyboard_settings"] = ks
        save_config(self.config_data)
        self.set_status("Đang gửi cài đặt phần cứng...")

        def worker():
            try:
                ok = self.device.apply_settings(**ks)
                self.after(0, lambda: self.set_status("✓ Đã cập nhật cài đặt phần cứng!" if ok else "✗ Không nhận được ACK.", error=not ok))
            except Exception as exc:
                self.after(0, lambda: self.set_status(f"✗ Lỗi: {exc}", error=True))

        threading.Thread(target=worker, daemon=True).start()

    def _on_sync_clock(self):
        self.set_status("Đang đồng bộ đồng hồ lên màn hình LCD...")

        def worker():
            try:
                ok = self.device.sync_clock()
                self.after(0, lambda: self.set_status("✓ Đã đồng bộ ngày giờ lên LCD!" if ok else "✗ Đồng bộ thất bại.", error=not ok))
            except Exception as exc:
                self.after(0, lambda: self.set_status(f"✗ Lỗi đồng bộ giờ: {exc}", error=True))

        threading.Thread(target=worker, daemon=True).start()

    def _on_toggle_autostart(self):
        want = bool(self.autostart_var.get())
        if not set_autostart(want):
            self.autostart_var.set(is_autostart_enabled())
            self.set_status("✗ Không thể chỉnh Windows Registry startup.", error=True)
        else:
            self.set_status("✓ Đã bật tự khởi động cùng Windows." if want else "✓ Đã tắt tự khởi động cùng Windows.")

    def _save_app_settings(self):
        self.config_data["app_settings"]["apply_on_startup"] = bool(self.apply_start_var.get())
        self.config_data["app_settings"]["minimize_to_tray"] = bool(self.tray_close_var.get())
        save_config(self.config_data)

    def _refresh_connection_status(self):
        mode = self.device.get_connection_mode()
        if mode == "USB":
            self.conn_dot_lbl.configure(text="● Đã kết nối (USB)", text_color="#00FF88")
            self.conn_detail_lbl.configure(text="VID 0x0C45 • PID 0x800A • MI_03")
        elif mode == "2.4G":
            self.conn_dot_lbl.configure(text="● Kết nối 2.4G Dongle", text_color="#F5B041")
            self.conn_detail_lbl.configure(text="Cắm cáp USB để chỉnh LED ổn định")
        else:
            self.conn_dot_lbl.configure(text="○ Chưa kết nối", text_color="#FF5C72")
            self.conn_detail_lbl.configure(text="Hãy kiểm tra cáp USB Type-C")

    def _poll_connection_loop(self):
        self._refresh_connection_status()
        self.after(4000, self._poll_connection_loop)

    def set_status(self, text: str, error: bool = False):
        self.status_lbl.configure(text=text, text_color="#FF6B7D" if error else "#CBD4EA")

    def _append_log_threadsafe(self, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"

        def write():
            if not hasattr(self, "log_box"):
                return
            self.log_box.configure(state="normal")
            self.log_box.insert("end", line + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        try:
            self.after(0, write)
        except Exception:
            pass

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _on_close_window(self):
        if self.config_data["app_settings"].get("minimize_to_tray", True) and self.on_minimize_to_tray:
            self.withdraw()
            self.on_minimize_to_tray()
        else:
            self.destroy()
