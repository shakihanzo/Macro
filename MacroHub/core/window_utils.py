import ctypes

def get_active_window_title() -> str:
    """獲取當前活動視窗的標題"""
    try:
        # 獲取當前視窗句柄
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        
        # 獲取標題長度
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
            
        # 建立緩衝區
        buff = ctypes.create_unicode_buffer(length + 1)
        
        # 獲取標題
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        
        return buff.value
    except Exception:
        return ""
