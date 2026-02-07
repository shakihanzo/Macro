"""
全域熱鍵管理器 - 負責在背景監聽並觸發巨集
使用 keyboard 庫實現更穩定的鍵盤監聽
"""
import threading
import time
from typing import Dict, Callable, Optional
import keyboard


class HotkeyManager:
    """全域熱鍵管理器 - 使用 keyboard 庫"""
    
    def __init__(self):
        self.hotkeys: Dict[str, Callable] = {}
        self._is_running = False
        self._last_trigger_time: Dict[str, float] = {}
        self._cooldown = 0.3  # 300ms 冷卻時間，避免重複觸發
        self._registered_hooks: Dict[str, Callable] = {}
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False
    
    def register_hotkey(self, key_combo: str, callback: Callable):
        """
        註冊熱鍵
        key_combo: 按鍵組合字串，如 "f2", "ctrl+shift+a"
        callback: 觸發時執行的函數
        """
        normalized = key_combo.lower().replace(" ", "")
        self.hotkeys[normalized] = callback
        self._last_trigger_time[normalized] = 0
        
        # 如果已經在運行，立即註冊這個熱鍵
        if self._is_running:
            self._register_single_hotkey(normalized, callback)
    
    def _register_single_hotkey(self, key_combo: str, callback: Callable):
        """註冊單一熱鍵到 keyboard 庫"""
        def wrapper():
            current_time = time.time()
            last_time = self._last_trigger_time.get(key_combo, 0)
            
            # 冷卻檢查
            if current_time - last_time >= self._cooldown:
                self._last_trigger_time[key_combo] = current_time
                # 在新執行緒中執行回調以避免阻塞
                threading.Thread(target=callback, daemon=True).start()
        
        try:
            # 移除舊的鉤子（如果存在）
            if key_combo in self._registered_hooks:
                try:
                    keyboard.remove_hotkey(self._registered_hooks[key_combo])
                except:
                    pass
            
            # 註冊新鉤子
            hook = keyboard.add_hotkey(key_combo, wrapper, suppress=False)
            self._registered_hooks[key_combo] = hook
        except Exception as e:
            print(f"Error registering hotkey '{key_combo}': {e}")
    
    def unregister_hotkey(self, key_combo: str):
        """取消註冊熱鍵"""
        normalized = key_combo.lower().replace(" ", "")
        if normalized in self.hotkeys:
            del self.hotkeys[normalized]
        
        if normalized in self._registered_hooks:
            try:
                keyboard.remove_hotkey(self._registered_hooks[normalized])
                del self._registered_hooks[normalized]
            except:
                pass
    
    def clear_all_hotkeys(self):
        """清除所有熱鍵"""
        for key_combo in list(self._registered_hooks.keys()):
            try:
                keyboard.remove_hotkey(self._registered_hooks[key_combo])
            except:
                pass
        self._registered_hooks.clear()
        self.hotkeys.clear()
        self._last_trigger_time.clear()
    
    def _heartbeat_loop(self):
        """
        心跳循環 - 定期重新註冊熱鍵以防止 Windows 移除鉤子
        這是解決 Windows LowLevelHooksTimeout 問題的關鍵
        """
        while self._heartbeat_running:
            time.sleep(30)  # 每 30 秒檢查一次
            
            if not self._heartbeat_running:
                break
                
            try:
                # 重新註冊所有熱鍵
                for key_combo, callback in list(self.hotkeys.items()):
                    self._register_single_hotkey(key_combo, callback)
            except Exception as e:
                print(f"Heartbeat error: {e}")
    
    def start(self):
        """開始監聽熱鍵"""
        if self._is_running:
            return
        
        self._is_running = True
        
        # 註冊所有熱鍵
        for key_combo, callback in self.hotkeys.items():
            self._register_single_hotkey(key_combo, callback)
        
        # 啟動心跳執行緒
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
    
    def stop(self):
        """停止監聽熱鍵"""
        self._is_running = False
        self._heartbeat_running = False
        
        # 清除所有註冊的鉤子
        for key_combo in list(self._registered_hooks.keys()):
            try:
                keyboard.remove_hotkey(self._registered_hooks[key_combo])
            except:
                pass
        self._registered_hooks.clear()
    
    def is_running(self) -> bool:
        """檢查是否正在運行"""
        return self._is_running
    
    def get_registered_hotkeys(self) -> Dict[str, str]:
        """獲取所有已註冊的熱鍵"""
        return {k: str(v) for k, v in self.hotkeys.items()}
    
    def refresh_all_hotkeys(self):
        """手動刷新所有熱鍵（強制重新註冊）"""
        if not self._is_running:
            return
            
        for key_combo, callback in list(self.hotkeys.items()):
            self._register_single_hotkey(key_combo, callback)
