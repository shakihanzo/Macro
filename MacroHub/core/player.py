"""
巨集播放器 - 負責播放錄製的巨集
"""
import time
import threading
from typing import Optional, Callable
from pynput import keyboard, mouse
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController

from .recorder import Macro, MacroEvent, EventType


class MacroPlayer:
    """巨集播放器"""
    
    def __init__(self):
        self.keyboard = KeyboardController()
        self.mouse = MouseController()
        
        self.is_playing = False
        self.is_paused = False
        self._stop_requested = False
        self._play_thread: Optional[threading.Thread] = None
        
        # 追蹤目前按住的按鍵和滑鼠按鈕（用於緊急停止時釋放）
        self._pressed_keys: set = set()
        self._pressed_buttons: set = set()
        
        # 播放設定
        self.speed_multiplier: float = 1.0  # 播放速度倍率
        self.ignore_delays: bool = False  # 是否忽略延遲
        
        # 回調函數
        self.on_play_started: Optional[Callable[[Macro], None]] = None
        self.on_play_stopped: Optional[Callable[[], None]] = None
        self.on_event_played: Optional[Callable[[MacroEvent, int], None]] = None
        self.on_loop_completed: Optional[Callable[[int], None]] = None
        self.on_emergency_stop: Optional[Callable[[], None]] = None
        
        # 停止播放的快捷鍵
        self.stop_key = keyboard.Key.f10
        self._keyboard_listener: Optional[keyboard.Listener] = None
    
    def _parse_key(self, key_str: str):
        """解析按鍵字串為 pynput Key 對象"""
        if not key_str:
            return None
            
        # 移除 Key. 前綴
        if key_str.startswith("Key."):
            key_name = key_str[4:]
            try:
                return getattr(Key, key_name)
            except AttributeError:
                return key_str
        
        # 小鍵盤數字 (num0 - num9)
        if key_str.startswith("num") and len(key_str) == 4 and key_str[3].isdigit():
            try:
                num = int(key_str[3])
                # 使用 VK 碼模擬小鍵盤
                from pynput.keyboard import KeyCode
                return KeyCode.from_vk(96 + num)
            except:
                pass
        
        # 小鍵盤特殊鍵
        numpad_special = {
            "num_multiply": 106,  # *
            "num_add": 107,       # +
            "num_subtract": 109,  # -
            "num_decimal": 110,   # . (Del)
            "num_divide": 111,    # /
            "num_lock": 144,      # Num Lock
        }
        if key_str in numpad_special:
            from pynput.keyboard import KeyCode
            return KeyCode.from_vk(numpad_special[key_str])
        
        # F1-F12
        if key_str.lower().startswith("f") and len(key_str) <= 3:
            try:
                f_num = int(key_str[1:])
                if 1 <= f_num <= 12:
                    return getattr(Key, key_str.lower())
            except:
                pass
        
        # 單個字符（支援大小寫）
        if len(key_str) == 1:
            return key_str.lower()
        
        # 嘗試特殊鍵
        try:
            return getattr(Key, key_str.lower())
        except AttributeError:
            return key_str
    
    def _parse_mouse_button(self, button_str: str) -> Button:
        """解析滑鼠按鈕字串"""
        if "left" in button_str.lower():
            return Button.left
        elif "right" in button_str.lower():
            return Button.right
        elif "middle" in button_str.lower():
            return Button.middle
        return Button.left
    
    def _execute_event(self, event: MacroEvent):
        """執行單個事件"""
        try:
            # DELAY 事件不需要執行動作，只需等待（在 _play_loop 中處理）
            if event.event_type == EventType.DELAY:
                return
            
            if event.event_type == EventType.KEY_PRESS:
                key = self._parse_key(event.key)
                self._pressed_keys.add(key)  # 追蹤按住的按鍵
                self.keyboard.press(key)
                time.sleep(0.005)  # 5ms 確保按鍵被識別
            
            elif event.event_type == EventType.KEY_RELEASE:
                key = self._parse_key(event.key)
                self._pressed_keys.discard(key)  # 從追蹤中移除
                self.keyboard.release(key)
                time.sleep(0.005)  # 5ms 確保按鍵被識別
            
            elif event.event_type == EventType.MOUSE_CLICK:
                # 直接在當前位置點擊，不移動
                button = self._parse_mouse_button(event.button)
                self._pressed_buttons.add(button)  # 追蹤按住的按鈕
                self.mouse.press(button)
                time.sleep(0.005)
            
            elif event.event_type == EventType.MOUSE_RELEASE:
                # 直接在當前位置釋放
                button = self._parse_mouse_button(event.button)
                self._pressed_buttons.discard(button)  # 從追蹤中移除
                self.mouse.release(button)
                time.sleep(0.005)
            
            elif event.event_type == EventType.MOUSE_MOVE:
                pass # 忽略所有移動事件
            
            elif event.event_type == EventType.MOUSE_SCROLL:
                # 直接滾動，不移動
                if event.scroll_dx is not None and event.scroll_dy is not None:
                    self.mouse.scroll(event.scroll_dx, event.scroll_dy)
                time.sleep(0.01)
        
        except Exception as e:
            print(f"執行事件時發生錯誤: {e}")
    
    def _play_loop(self, macro: Macro):
        """播放循環"""
        loop_count = macro.loop_count
        current_loop = 0
        
        while not self._stop_requested:
            # 檢查循環次數
            if loop_count > 0 and current_loop >= loop_count:
                break
            
            # 播放所有事件
            for i, event in enumerate(macro.events):
                if self._stop_requested:
                    break
                
                # 暫停處理
                while self.is_paused and not self._stop_requested:
                    time.sleep(0.1)
                
                if self._stop_requested:
                    break
                
                # 延遲處理
                if not self.ignore_delays and event.delay > 0:
                    delay = event.delay / self.speed_multiplier
                    time.sleep(delay)
                
                # 執行事件
                self._execute_event(event)
                
                if self.on_event_played:
                    self.on_event_played(event, i)
            
            current_loop += 1
            
            if self.on_loop_completed:
                self.on_loop_completed(current_loop)
            
            # 循環延遲
            if not self._stop_requested and (loop_count == 0 or current_loop < loop_count):
                if macro.loop_delay > 0:
                    time.sleep(macro.loop_delay / self.speed_multiplier)
        
        self.is_playing = False
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        
        if self.on_play_stopped:
            self.on_play_stopped()
    
    def _on_key_press(self, key):
        """監聽停止鍵"""
        if key == self.stop_key:
            self.stop()
            return False
    
    def play(self, macro: Macro):
        """開始播放巨集"""
        if self.is_playing:
            self.stop()
        
        self.is_playing = True
        self.is_paused = False
        self._stop_requested = False
        
        # 啟動停止鍵監聽
        self._keyboard_listener = keyboard.Listener(on_press=self._on_key_press)
        self._keyboard_listener.start()
        
        if self.on_play_started:
            self.on_play_started(macro)
        
        # 在新執行緒中播放
        self._play_thread = threading.Thread(target=self._play_loop, args=(macro,))
        self._play_thread.daemon = True
        self._play_thread.start()
    
    def stop(self):
        """停止播放"""
        self._stop_requested = True
        self.is_paused = False
        # 停止時自動釋放按鍵，避免卡鍵
        self.release_all_keys()
    
    def pause(self):
        """暫停播放"""
        if self.is_playing:
            self.is_paused = True
    
    def resume(self):
        """繼續播放"""
        if self.is_playing:
            self.is_paused = False
    
    def toggle_pause(self):
        """切換暫停狀態"""
        if self.is_playing:
            self.is_paused = not self.is_paused
    
    def release_all_keys(self):
        """釋放所有按住的按鍵和滑鼠按鈕"""
        # 釋放所有追蹤的按鍵
        for key in list(self._pressed_keys):
            try:
                self.keyboard.release(key)
            except:
                pass
        self._pressed_keys.clear()
        
        # 釋放所有追蹤的滑鼠按鈕
        for button in list(self._pressed_buttons):
            try:
                self.mouse.release(button)
            except:
                pass
        self._pressed_buttons.clear()
        
        # 額外釋放常見的修飾鍵（以防萬一）
        common_keys = [Key.ctrl, Key.ctrl_l, Key.ctrl_r,
                       Key.alt, Key.alt_l, Key.alt_r,
                       Key.shift, Key.shift_l, Key.shift_r,
                       Key.cmd, Key.cmd_l, Key.cmd_r]
        for key in common_keys:
            try:
                self.keyboard.release(key)
            except:
                pass
    
    def emergency_stop(self):
        """緊急停止：停止所有巨集並釋放所有按鍵"""
        # 立即停止播放
        self._stop_requested = True
        self.is_paused = False
        self.is_playing = False
        
        # 釋放所有按鍵
        self.release_all_keys()
        
        # 停止監聽器
        if self._keyboard_listener:
            try:
                self._keyboard_listener.stop()
            except:
                pass
            self._keyboard_listener = None
        
        # 觸發回調
        if self.on_emergency_stop:
            self.on_emergency_stop()
