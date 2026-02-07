import os
import sys
import subprocess
import customtkinter

def build():
    print("正在準備打包 MacroHub...")
    
    # 獲取 customtkinter 的路徑
    ctk_path = os.path.dirname(customtkinter.__file__)
    print(f"CustomTkinter 路徑: {ctk_path}")
    
    # 定義分隔符 (Windows 是 ;)
    sep = ";" if os.name == "nt" else ":"
    
    # 資源檔設定: 把 customtkinter 整個資料夾複製過去
    add_data = f"{ctk_path}{sep}customtkinter"
    
    # PyInstaller 命令（改用 onedir 模式以避免 DLL 問題）
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",  # 改為資料夾模式（更穩定）
        "--windowed", # 不顯示黑視窗 (GUI模式)
        "--name", "MacroHub",
        "--uac-admin", # 自動請求管理員權限
        "--add-data", add_data,
        "--hidden-import", "pynput.keyboard._win32",
        "--hidden-import", "pynput.mouse._win32",
        "--hidden-import", "pynput.keyboard",
        "--hidden-import", "pynput.mouse",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "keyboard",
        "--collect-all", "customtkinter",
        "--collect-all", "pystray",
        "--collect-all", "keyboard",
        "--noupx",  # 不使用 UPX 壓縮（避免相容性問題）
        "main.py"
    ]
    
    print("執行命令:", " ".join(cmd))
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ 打包完成！")
        print(f"請在 dist/MacroHub 資料夾中尋找 MacroHub.exe")
        print("\n📝 注意：")
        print("  - 整個 dist/MacroHub 資料夾都需要一起發布")
        print("  - 如果要給別人使用，請把整個資料夾壓縮成 ZIP")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包失敗: {e}")
    except FileNotFoundError:
        print("\n❌ 找不到 pyinstaller，請先執行: pip install pyinstaller")

if __name__ == "__main__":
    # 確保安裝了 pyinstaller
    try:
        import PyInstaller
    except ImportError:
        print("正在安裝 pyinstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        
    build()
