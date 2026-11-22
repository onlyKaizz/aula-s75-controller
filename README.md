# AULA S75 Pro Controller

An open-source Windows application to customize RGB lighting and configuration for the **AULA S75 Pro** mechanical keyboard.

## Project Goals
- Lightweight desktop application (built with Python & CustomTkinter, compiled to a single `.exe`).
- Direct USB HID control without needing clunky official drivers.
- Custom lighting presets, per-key RGB coloring, and real-time audio/screen reactive effects.
- Background execution via Windows System Tray.

## Target Hardware Specifications
- **Device**: AULA S75 Pro (Wired mode)
- **Vendor ID (VID)**: `0x0C45`
- **Product ID (PID)**: `0x800A`

## Setup & Development
1. Clone this repository:
   ```bash
   git clone https://github.com/onlyKaizz/aula-s75-controller.git
   cd aula-s75-controller
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run device probe:
   ```bash
   python src/device.py
   ```
