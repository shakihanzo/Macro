"""
按鍵偵測工具 - 用於偵測按鍵的實際 VK 碼
按 ESC 退出
"""
from pynput import keyboard

def on_press(key):
    print(f"按下: {key}")
    
    if hasattr(key, 'vk'):
        print(f"  VK 碼: {key.vk}")
    if hasattr(key, 'char'):
        print(f"  字元: {key.char}")
    if hasattr(key, 'name'):
        print(f"  名稱: {key.name}")
    
    # 完整物件資訊
    print(f"  類型: {type(key)}")
    print(f"  完整: {repr(key)}")
    print()
    
    if key == keyboard.Key.esc:
        print("已退出")
        return False

print("按鍵偵測工具")
print("請嘗試按下小鍵盤的 Del (.) 鍵")
print("按 ESC 退出")
print("-" * 40)

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
