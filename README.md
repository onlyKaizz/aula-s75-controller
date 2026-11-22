# AULA S75 Pro Controller 🎮🌈

Phần mềm mã nguồn mở tùy chỉnh đèn LED RGB và cấu hình bàn phím cơ **AULA S75 Pro** trên Windows, thay thế phần mềm OEM chính hãng nặng nề và hạn chế.

![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6.svg)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-1f6aa5.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## ✨ Tính năng nổi bật

- 🎨 **Tùy chỉnh màu sắc trực quan**: Hỗ trợ bảng chọn màu RGB tự do (Color Picker) + bảng màu preset hiện đại (Cyberpunk Cyan, Neon Pink, Purple, Mint Green, Gold,...).
- ✨ **20 Chế độ hiệu ứng LED**: Static (Tĩnh), Single On/Off, Glittering, Fluttering, Colourful, Breathing, Spectrum, Scrolling, Rolling, Rotating, Explode, Launch, Ripples, Flowing, Pulsating, Tilt, Shuttle, LED Off.
- ⚡ **Điều khiển thông số thời gian thực**:
  - Độ sáng (Brightness): 5 cấp độ (1 - 5)
  - Tốc độ hiệu ứng (Speed): 5 cấp độ (1 - 5)
  - Hướng hiệu ứng (Direction): Trái sang Phải / Phải sang Trái
  - Chế độ Đa sắc / Cầu vồng (Rainbow spectrum toggle)
- 📌 **Chạy nền trên Khay hệ thống (System Tray)**: Thu nhỏ ứng dụng xuống khay đồng hồ Windows khi đóng cửa sổ, hỗ trợ menu chuột phải tắt/bật nhanh hiệu ứng.
- 🚀 **Giao diện hiện đại (Modern Dark Theme)**: Thiết kế bằng CustomTkinter mượt mà, thân thiện.
- 📦 **Đóng gói thành file `.exe` duy nhất**: Không cần cài đặt Python trên máy khác, chỉ cần tải về và chạy ngay.

---

## 🔌 Thông số phần cứng & Giao thức HID

- **Thiết bị**: Bàn phím cơ AULA S75 Pro (Chế độ cắm dây USB)
- **Vendor ID (VID)**: `0x0C45` (Sonix Technology Co., Ltd.)
- **Product ID (PID)**: `0x800A`
- **HID Interface**: Interface 3 (`UsagePage: 0xFF13`, `Usage: 0x0001`)

### Cấu trúc gói lệnh HID (Feature Reports 65 bytes):
1. **Handshake 1**: `[0x00, 0x04, 0x18] + [0x00] * 62` (Chờ phản hồi xác thực `report[4] == 1`).
2. **Handshake 2**: `[0x00, 0x04, 0x13, 0, 0, 0, 0, 0, 0, 1] + [0x00] * 54`.
3. **Lệnh đổi Mode (0x80)**: Byte 0 là `0x80`, Byte 9 là `mode_id` (1 - 20), Byte 14..15 là magic word `0x55AA`.
4. **Bảng màu Per-Key (576 bytes)**: 9 gói 64 bytes (`0x04, 0x23`), chứa mảng màu từng phím (`[key_index, R, G, B]`).
5. **Cấu hình thuộc tính**: Byte 0 là `mode_id`, Byte 1..3 là `[R, G, B]`, Byte 8 là `brightness`, Byte 9 là `speed`, Byte 10 là `direction`, Byte 11 là `colorful`.
6. **Apply & Finish**: `[0x04, 0x02]` và `[0x04, 0xF0]`.

---

## 🛠️ Hướng dẫn cài đặt & Chạy từ mã nguồn

### Yêu cầu:
- Windows 10/11
- Python 3.10 trở lên

### Các bước thực hiện:
```bash
# 1. Clone mã nguồn từ GitHub
git clone https://github.com/onlyKaizz/aula-s75-controller.git
cd aula-s75-controller

# 2. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt

# 3. Khởi chạy ứng dụng
python src/main.py
```

---

## 📦 Hướng dẫn đóng gói thành ứng dụng Windows `.exe`

Chạy lệnh PyInstaller sau trong thư mục dự án:
```powershell
python build.py
```
Hoặc dùng lệnh trực tiếp:
```powershell
pyinstaller --noconsole --onefile --name "AulaS75Controller" --collect-all customtkinter src/main.py
```
File ứng dụng `AulaS75Controller.exe` sẽ được tạo trong thư mục `dist/`.

---

## 🤝 Đóng góp & Bản quyền
Mã nguồn phát triển phục vụ cộng đồng bàn phím cơ AULA S75 Pro. Mọi đóng góp (Pull Request, Issue) đều được chào đón!
Giấy phép: MIT License.
