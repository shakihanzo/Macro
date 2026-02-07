"""
巨集管理器 - 負責儲存、載入和管理巨集
"""
import os
import json
from typing import Dict, List, Optional
from .recorder import Macro


class MacroManager:
    """巨集管理器"""
    
    def __init__(self, macros_dir: str = "macros"):
        self.macros_dir = macros_dir
        self.macros: Dict[str, Macro] = {}
        
        # 確保目錄存在
        os.makedirs(self.macros_dir, exist_ok=True)
        
        # 載入所有巨集
        self.load_all()
    
    def save_macro(self, macro: Macro) -> bool:
        """儲存巨集到檔案"""
        try:
            # 清理檔名
            safe_name = self._sanitize_filename(macro.name)
            filepath = os.path.join(self.macros_dir, f"{safe_name}.json")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(macro.to_dict(), f, ensure_ascii=False, indent=2)
            
            self.macros[macro.name] = macro
            return True
        
        except Exception as e:
            print(f"儲存巨集失敗: {e}")
            return False
    
    def load_macro(self, name: str) -> Optional[Macro]:
        """載入指定巨集"""
        safe_name = self._sanitize_filename(name)
        filepath = os.path.join(self.macros_dir, f"{safe_name}.json")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            macro = Macro.from_dict(data)
            self.macros[macro.name] = macro
            return macro
        
        except FileNotFoundError:
            print(f"找不到巨集檔案: {filepath}")
            return None
        except Exception as e:
            print(f"載入巨集失敗: {e}")
            return None
    
    def load_all(self) -> List[Macro]:
        """載入所有巨集"""
        self.macros.clear()
        
        if not os.path.exists(self.macros_dir):
            return []
        
        for filename in os.listdir(self.macros_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.macros_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    macro = Macro.from_dict(data)
                    self.macros[macro.name] = macro
                except Exception as e:
                    print(f"載入 {filename} 失敗: {e}")
        
        return list(self.macros.values())
    
    def delete_macro(self, name: str) -> bool:
        """刪除巨集"""
        try:
            safe_name = self._sanitize_filename(name)
            filepath = os.path.join(self.macros_dir, f"{safe_name}.json")
            
            if os.path.exists(filepath):
                os.remove(filepath)
            
            if name in self.macros:
                del self.macros[name]
            
            return True
        
        except Exception as e:
            print(f"刪除巨集失敗: {e}")
            return False
    
    def rename_macro(self, old_name: str, new_name: str) -> bool:
        """重新命名巨集"""
        if old_name not in self.macros:
            return False
        
        if new_name in self.macros:
            return False  # 新名稱已存在
        
        macro = self.macros[old_name]
        macro.name = new_name
        
        # 刪除舊檔案
        self.delete_macro(old_name)
        
        # 儲存新檔案
        return self.save_macro(macro)
    
    def get_macro(self, name: str) -> Optional[Macro]:
        """獲取巨集"""
        return self.macros.get(name)
    
    def get_all_macros(self) -> List[Macro]:
        """獲取所有巨集"""
        return list(self.macros.values())
    
    def _sanitize_filename(self, name: str) -> str:
        """清理檔名，移除不合法字元"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name
    
    def export_macro(self, name: str, filepath: str) -> bool:
        """匯出巨集到指定位置"""
        if name not in self.macros:
            return False
        
        try:
            macro = self.macros[name]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(macro.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"匯出巨集失敗: {e}")
            return False
    
    def import_macro(self, filepath: str) -> Optional[Macro]:
        """從檔案匯入巨集"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            macro = Macro.from_dict(data)
            
            # 如果名稱重複，添加後綴
            original_name = macro.name
            counter = 1
            while macro.name in self.macros:
                macro.name = f"{original_name} ({counter})"
                counter += 1
            
            self.save_macro(macro)
            return macro
        
        except Exception as e:
            print(f"匯入巨集失敗: {e}")
            return None
