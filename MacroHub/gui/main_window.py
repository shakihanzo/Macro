"""
MacroHub 主視窗 - 現代化深色主題 GUI（增強版）
新增功能：即時錄製顯示、事件編輯、全域熱鍵、系統托盤
"""
import os
import sys
import threading
import customtkinter as ctk
from tkinter import messagebox, filedialog
from typing import Optional
import time
import pystray
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recorder import MacroRecorder, Macro, MacroEvent, EventType
from core.player import MacroPlayer
from core.manager import MacroManager
from core.hotkey_manager import HotkeyManager
from core import window_utils

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")  # 使用綠色作為基礎

# CMD 風格常數
CMD_BG = "#000000"       # 純黑背景
CMD_FG = "#000000"       # 稍微淺一點的黑色（用於區塊）
CMD_TEXT = "#cccccc"     # 淺灰文字（主要）
CMD_ACCENT = "#00ff00"   # 終端機綠（強調/按鈕）
CMD_BORDER = "#00ff00"   # 綠色邊框
CMD_HOVER = "#003300"    # 深綠（懸停）
CMD_FONT_FAMILY = "Consolas"

# 修改全域預設字體
# 注意：CustomTkinter 沒有直接的全域字體設定，我們將在元件中使用常數


class EventEditorDialog(ctk.CTkToplevel):
    """事件編輯對話框"""
    
    def __init__(self, parent, event: MacroEvent = None, insert_mode=False):
        super().__init__(parent)
        self.title("編輯事件" if event else "新增事件")
        self.geometry("400x350")
        self.resizable(False, False)
        self.configure(fg_color="#0a0a0f")
        
        self.event = event
        self.result = None
        self.insert_mode = insert_mode
        
        self._create_ui()
        self.grab_set()
        self.focus_force()
    
    def _create_ui(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 事件類型
        ctk.CTkLabel(main, text="事件類型", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.type_var = ctk.StringVar(value="delay")
        type_frame = ctk.CTkFrame(main, fg_color="transparent")
        type_frame.pack(fill="x", pady=(5, 15))
        
        types = [("延遲", "delay"), ("按鍵按下", "key_press"), ("按鍵釋放", "key_release"),
                 ("滑鼠點擊", "mouse_click"), ("滑鼠釋放", "mouse_release")]
        for text, val in types:
            ctk.CTkRadioButton(type_frame, text=text, variable=self.type_var, value=val,
                              command=self._on_type_change).pack(side="left", padx=5)
        
        # 延遲時間
        self.delay_frame = ctk.CTkFrame(main, fg_color="transparent")
        self.delay_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(self.delay_frame, text="延遲 (毫秒)").pack(anchor="w")
        self.delay_entry = ctk.CTkEntry(self.delay_frame, width=150)
        self.delay_entry.insert(0, str(int(self.event.delay * 1000)) if self.event else "100")
        self.delay_entry.pack(anchor="w", pady=5)
        
        # 按鍵
        self.key_frame = ctk.CTkFrame(main, fg_color="transparent")
        ctk.CTkLabel(self.key_frame, text="按鍵").pack(anchor="w")
        self.key_entry = ctk.CTkEntry(self.key_frame, width=150)
        if self.event and self.event.key:
            self.key_entry.insert(0, self.event.key)
        self.key_entry.pack(anchor="w", pady=5)
        
        # 滑鼠座標
        self.mouse_frame = ctk.CTkFrame(main, fg_color="transparent")
        coord_frame = ctk.CTkFrame(self.mouse_frame, fg_color="transparent")
        coord_frame.pack(anchor="w")
        ctk.CTkLabel(coord_frame, text="X:").pack(side="left")
        self.x_entry = ctk.CTkEntry(coord_frame, width=80)
        self.x_entry.insert(0, str(self.event.x) if self.event and self.event.x else "0")
        self.x_entry.pack(side="left", padx=5)
        ctk.CTkLabel(coord_frame, text="Y:").pack(side="left", padx=(10,0))
        self.y_entry = ctk.CTkEntry(coord_frame, width=80)
        self.y_entry.insert(0, str(self.event.y) if self.event and self.event.y else "0")
        self.y_entry.pack(side="left", padx=5)
        
        self.btn_var = ctk.StringVar(value="left")
        btn_frame = ctk.CTkFrame(self.mouse_frame, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=10)
        for txt, val in [("左鍵", "left"), ("右鍵", "right"), ("中鍵", "middle")]:
            ctk.CTkRadioButton(btn_frame, text=txt, variable=self.btn_var, value=val).pack(side="left", padx=5)
        
        # 按鈕
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        ctk.CTkButton(btn_frame, text="確定", fg_color="#22c55e", command=self._confirm).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="取消", fg_color="#666", command=self.destroy).pack(side="left")
        
        self._on_type_change()
    
    def _on_type_change(self):
        t = self.type_var.get()
        self.key_frame.pack_forget()
        self.mouse_frame.pack_forget()
        if t in ["key_press", "key_release"]:
            self.key_frame.pack(fill="x", pady=10)
        elif t in ["mouse_click", "mouse_release"]:
            self.mouse_frame.pack(fill="x", pady=10)
    
    def _confirm(self):
        try:
            delay = float(self.delay_entry.get()) / 1000
            t = self.type_var.get()
            
            if t == "delay":
                self.result = MacroEvent(EventType.DELAY, 0, delay=delay)
            elif t == "key_press":
                self.result = MacroEvent(EventType.KEY_PRESS, 0, delay=delay, key=self.key_entry.get())
            elif t == "key_release":
                self.result = MacroEvent(EventType.KEY_RELEASE, 0, delay=delay, key=self.key_entry.get())
            elif t == "mouse_click":
                self.result = MacroEvent(EventType.MOUSE_CLICK, 0, delay=delay,
                                        x=int(self.x_entry.get()), y=int(self.y_entry.get()),
                                        button=f"Button.{self.btn_var.get()}")
            elif t == "mouse_release":
                self.result = MacroEvent(EventType.MOUSE_RELEASE, 0, delay=delay,
                                        x=int(self.x_entry.get()), y=int(self.y_entry.get()),
                                        button=f"Button.{self.btn_var.get()}")
            self.destroy()
        except ValueError:
            messagebox.showerror("錯誤", "請輸入有效數值")


class RecordingOverlay(ctk.CTkToplevel):
    """錄製時的即時顯示視窗"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("錄製中")
        self.geometry("350x500+50+50")
        self.attributes("-topmost", True)
        self.configure(fg_color="#0a0a0f")
        self.overrideredirect(False)
        
        header = ctk.CTkFrame(self, fg_color="#1a1a25", height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        ctk.CTkLabel(header, text="🔴 錄製中 - 按 F10 停止", font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#ef4444").pack(pady=15)
        
        self.events_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.events_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.event_count = 0
    
    def add_event(self, event: MacroEvent):
        self.event_count += 1
        icons = {
            EventType.KEY_PRESS: "⌨️↓", EventType.KEY_RELEASE: "⌨️↑",
            EventType.MOUSE_CLICK: "🖱️↓", EventType.MOUSE_RELEASE: "🖱️↑",
            EventType.MOUSE_MOVE: "🖱️→", EventType.MOUSE_SCROLL: "🖱️⟳",
            EventType.DELAY: "⏱️"
        }
        icon = icons.get(event.event_type, "❓")
        
        if event.event_type == EventType.DELAY:
            desc = f"等待 {event.delay*1000:.0f} ms"
        elif event.event_type in [EventType.KEY_PRESS, EventType.KEY_RELEASE]:
            desc = event.key
        elif event.event_type in [EventType.MOUSE_CLICK, EventType.MOUSE_RELEASE]:
            desc = f"{event.button} ({event.x},{event.y})"
        else:
            desc = str(event.event_type.value)
        
        item = ctk.CTkFrame(self.events_frame, fg_color="#12121a", corner_radius=5, height=28)
        item.pack(fill="x", pady=1)
        item.pack_propagate(False)
        
        ctk.CTkLabel(item, text=f"{self.event_count}. {icon} {desc}", font=ctk.CTkFont(size=11),
                    anchor="w").pack(side="left", padx=10)
        
        self.events_frame._parent_canvas.yview_moveto(1.0)


class MacroHubApp(ctk.CTk):
    """MacroHub 主應用程式"""
    
    def __init__(self):
        super().__init__()
        self.title("🎮 MacroHub - 通用巨集管理器")
        self.geometry("1200x800")
        self.minsize(900, 600)
        self.configure(fg_color=CMD_BG)
        
        self.recorder = MacroRecorder()
        self.player = MacroPlayer()
        
        # 決定巨集儲存路徑
        if getattr(sys, 'frozen', False):
            # 如果是打包後的 EXE，儲存在 EXE 同級目錄
            base_path = os.path.dirname(sys.executable)
        else:
            # 開發環境
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.manager = MacroManager(os.path.join(base_path, "macros"))
        self.hotkey_manager = HotkeyManager()
        
        self.selected_macro: Optional[Macro] = None
        self.recording_overlay: Optional[RecordingOverlay] = None
        self.tray_icon = None
        
        # 拖放排序相關
        self.drag_start_idx = None
        self.drag_item = None
        self.event_items = []  # 儲存事件項目的參考
        
        # 多選和剪貼簿
        self.selected_indices = set()
        self.clipboard_events = []
        
        self._setup_callbacks()
        self._create_ui()
        self._refresh_macro_list()
        self._setup_hotkeys()
        self._start_health_check()
        
        # 綁定鍵盤快捷鍵
        self.bind("<Up>", self._move_event_up)
        self.bind("<Down>", self._move_event_down)
        self.bind("<Delete>", self._delete_event_key)
        self.bind("<Control-c>", self._copy_events)
        self.bind("<Control-x>", self._cut_events)
        self.bind("<Control-v>", self._paste_events)
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_callbacks(self):
        self.recorder.on_event_recorded = self._on_event_recorded
        self.recorder.on_recording_stopped = self._on_recording_stopped
        self.player.on_play_started = self._on_play_started
        self.player.on_play_stopped = self._on_play_stopped
        self.player.on_emergency_stop = self._on_emergency_stop
    
    
    def _start_health_check(self):
        """啟動健康檢查循環"""
        self._check_health()
        
    def _check_health(self):
        """定期檢查核心組件狀態"""
        # 檢查熱鍵管理器狀態
        try:
            if not self.hotkey_manager.is_running():
                print("Hotkey manager is not running. Starting...")
                self.hotkey_manager.start()
            else:
                # 強制刷新熱鍵以防止 Windows 移除鉤子
                self.hotkey_manager.refresh_all_hotkeys()
        except Exception as e:
            print(f"Health check warning: {e}")
           
        # 每 60 秒檢查一次（配合 keyboard 庫的心跳機制）
        self.after(60000, self._check_health)

    def _setup_hotkeys(self):
        """設定全域熱鍵"""
        for macro in self.manager.get_all_macros():
            if macro.trigger_key:
                self.hotkey_manager.register_hotkey(macro.trigger_key, lambda m=macro: self._trigger_macro(m))
        
        # 註冊緊急停止鍵（Escape）
        self.hotkey_manager.register_hotkey("escape", self._emergency_stop)
        
        self.hotkey_manager.start()
    
    def _trigger_macro(self, macro: Macro):
        """通過熱鍵觸發巨集"""
        # 檢查目標視窗
        if macro.target_window:
            current_title = window_utils.get_active_window_title()
            if macro.target_window.lower() not in current_title.lower():
                return
                
        if not self.player.is_playing:
            self.player.play(macro)
    
    def _emergency_stop(self):
        """緊急停止所有巨集並釋放按鍵"""
        self.player.emergency_stop()
        # 同時停止錄製
        if self.recorder.is_recording:
            self.recorder.stop_recording()
    
    def _on_emergency_stop(self):
        """緊急停止回調"""
        def update_ui():
            self.status_indicator.configure(text="🛑 緊急停止", text_color="#ef4444")
            self.play_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            # 2 秒後恢復正常狀態
            self.after(2000, lambda: self.status_indicator.configure(text="● 待命中", text_color="#22c55e"))
        self.after(0, update_ui)
    
    def _create_ui(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        self._create_header()
        
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, pady=(20, 0))
        
        self._create_macro_list_panel()
        self._create_detail_panel()
    
    def _create_header(self):
        header = ctk.CTkFrame(self.main_container, fg_color=CMD_BG, corner_radius=0, 
                             border_width=1, border_color=CMD_BORDER, height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=25, pady=15)
        
        ctk.CTkLabel(title_frame, text="[ 系統: MACROHUB ]", font=ctk.CTkFont(family=CMD_FONT_FAMILY, size=24, weight="bold"),
                    text_color=CMD_ACCENT).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="> 狀態: 線上", font=ctk.CTkFont(family=CMD_FONT_FAMILY, size=12),
                    text_color=CMD_TEXT).pack(anchor="w")
        
        # 最小化到托盤按鈕
        ctk.CTkButton(header, text="[ _ ]", width=50, height=30, fg_color=CMD_BG,
                      border_width=1, border_color=CMD_BORDER, text_color=CMD_TEXT,
                     hover_color=CMD_HOVER, command=self._minimize_to_tray).pack(side="right", padx=10)
        
        self.status_frame = ctk.CTkFrame(header, fg_color="transparent")
        self.status_frame.pack(side="right", padx=15)
        
        self.status_indicator = ctk.CTkLabel(self.status_frame, text="● 待命", font=ctk.CTkFont(family=CMD_FONT_FAMILY, size=14),
                                            text_color=CMD_ACCENT)
        self.status_indicator.pack()
        ctk.CTkLabel(self.status_frame, text="[F10]:停止 [ESC]:急停", font=ctk.CTkFont(family=CMD_FONT_FAMILY, size=11),
                    text_color=CMD_TEXT).pack()
    
    def _create_macro_list_panel(self):
        left_panel = ctk.CTkFrame(self.content_frame, fg_color=CMD_FG, corner_radius=0, 
                                 border_width=1, border_color=CMD_BORDER, width=350)
        left_panel.pack(side="left", fill="y", padx=(0, 15))
        left_panel.pack_propagate(False)
        
        list_header = ctk.CTkFrame(left_panel, fg_color="transparent")
        list_header.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(list_header, text="📁 我的巨集", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        ctk.CTkButton(list_header, text="+ 新增", width=70, height=30, fg_color="#6366f1",
                     hover_color="#4f46e5", command=self._start_recording).pack(side="right")
        
        self.macro_list_frame = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self.macro_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 15))
        
        bottom = ctk.CTkFrame(left_panel, fg_color="transparent")
        bottom.pack(fill="x", padx=15, pady=15)
        ctk.CTkButton(bottom, text="📥 匯入", width=100, height=35, fg_color="#1f1f2e",
                     command=self._import_macro).pack(side="left")
        ctk.CTkButton(bottom, text="📤 匯出", width=100, height=35, fg_color="#1f1f2e",
                     command=self._export_macro).pack(side="right")
    
    def _create_detail_panel(self):
        right_panel = ctk.CTkFrame(self.content_frame, fg_color="#12121a", corner_radius=15)
        right_panel.pack(side="right", fill="both", expand=True)
        
        self.no_selection_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self.no_selection_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(self.no_selection_frame, text="🎯", font=ctk.CTkFont(size=64)).pack(pady=(100, 20))
        ctk.CTkLabel(self.no_selection_frame, text="選擇一個巨集或開始錄製", font=ctk.CTkFont(size=16),
                    text_color="#666").pack()
        ctk.CTkButton(self.no_selection_frame, text="🔴 開始錄製", font=ctk.CTkFont(size=14),
                     fg_color="#ef4444", height=45, width=200, command=self._start_recording).pack(pady=30)
        
        self.detail_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self._create_top_section()
        self._create_control_section()
        self._create_events_section()
    
    def _create_top_section(self):
        """單行緊湊設定區域"""
        top = ctk.CTkFrame(self.detail_frame, fg_color=CMD_FG, corner_radius=0,
                          border_width=1, border_color=CMD_BORDER)
        top.pack(fill="x", padx=20, pady=(15, 8))
        
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=10)
        
        # 巨集名稱（較小）
        ctk.CTkLabel(row, text="名稱", font=ctk.CTkFont(size=11), text_color="#888").pack(side="left")
        self.macro_name_entry = ctk.CTkEntry(row, font=ctk.CTkFont(size=12), height=30, width=150,
                                            fg_color="#12121a", border_color="#333")
        self.macro_name_entry.pack(side="left", padx=(5, 15))
        
        # 熱鍵
        ctk.CTkLabel(row, text="熱鍵", font=ctk.CTkFont(size=11), text_color="#888").pack(side="left")
        self.hotkey_entry = ctk.CTkEntry(row, height=30, width=80, fg_color="#12121a", border_color="#333",
                                        placeholder_text="F2")
        self.hotkey_entry.pack(side="left", padx=(5, 15))
        
        # 播放設定
        for label, attr, default, suffix in [("循環", "loop_count", "1", ""),
                                              ("間隔", "loop_delay", "0", "s"),
                                              ("速度", "speed", "1.0", "x")]:
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=11), text_color="#888").pack(side="left")
            entry = ctk.CTkEntry(row, width=45, height=30, fg_color="#12121a", border_color="#333")
            entry.insert(0, default)
            entry.pack(side="left", padx=(3, 0))
            setattr(self, f"{attr}_entry", entry)
            if suffix:
                ctk.CTkLabel(row, text=suffix, font=ctk.CTkFont(size=10), text_color="#666").pack(side="left", padx=(1, 5))
            else:
                ctk.CTkLabel(row, text="", width=10).pack(side="left", padx=(0, 5))
        
        # 統計資訊
        # 統計資訊
        self.stats_label = ctk.CTkLabel(row, text="📊 0 事件", font=ctk.CTkFont(size=11), text_color="#888")
        self.stats_label.pack(side="right")

        # Row 2: 應用程式綁定
        row2 = ctk.CTkFrame(top, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(row2, text="綁定視窗", font=ctk.CTkFont(size=11), text_color="#888").pack(side="left")
        self.target_window_entry = ctk.CTkEntry(row2, height=30, fg_color="#12121a", border_color="#333",
                                               placeholder_text="視窗標題關鍵字 (留空 = 全域有效)")
        self.target_window_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        ctk.CTkButton(row2, text="🎯 3秒後獲取", width=90, height=28, fg_color="#2a2a35", hover_color="#3a3a45",
                     command=self._get_active_window_delay).pack(side="left")
    
    def _create_control_section(self):
        ctrl = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        ctrl.pack(fill="x", padx=20, pady=10)
        
        self.play_btn = ctk.CTkButton(ctrl, text="[ 執行 ]", font=ctk.CTkFont(family=CMD_FONT_FAMILY, size=14, weight="bold"),
                                      fg_color=CMD_BG, border_width=1, border_color=CMD_ACCENT, text_color=CMD_ACCENT,
                                      hover_color=CMD_HOVER, height=40, width=120,
                                      command=self._play_macro)
        self.play_btn.pack(side="left", padx=(0, 8))
        
        self.stop_btn = ctk.CTkButton(ctrl, text="[ 停止 ]", font=ctk.CTkFont(family=CMD_FONT_FAMILY, size=14, weight="bold"),
                                      fg_color=CMD_BG, border_width=1, border_color="#ef4444", text_color="#ef4444",
                                      hover_color="#330000", height=40, width=100, command=self._stop_macro,
                                      state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 8))
        
        ctk.CTkButton(ctrl, text="[ 儲存 ]", font=ctk.CTkFont(family=CMD_FONT_FAMILY, size=12), fg_color=CMD_BG, border_width=1, border_color="#6366f1", text_color="#6366f1", height=40, width=80, hover_color="#000033",
                     command=self._save_macro).pack(side="left", padx=(0, 8))
        ctk.CTkButton(ctrl, text="[ 刪除 ]", font=ctk.CTkFont(family=CMD_FONT_FAMILY, size=12), fg_color=CMD_BG, border_width=1, border_color="#ef4444", text_color="#ef4444", hover_color="#330000", height=40, width=80,
                     command=self._delete_macro).pack(side="right")
    
    def _create_events_section(self):
        events = ctk.CTkFrame(self.detail_frame, fg_color=CMD_FG, corner_radius=0, 
                             border_width=1, border_color=CMD_BORDER)
        events.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        header = ctk.CTkFrame(events, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(header, text="> 事件紀錄", font=ctk.CTkFont(family=CMD_FONT_FAMILY, size=14, weight="bold"),
                    text_color=CMD_TEXT).pack(side="left")
        
        # 編輯按鈕
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        ctk.CTkButton(btn_frame, text="🔴 追加錄製", width=90, height=28, fg_color="#ef4444",
                     hover_color="#dc2626", command=self._append_recording).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="[ 插入 ]", width=60, height=28, fg_color=CMD_BG, border_width=1, border_color=CMD_BORDER, text_color=CMD_TEXT, font=ctk.CTkFont(family=CMD_FONT_FAMILY, size=11), hover_color=CMD_HOVER,
                     command=self._insert_event).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="[ 編輯 ]", width=60, height=28, fg_color=CMD_BG, border_width=1, border_color=CMD_BORDER, text_color=CMD_TEXT, font=ctk.CTkFont(family=CMD_FONT_FAMILY, size=11), hover_color=CMD_HOVER,
                     command=self._edit_event).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="🗑️ 刪除", width=70, height=28, fg_color="#1f1f2e",
                     hover_color="#dc2626", command=self._delete_event).pack(side="left", padx=3)
        
        # 選項
        opts = ctk.CTkFrame(events, fg_color="transparent")
        opts.pack(fill="x", padx=15)
        self.record_keyboard_var = ctk.BooleanVar(value=True)
        self.record_mouse_var = ctk.BooleanVar(value=True)
        self.record_scroll_var = ctk.BooleanVar(value=True)
        for txt, var in [("鍵盤", self.record_keyboard_var), ("滑鼠點擊", self.record_mouse_var),
                         ("滑鼠滾輪", self.record_scroll_var)]:
            ctk.CTkCheckBox(opts, text=txt, variable=var, font=ctk.CTkFont(size=11),
                           fg_color="#6366f1").pack(side="left", padx=5)
        
        self.events_list = ctk.CTkScrollableFrame(events, fg_color="transparent")
        self.events_list.pack(fill="both", expand=True, padx=10, pady=(10, 10))
        
        self.selected_event_idx = None
    
    def _refresh_macro_list(self):
        for w in self.macro_list_frame.winfo_children():
            w.destroy()
        
        macros = self.manager.get_all_macros()
        if not macros:
            ctk.CTkLabel(self.macro_list_frame, text="尚無巨集\n點擊「+ 新增」開始", font=ctk.CTkFont(size=12),
                        text_color="#666").pack(pady=50)
            return
        
        for macro in sorted(macros, key=lambda m: m.created_time, reverse=True):
            self._create_macro_item(macro)
    
    def _create_macro_item(self, macro: Macro):
        item = ctk.CTkFrame(self.macro_list_frame, fg_color="#1a1a25", corner_radius=8, height=60)
        item.pack(fill="x", pady=3)
        item.pack_propagate(False)
        item.bind("<Button-1>", lambda e, m=macro: self._select_macro(m))
        
        content = ctk.CTkFrame(item, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=8)
        content.bind("<Button-1>", lambda e, m=macro: self._select_macro(m))
        
        name_text = f"🎯 {macro.name}"
        if macro.trigger_key:
            name_text += f"  [{macro.trigger_key.upper()}]"
        name = ctk.CTkLabel(content, text=name_text, font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        name.pack(anchor="w")
        name.bind("<Button-1>", lambda e, m=macro: self._select_macro(m))
        
        stats = f"📊 {macro.event_count} 事件 | ⏱️ {macro.total_duration:.1f}s"
        if macro.loop_count != 1:
            stats += f" | 🔄 {macro.loop_count if macro.loop_count > 0 else '∞'}"
        stats_lbl = ctk.CTkLabel(content, text=stats, font=ctk.CTkFont(size=10), text_color="#888", anchor="w")
        stats_lbl.pack(anchor="w")
        stats_lbl.bind("<Button-1>", lambda e, m=macro: self._select_macro(m))
    
    def _select_macro(self, macro: Macro):
        self.selected_macro = macro
        self.selected_event_idx = None
        self.selected_indices = set()
        self.no_selection_frame.pack_forget()
        self.detail_frame.pack(fill="both", expand=True)
        
        self.macro_name_entry.delete(0, "end")
        self.macro_name_entry.insert(0, macro.name)
        self.hotkey_entry.delete(0, "end")
        if macro.trigger_key:
            self.hotkey_entry.insert(0, macro.trigger_key)
        self.loop_count_entry.delete(0, "end")
        self.loop_count_entry.insert(0, str(macro.loop_count))
        self.loop_delay_entry.delete(0, "end")
        self.loop_delay_entry.insert(0, str(macro.loop_delay))
        self.target_window_entry.delete(0, "end")
        if hasattr(macro, 'target_window'):
            self.target_window_entry.insert(0, macro.target_window)
            
        self.stats_label.configure(text=f"📊 {macro.event_count} 個事件 | ⏱️ {macro.total_duration:.2f} 秒")
        
        # 更新事件列表（這行之前被意外刪除了）
        self._update_events_list(macro.events)
    
    def _get_active_window_delay(self):
        """3秒後獲取當前視窗"""
        self.target_window_entry.delete(0, "end")
        self.target_window_entry.insert(0, "等待 3 秒...")
        self.update()
        
        def run():
            time.sleep(3)
            title = window_utils.get_active_window_title()
            self.after(0, self._update_window_entry, title)
            
        threading.Thread(target=run, daemon=True).start()
        
    def _update_window_entry(self, title):
        self.target_window_entry.delete(0, "end")
        self.target_window_entry.insert(0, title)
        messagebox.showinfo("已獲取", f"已設定目標視窗為：\n{title}")
        
        # Bug fix: Removed undefined macro reference
    
    def _update_events_list(self, events: list, preserve_scroll: bool = False, scroll_to_index: int = None):
        # 保存目前滾動位置
        scroll_pos = 0.0
        try:
            if preserve_scroll:
                scroll_pos = self.events_list._parent_canvas.yview()[0]
        except:
            pass
        
        # 清除舊內容
        for w in self.events_list.winfo_children():
            w.destroy()
        
        self.event_items = []
        
        # 提示標籤
        if events:
            ctk.CTkLabel(self.events_list, text="💡 拖動事件可重新排序", font=ctk.CTkFont(size=10),
                        text_color="#666").pack(anchor="w", pady=(0, 5))
        
        # 限制顯示數量以提升性能
        display_count = min(len(events), 200)
        
        for i in range(display_count):
            item = self._create_event_item(events[i], i)
            self.event_items.append(item)
        
        if len(events) > display_count:
            ctk.CTkLabel(self.events_list, text=f"... 還有 {len(events) - display_count} 個事件",
                        font=ctk.CTkFont(size=11), text_color="#666").pack(pady=10)
        
        # 刷新佈局
        self.events_list.update_idletasks()
        
        # 恢復滾動位置或滾動到指定索引
        try:
            if scroll_to_index is not None and len(self.event_items) > 0:
                # 滾動到指定索引的位置
                ratio = scroll_to_index / max(len(events), 1)
                self.events_list._parent_canvas.yview_moveto(ratio)
            elif preserve_scroll:
                self.events_list._parent_canvas.yview_moveto(scroll_pos)
            else:
                self.events_list._parent_canvas.yview_moveto(0.0)
        except:
            pass

    def _create_event_item(self, event: MacroEvent, index: int):
        icons = {EventType.KEY_PRESS: "⌨️↓", EventType.KEY_RELEASE: "⌨️↑", EventType.MOUSE_CLICK: "🖱️↓",
                EventType.MOUSE_RELEASE: "🖱️↑", EventType.MOUSE_MOVE: "🖱️→", EventType.MOUSE_SCROLL: "🖱️⟳",
                EventType.DELAY: "⏱️"}
        icon = icons.get(event.event_type, "❓")
        
        if event.event_type == EventType.DELAY:
            desc = f"等待 {event.delay*1000:.0f} ms"
        elif event.event_type in [EventType.KEY_PRESS, EventType.KEY_RELEASE]:
            desc = event.key
        elif event.event_type in [EventType.MOUSE_CLICK, EventType.MOUSE_RELEASE]:
            desc = f"{event.button} ({event.x},{event.y})"
        else:
            desc = str(event.event_type.value) if event.event_type else "未知"
        
        item = ctk.CTkFrame(self.events_list, fg_color=CMD_BG, corner_radius=0, height=32, border_width=1, border_color="#333333")
        item.pack(fill="x", pady=1)
        item.pack_propagate(False)
        item.event_index = index  # 儲存索引
        
        # 點擊選中
        item.bind("<Button-1>", lambda e, i=index: self._select_event(i, item, e))
        
        # 雙擊快速編輯延遲
        item.bind("<Double-Button-1>", lambda e, i=index: self._quick_edit_delay(i))
        
        # 拖放事件
        item.bind("<ButtonPress-1>", lambda e, i=index: self._drag_start(e, i, item))
        item.bind("<B1-Motion>", self._drag_motion)
        item.bind("<ButtonRelease-1>", self._drag_end)
        
        label = ctk.CTkLabel(item, text=f"[{index+1:03d}] {icon} {desc}", font=ctk.CTkFont(size=11, family=CMD_FONT_FAMILY), text_color=CMD_TEXT,
                    anchor="w")
        label.pack(side="left", padx=10)
        label.bind("<ButtonPress-1>", lambda e, i=index: self._drag_start(e, i, item))
        label.bind("<B1-Motion>", self._drag_motion)
        label.bind("<ButtonRelease-1>", self._drag_end)
        label.bind("<Double-Button-1>", lambda e, i=index: self._quick_edit_delay(i))
        
        # 延遲事件顯示可編輯提示
        if event.event_type == EventType.DELAY:
            delay_label = ctk.CTkLabel(item, text="(雙擊編輯)", font=ctk.CTkFont(size=9),
                        text_color="#6366f1")
        else:
            delay_label = ctk.CTkLabel(item, text="", font=ctk.CTkFont(size=10),
                        text_color="#666")
        delay_label.pack(side="right", padx=10)
        delay_label.bind("<ButtonPress-1>", lambda e, i=index: self._drag_start(e, i, item))
        delay_label.bind("<B1-Motion>", self._drag_motion)
        delay_label.bind("<ButtonRelease-1>", self._drag_end)
        delay_label.bind("<Double-Button-1>", lambda e, i=index: self._quick_edit_delay(i))
        
        return item
    
    def _quick_edit_delay(self, index: int):
        """快速編輯延遲事件"""
        if not self.selected_macro or index >= len(self.selected_macro.events):
            return
        
        event = self.selected_macro.events[index]
        
        # 只有延遲事件可以快速編輯
        if event.event_type != EventType.DELAY:
            return
        
        # 彈出簡單輸入對話框
        current_ms = int(event.delay * 1000)
        
        dialog = ctk.CTkInputDialog(
            text=f"請輸入新的延遲時間 (毫秒):",
            title="編輯延遲"
        )
        result = dialog.get_input()
        
        if result:
            try:
                new_ms = int(result)
                if new_ms >= 0:
                    event.delay = new_ms / 1000
                    self._update_events_list(self.selected_macro.events, scroll_to_index=index)
                    self.stats_label.configure(text=f"📊 {self.selected_macro.event_count} 事件")
            except ValueError:
                messagebox.showerror("錯誤", "請輸入有效的數字")
    
    def _drag_start(self, event, index, item):
        """開始拖動"""
        self.drag_start_idx = index
        self.drag_item = item
        self._select_event(index, item)
        item.configure(fg_color="#4f46e5")
    
    def _drag_motion(self, event):
        """拖動中"""
        if self.drag_item is None or not self.event_items:
            return
        
        # 計算滑鼠相對位置，決定目標位置
        try:
            y = event.widget.winfo_rooty() + event.y
            
            for i, item in enumerate(self.event_items):
                if item == self.drag_item:
                    continue
                item_y = item.winfo_rooty()
                item_h = item.winfo_height()
                
                # 判斷滑鼠是否在這個項目的範圍內
                if item_y < y < item_y + item_h:
                    # 高亮顯示目標位置
                    item.configure(fg_color="#2a3a5e")
                else:
                    if hasattr(item, 'event_index') and item.event_index == self.selected_event_idx:
                        item.configure(fg_color="#2a2a4e")
                    else:
                        item.configure(fg_color="#12121a")
        except:
            pass
    
    def _drag_end(self, event):
        """結束拖動"""
        if self.drag_item is None or self.drag_start_idx is None or not self.selected_macro:
            self.drag_item = None
            self.drag_start_idx = None
            return
        
        try:
            y = event.widget.winfo_rooty() + event.y
            target_idx = self.drag_start_idx
            
            for i, item in enumerate(self.event_items):
                item_y = item.winfo_rooty()
                item_h = item.winfo_height()
                
                if item_y < y < item_y + item_h:
                    target_idx = i
                    break
            
            # 如果位置改變，重新排序
            if target_idx != self.drag_start_idx:
                events = self.selected_macro.events
                moved_event = events.pop(self.drag_start_idx)
                events.insert(target_idx, moved_event)
                self.selected_event_idx = target_idx
                self._update_events_list(events, scroll_to_index=target_idx)
        except:
            pass
        
        self.drag_item = None
        self.drag_start_idx = None
    
    def _select_event(self, index: int, item, event=None):
        # 處理多選邏輯
        if event:
            # Windows/Linux: Shift=0x1, Ctrl=0x4
            ctrl_pressed = (event.state & 0x4) != 0
            shift_pressed = (event.state & 0x1) != 0
            
            if shift_pressed and self.selected_event_idx is not None:
                # Shift 連選：選擇從 Anchor 到當前的範圍
                start = min(self.selected_event_idx, index)
                end = max(self.selected_event_idx, index)
                
                if not ctrl_pressed:
                    self.selected_indices.clear()
                
                for i in range(start, end + 1):
                    self.selected_indices.add(i)
                    
            elif ctrl_pressed:
                # Ctrl 加選/減選
                if index in self.selected_indices:
                    self.selected_indices.discard(index)
                    # 如果取消選中的是 Anchor，嘗試移動 Anchor
                    if index == self.selected_event_idx and self.selected_indices:
                        self.selected_event_idx = list(self.selected_indices)[-1]
                else:
                    self.selected_indices.add(index)
                    self.selected_event_idx = index
            else:
                # 單選
                self.selected_indices.clear()
                self.selected_indices.add(index)
                self.selected_event_idx = index
        else:
            # 程式化選擇
            self.selected_indices = {index}
            self.selected_event_idx = index

        self._update_selection_visuals()
        # 確保視窗獲得焦點以接收鍵盤事件
        self.focus_set()
        
    def _update_selection_visuals(self):
        """更新所有事件項目的選中狀態顏色"""
        for i, item in enumerate(self.event_items):
            if i in self.selected_indices:
                item.configure(fg_color="#2a2a4e") # 選中顏色
            else:
                item.configure(fg_color="#12121a") # 預設顏色
    
    def _move_event_up(self, event=None):
        """按上鍵將選中事件向上移動"""
        if not self.selected_macro or self.selected_event_idx is None:
            return
        if self.selected_event_idx <= 0:
            return  # 已經在最上面
        
        events = self.selected_macro.events
        idx = self.selected_event_idx
        # 交換位置
        events[idx], events[idx - 1] = events[idx - 1], events[idx]
        self.selected_event_idx = idx - 1
        self._update_events_list(events, scroll_to_index=idx - 1)
        # 重新選中
        if self.event_items and self.selected_event_idx < len(self.event_items):
            self.event_items[self.selected_event_idx].configure(fg_color="#2a2a4e")
    
    def _move_event_down(self, event=None):
        """按下鍵將選中事件向下移動"""
        if not self.selected_macro or self.selected_event_idx is None:
            return
        if self.selected_event_idx >= len(self.selected_macro.events) - 1:
            return  # 已經在最下面
        
        events = self.selected_macro.events
        idx = self.selected_event_idx
        # 交換位置
        events[idx], events[idx + 1] = events[idx + 1], events[idx]
        self.selected_event_idx = idx + 1
        self._update_events_list(events, scroll_to_index=idx + 1)
        # 重新選中
        if self.event_items and self.selected_event_idx < len(self.event_items):
            self.event_items[self.selected_event_idx].configure(fg_color="#2a2a4e")
    
    def _delete_event_key(self, event=None):
        """按 Delete 鍵刪除選中事件"""
        if not self.selected_macro or not self.selected_indices:
            return
            
        events = self.selected_macro.events
        # 從後往前刪除，避免索引偏移
        for idx in sorted(list(self.selected_indices), reverse=True):
            if idx < len(events):
                del events[idx]
        
        self.selected_indices.clear()
        self.selected_event_idx = None
        self._update_events_list(events, preserve_scroll=True)
        self.stats_label.configure(text=f"📊 {self.selected_macro.event_count} 個事件 | ⏱️ {self.selected_macro.total_duration:.2f} 秒")
    
    def _insert_event(self):
        if not self.selected_macro:
            return
        dialog = EventEditorDialog(self, insert_mode=True)
        self.wait_window(dialog)
        if dialog.result:
            idx = (self.selected_event_idx + 1) if self.selected_event_idx is not None else len(self.selected_macro.events)
            self.selected_macro.events.insert(idx, dialog.result)
            self._update_events_list(self.selected_macro.events, scroll_to_index=idx)
            self.stats_label.configure(text=f"📊 {self.selected_macro.event_count} 個事件 | ⏱️ {self.selected_macro.total_duration:.2f} 秒")
    
    def _edit_event(self):
        if not self.selected_macro or len(self.selected_indices) != 1:
            messagebox.showinfo("提示", "請選擇單個事件進行編輯")
            return
        
        # 使用集合中的唯一索引
        idx = list(self.selected_indices)[0]
        event = self.selected_macro.events[idx]
        dialog = EventEditorDialog(self, event=event)
        self.wait_window(dialog)
        if dialog.result:
            self.selected_macro.events[self.selected_event_idx] = dialog.result
            self._update_events_list(self.selected_macro.events, scroll_to_index=idx)
    
    def _delete_event(self):
        if not self.selected_macro:
             return
             
        if not self.selected_indices:
             if self.selected_event_idx is not None:
                 self.selected_indices = {self.selected_event_idx}
             else:
                 messagebox.showinfo("提示", "請先選擇要刪除的事件")
                 return

        if messagebox.askyesno("確認", f"確定刪除選中的 {len(self.selected_indices)} 個事件？"):
            events = self.selected_macro.events
            for idx in sorted(list(self.selected_indices), reverse=True):
                if idx < len(events):
                    del events[idx]
            
            self.selected_indices.clear()
            self.selected_event_idx = None
            self._update_events_list(events, preserve_scroll=True)
            self.stats_label.configure(text=f"📊 {self.selected_macro.event_count} 個事件 | ⏱️ {self.selected_macro.total_duration:.2f} 秒")

    def _copy_events(self, event=None):
        """Ctrl+C: 複製選中事件"""
        if not self.selected_macro or not self.selected_indices:
            return
        
        # 排序索引以保證順序
        indices = sorted(list(self.selected_indices))
        events = self.selected_macro.events
        
        self.clipboard_events = []
        import copy
        for idx in indices:
            if idx < len(events):
                self.clipboard_events.append(copy.deepcopy(events[idx]))
        
        self.status_indicator.configure(text=f"📋 已複製 {len(self.clipboard_events)} 個事件", text_color="#6366f1")
        self.after(2000, lambda: self.status_indicator.configure(text="● 待命中", text_color="#22c55e"))

    def _cut_events(self, event=None):
        """Ctrl+X: 剪下選中事件"""
        if not self.selected_macro or not self.selected_indices:
            return
            
        self._copy_events()
        # 靜默執行刪除
        events = self.selected_macro.events
        for idx in sorted(list(self.selected_indices), reverse=True):
            if idx < len(events):
                del events[idx]
        
        self.selected_indices.clear()
        self.selected_event_idx = None
        self._update_events_list(events, preserve_scroll=True)
        self.stats_label.configure(text=f"📊 {self.selected_macro.event_count} 個事件 | ⏱️ {self.selected_macro.total_duration:.2f} 秒")

    def _paste_events(self, event=None):
        """Ctrl+V: 貼上事件"""
        if not self.selected_macro or not self.clipboard_events:
            return
            
        events = self.selected_macro.events
        
        # 決定插入位置：如果在最後選擇的事件後面，或者列表末尾
        if self.selected_event_idx is not None:
             insert_pos = self.selected_event_idx + 1
        else:
             insert_pos = len(events)
             
        import copy
        new_events = [copy.deepcopy(e) for e in self.clipboard_events]
        
        for i, new_event in enumerate(new_events):
            events.insert(insert_pos + i, new_event)
            
        self._update_events_list(events, scroll_to_index=insert_pos)
        self.stats_label.configure(text=f"📊 {self.selected_macro.event_count} 個事件 | ⏱️ {self.selected_macro.total_duration:.2f} 秒")
        
        # 選中新貼上的事件
        self.selected_indices.clear()
        for i in range(len(new_events)):
            self.selected_indices.add(insert_pos + i)
        self.selected_event_idx = insert_pos + len(new_events) - 1 if new_events else insert_pos
        self._update_selection_visuals()
        
        self.status_indicator.configure(text=f"📋 已貼上 {len(new_events)} 個事件", text_color="#6366f1")
        self.after(2000, lambda: self.status_indicator.configure(text="● 待命中", text_color="#22c55e"))
    
    def _append_recording(self):
        """追加錄製：在現有巨集末尾繼續錄製"""
        if not self.selected_macro:
            messagebox.showwarning("提示", "請先選擇要編輯的巨集")
            return
        
        # 記住當前巨集用於追加
        self._append_target_macro = self.selected_macro
        self._append_insert_idx = self.selected_event_idx  # 如果有選中事件，在其後插入；否則在末尾
        
        self.status_indicator.configure(text="🔴 追加錄製中...", text_color="#ef4444")
        self.recorder.record_keyboard = self.record_keyboard_var.get()
        self.recorder.record_mouse_clicks = self.record_mouse_var.get()
        self.recorder.record_mouse_scroll = self.record_scroll_var.get()
        
        self.recording_overlay = RecordingOverlay(self)
        self.recording_overlay.title("追加錄製中")
        
        # 設定追加模式的回調
        self.recorder.on_event_recorded = lambda e: self.after(0, lambda: self.recording_overlay.add_event(e) if self.recording_overlay else None)
        self.recorder.on_recording_stopped = self._on_append_recording_stopped
        
        messagebox.showinfo("追加錄製", f"將在巨集「{self.selected_macro.name}」後追加錄製\n按 F10 停止錄製")
        self.recorder.start_recording()
    
    def _on_append_recording_stopped(self):
        """追加錄製停止的回調"""
        def update():
            if self.recording_overlay:
                self.recording_overlay.destroy()
                self.recording_overlay = None
            self.status_indicator.configure(text="● 待命中", text_color="#22c55e")
            
            if self.recorder.events and hasattr(self, '_append_target_macro') and self._append_target_macro:
                macro = self._append_target_macro
                new_events = self.recorder.events.copy()
                
                # 決定插入位置
                if hasattr(self, '_append_insert_idx') and self._append_insert_idx is not None:
                    insert_idx = self._append_insert_idx + 1
                else:
                    insert_idx = len(macro.events)
                
                # 插入新事件
                for i, event in enumerate(new_events):
                    macro.events.insert(insert_idx + i, event)
                
                # 更新顯示
                # Bug fix: Removed undefined macro reference
                self.stats_label.configure(text=f"📊 {macro.event_count} 個事件 | ⏱️ {macro.total_duration:.2f} 秒")
                
                messagebox.showinfo("完成", f"已追加 {len(new_events)} 個事件\n記得點擊「儲存」保存變更")
            
            # 恢復正常錄製回調
            self.recorder.on_recording_stopped = self._on_recording_stopped
            self._append_target_macro = None
            self._append_insert_idx = None
        
        self.after(100, update)
    
    def _start_recording(self):
        self.status_indicator.configure(text="🔴 錄製中...", text_color="#ef4444")
        self.recorder.record_keyboard = self.record_keyboard_var.get()
        self.recorder.record_mouse_clicks = self.record_mouse_var.get()
        self.recorder.record_mouse_scroll = self.record_scroll_var.get()
        
        self.recording_overlay = RecordingOverlay(self)
        self.recorder.on_event_recorded = lambda e: self.after(0, lambda: self.recording_overlay.add_event(e) if self.recording_overlay else None)
        
        messagebox.showinfo("開始錄製", "點擊確定後開始錄製\n按 F10 停止")
        self.recorder.start_recording()
    
    def _on_event_recorded(self, event: MacroEvent):
        pass
    
    def _on_recording_stopped(self):
        def update():
            if self.recording_overlay:
                self.recording_overlay.destroy()
                self.recording_overlay = None
            self.status_indicator.configure(text="● 待命中", text_color="#22c55e")
            
            if self.recorder.events:
                name = ctk.CTkInputDialog(text="請輸入巨集名稱：", title="儲存巨集").get_input()
                if name:
                    macro = self.recorder.create_macro(name)
                    self.manager.save_macro(macro)
                    self._refresh_macro_list()
                    self._select_macro(macro)
                    messagebox.showinfo("完成", f"已儲存「{name}」({len(macro.events)} 事件)")
        self.after(100, update)
    
    def _play_macro(self):
        if not self.selected_macro:
            return
        
        try:
            # 更新設定
            self.selected_macro.loop_count = int(self.loop_count_entry.get())
            self.selected_macro.loop_delay = float(self.loop_delay_entry.get())
            self.player.speed_multiplier = float(self.speed_entry.get())
            
            self.play_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.status_indicator.configure(text="▶️ 播放中...", text_color="#6366f1")
            
            # 使用線程啟動，避免卡住 GUI
            threading.Thread(target=lambda: self.player.play(self.selected_macro), daemon=True).start()
            
        except ValueError:
            messagebox.showerror("錯誤", "設定值必須為數字")
    
    def _stop_macro(self):
        self.player.stop()
    
    def _on_play_started(self, macro):
        pass
    
    def _on_play_stopped(self):
        self.after(100, lambda: (self.play_btn.configure(state="normal"), self.stop_btn.configure(state="disabled"),
                                 self.status_indicator.configure(text="● 待命中", text_color="#22c55e")))
    
    def _save_macro(self):
        if not self.selected_macro:
            return
        try:
            new_name = self.macro_name_entry.get().strip()
            if not new_name:
                messagebox.showerror("錯誤", "請輸入名稱")
                return
            
            old_name = self.selected_macro.name
            old_key = self.selected_macro.trigger_key
            
            self.selected_macro.name = new_name
            self.selected_macro.trigger_key = self.hotkey_entry.get().strip() or None
            self.selected_macro.loop_count = int(self.loop_count_entry.get())
            self.selected_macro.loop_delay = float(self.loop_delay_entry.get())
            self.selected_macro.target_window = self.target_window_entry.get().strip()
            
            if old_name != new_name:
                self.manager.delete_macro(old_name)
            
            # 更新熱鍵
            if old_key:
                self.hotkey_manager.unregister_hotkey(old_key)
            if self.selected_macro.trigger_key:
                self.hotkey_manager.register_hotkey(self.selected_macro.trigger_key,
                                                   lambda m=self.selected_macro: self._trigger_macro(m))
            
            self.manager.save_macro(self.selected_macro)
            self._refresh_macro_list()
            messagebox.showinfo("完成", "已儲存")
        except ValueError:
            messagebox.showerror("錯誤", "請輸入有效數值")
    
    def _delete_macro(self):
        if not self.selected_macro:
            return
        if messagebox.askyesno("確認", f"刪除「{self.selected_macro.name}」？"):
            if self.selected_macro.trigger_key:
                self.hotkey_manager.unregister_hotkey(self.selected_macro.trigger_key)
            self.manager.delete_macro(self.selected_macro.name)
            self.selected_macro = None
            self.detail_frame.pack_forget()
            self.no_selection_frame.pack(fill="both", expand=True)
            self._refresh_macro_list()
    
    def _import_macro(self):
        path = filedialog.askopenfilename(title="選擇檔案", filetypes=[("JSON", "*.json")])
        if path:
            macro = self.manager.import_macro(path)
            if macro:
                self._refresh_macro_list()
                self._select_macro(macro)
                messagebox.showinfo("完成", f"已匯入「{macro.name}」")
    
    def _export_macro(self):
        if not self.selected_macro:
            messagebox.showwarning("提示", "請先選擇巨集")
            return
        path = filedialog.asksaveasfilename(title="儲存", defaultextension=".json",
                                           initialfile=f"{self.selected_macro.name}.json")
        if path:
            self.manager.export_macro(self.selected_macro.name, path)
            messagebox.showinfo("完成", f"已匯出至 {path}")
    
    def _minimize_to_tray(self):
        """最小化到系統托盤"""
        self.withdraw()
        
        # 建立托盤圖示
        img = Image.new('RGB', (64, 64), color='#6366f1')
        draw = ImageDraw.Draw(img)
        draw.rectangle([16, 16, 48, 48], fill='#22c55e')
        
        menu = pystray.Menu(
            pystray.MenuItem("顯示視窗", self._show_from_tray),
            pystray.MenuItem("退出", self._quit_from_tray)
        )
        
        self.tray_icon = pystray.Icon("MacroHub", img, "MacroHub - 運行中", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def _show_from_tray(self):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.after(0, self.deiconify)
    
    def _quit_from_tray(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self._cleanup_and_quit)
    
    def _cleanup_and_quit(self):
        self.hotkey_manager.stop()
        self.destroy()
    
    def _on_close(self):
        if messagebox.askyesno("確認", "要最小化到托盤還是退出？\n\n是 = 最小化到托盤\n否 = 完全退出"):
            self._minimize_to_tray()
        else:
            self._cleanup_and_quit()


def main():
    app = MacroHubApp()
    app.mainloop()


if __name__ == "__main__":
    main()
