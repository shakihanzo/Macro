"""
巨集錄製器 - 負責錄製鍵盤和滑鼠動作
"""
import time
import threading
from pynput import keyboard, mouse
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from enum import Enum


class EventType(Enum):
    """事件類型"""
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"
    MOUSE_CLICK = "mouse_click"
    MOUSE_RELEASE = "mouse_release"
    MOUSE_MOVE = "mouse_move"
    MOUSE_SCROLL = "mouse_scroll"
    DELAY = "delay"  # 獨立的延遲事件


@dataclass
class MacroEvent:
    """巨集事件"""
    event_type: EventType
    timestamp: float
    delay: float = 0.0  # 與前一事件的延遲時間
    
    # 鍵盤相關
    key: Optional[str] = None
    key_code: Optional[int] = None
    
    # 滑鼠相關
    x: Optional[int] = None
    y: Optional[int] = None
    button: Optional[str] = None
    scroll_dx: Optional[int] = None
    scroll_dy: Optional[int] = None
    
    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "delay": self.delay,
            "key": self.key,
            "key_code": self.key_code,
            "x": self.x,
            "y": self.y,
            "button": self.button,
            "scroll_dx": self.scroll_dx,
            "scroll_dy": self.scroll_dy
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MacroEvent':
        """從字典建立事件"""
        return cls(
            event_type=EventType(data["event_type"]),
            timestamp=data["timestamp"],
            delay=data["delay"],
            key=data.get("key"),
            key_code=data.get("key_code"),
            x=data.get("x"),
            y=data.get("y"),
            button=data.get("button"),
            scroll_dx=data.get("scroll_dx"),
            scroll_dy=data.get("scroll_dy")
        )


@dataclass
class Macro:
    """巨集資料結構"""
    name: str
    events: List[MacroEvent] = field(default_factory=list)
    loop_count: int = 1  # 循環次數，0 表示無限
    loop_delay: float = 0.0  # 循環間隔
    trigger_key: Optional[str] = None  # 觸發按鍵
    target_window: str = ""  # 目標視窗標題（空字串為全域）
    created_time: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            "name": self.name,
            "events": [e.to_dict() for e in self.events],
            "loop_count": self.loop_count,
            "loop_delay": self.loop_delay,
            "trigger_key": self.trigger_key,
            "target_window": self.target_window,
            "created_time": self.created_time
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Macro':
        """從字典建立巨集"""
        return cls(
            name=data["name"],
            events=[MacroEvent.from_dict(e) for e in data["events"]],
            loop_count=data.get("loop_count", 1),
            loop_delay=data.get("loop_delay", 0.0),
            trigger_key=data.get("trigger_key"),
            target_window=data.get("target_window", ""),
            created_time=data.get("created_time", time.time())
        )
    
    @property
    def total_duration(self) -> float:
        """計算巨集總時長"""
        if not self.events:
            return 0.0
        return sum(e.delay for e in self.events)
    
    @property
    def event_count(self) -> int:
        """事件數量"""
        return len(self.events)


