"""
Build script to package AULA S75 Pro Controller into a standalone Windows .exe
"""

import subprocess
import sys
import os

def build_exe():
    print("[*] Bắt đầu đóng gói AULA S75 Pro Controller thành Windows .exe ...")
    project_root = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(project_root, "src", "main.py")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "AulaS75Controller",
        "--collect-all", "customtkinter",
        "--hidden-import", "PIL._tkinter_finder",
        "--paths", project_root,
        main_py
    ]

    print(f"[*] Đang thực thi lệnh: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=project_root)
    if result.returncode == 0:
        exe_path = os.path.join(project_root, "dist", "AulaS75Controller.exe")
        print("\n[+] ĐÓNG GÓI THÀNH CÔNG!")
        print(f"[+] Đường dẫn file thực thi: {exe_path}")
    else:
        print(f"\n[-] Đóng gói thất bại với mã lỗi: {result.returncode}")

if __name__ == "__main__":
    build_exe()