class MacroRecorder:
    """巨集錄製器"""
    
    def __init__(self):
        self.events: List[MacroEvent] = []
        self.is_recording = False
        self.record_keyboard = True
        self.record_mouse_clicks = True
        self.record_mouse_move = False  # 預設不錄製滑鼠移動（會產生太多事件）
        self.record_mouse_scroll = True
        
        self._start_time: float = 0.0
        self._last_event_time: float = 0.0
        
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._mouse_listener: Optional[mouse.Listener] = None
        
        # 追蹤已按下的按鍵和滑鼠按鈕（避免重複記錄）
        self._pressed_keys: set = set()
        self._pressed_buttons: set = set()
        
        # 回調函數
        self.on_event_recorded: Optional[Callable[[MacroEvent], None]] = None
        self.on_recording_stopped: Optional[Callable[[], None]] = None
        
        # 停止錄製的快捷鍵（預設 F10）
        self.stop_key = keyboard.Key.f10
    
    def start_recording(self):
        """開始錄製"""
        if self.is_recording:
            return
        
        self.events.clear()
        self._pressed_keys.clear()
        self._pressed_buttons.clear()
        self.is_recording = True
        self._start_time = None  # 等待第一個事件才開始計時
        self._last_event_time = None
        
        # 建立監聽器
        if self.record_keyboard:
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self._keyboard_listener.start()
        
        if self.record_mouse_clicks or self.record_mouse_scroll:
            self._mouse_listener = mouse.Listener(
                on_click=self._on_mouse_click if self.record_mouse_clicks else None,
                on_scroll=self._on_mouse_scroll if self.record_mouse_scroll else None
            )
            self._mouse_listener.start()
    
    def stop_recording(self) -> List[MacroEvent]:
        """停止錄製並返回事件列表"""
        if not self.is_recording:
            return self.events
        
        self.is_recording = False
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        
        if self.on_recording_stopped:
            self.on_recording_stopped()
        
        return self.events
    
    def create_macro(self, name: str) -> Macro:
        """從錄製的事件建立巨集"""
        return Macro(name=name, events=self.events.copy())
    
    def _add_event(self, event: MacroEvent):
        """添加事件"""
        current_time = time.time()
        
        # 如果是第一個事件，初始化開始時間
        if self._start_time is None:
            self._start_time = current_time
            self._last_event_time = current_time
            
        delay = current_time - self._last_event_time
        event.timestamp = current_time - self._start_time
        self._last_event_time = current_time
        
        # 如果延遲超過閾值（50ms），插入一個獨立的延遲事件
        min_delay_threshold = 0.05  # 50毫秒
        
        if delay > min_delay_threshold:
            delay_event = MacroEvent(
                event_type=EventType.DELAY,
                timestamp=event.timestamp - delay,
                delay=delay
            )
            self.events.append(delay_event)
            if self.on_event_recorded:
                self.on_event_recorded(delay_event)
        
        # 動作事件的 delay 設為 0
        event.delay = 0.0
        self.events.append(event)
        
        if self.on_event_recorded:
            self.on_event_recorded(event)
    
    def _get_key_string(self, key) -> str:
        """獲取按鍵字串表示"""
        try:
            # 優先使用 vk (虛擬鍵碼) 來識別按鍵，這樣即使按住 Shift 也能正確識別
            if hasattr(key, 'vk') and key.vk is not None:
                vk = key.vk
                # A-Z: VK 65-90
                if 65 <= vk <= 90:
                    return chr(vk).lower()
                # 0-9: VK 48-57
                elif 48 <= vk <= 57:
                    return chr(vk)
                # 小鍵盤 0-9: VK 96-105
                elif 96 <= vk <= 105:
                    return f"num{vk - 96}"
                # F1-F12: VK 112-123
                elif 112 <= vk <= 123:
                    return f"f{vk - 111}"
                # 小鍵盤特殊鍵
                elif vk == 106:  # Numpad *
                    return "num_multiply"
                elif vk == 107:  # Numpad +
                    return "num_add"
                elif vk == 109:  # Numpad -
                    return "num_subtract"
                elif vk == 110:  # Numpad . (Del)
                    return "num_decimal"
                elif vk == 111:  # Numpad /
                    return "num_divide"
                elif vk == 144:  # Num Lock
                    return "num_lock"
            
            # 如果有 char 屬性，使用小寫
            if hasattr(key, 'char') and key.char:
                return key.char.lower()
            
            # 否則使用字串表示
            return str(key)
        except AttributeError:
            return str(key)
    
    def _on_key_press(self, key):
        """鍵盤按下事件"""
        # 檢查是否為停止鍵
        if key == self.stop_key:
            self.stop_recording()
            return False
        
        if not self.is_recording:
            return
        
        key_str = self._get_key_string(key)
        
        # 如果按鍵已經被按下，忽略重複的按下事件
        if key_str in self._pressed_keys:
            return
        
        # 標記按鍵為已按下
        self._pressed_keys.add(key_str)
        
        event = MacroEvent(
            event_type=EventType.KEY_PRESS,
            timestamp=0,
            key=key_str
        )
        self._add_event(event)
    
    def _on_key_release(self, key):
        """鍵盤釋放事件"""
        if not self.is_recording:
            return
        
        # 檢查是否為停止鍵
        if key == self.stop_key:
            return
        
        key_str = self._get_key_string(key)
        
        # 從追蹤集合中移除（即使不在集合中也不報錯）
        self._pressed_keys.discard(key_str)
        
        event = MacroEvent(
            event_type=EventType.KEY_RELEASE,
            timestamp=0,
            key=key_str
        )
        self._add_event(event)
    
    def _on_mouse_click(self, x, y, button, pressed):
        """滑鼠點擊事件"""
        if not self.is_recording:
            return
        
        button_str = str(button)
        
        if pressed:
            # 如果按鈕已經被按下，忽略重複
            if button_str in self._pressed_buttons:
                return
            self._pressed_buttons.add(button_str)
        else:
            # 釋放時從集合移除
            self._pressed_buttons.discard(button_str)
        
        event = MacroEvent(
            event_type=EventType.MOUSE_CLICK if pressed else EventType.MOUSE_RELEASE,
            timestamp=0,
            x=None,  # 不記錄座標
            y=None,  # 不記錄座標
            button=button_str
        )
        self._add_event(event)

    # 移除滑鼠移動監聽
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """滑鼠滾輪事件"""
        if not self.is_recording:
            return
        
        event = MacroEvent(
            event_type=EventType.MOUSE_SCROLL,
            timestamp=0,
            x=None,  # 不記錄座標
            y=None,  # 不記錄座標
            scroll_dx=dx,
            scroll_dy=dy
        )
        self._add_event(event)
        self._add_event(event)
