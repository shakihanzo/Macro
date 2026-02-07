"""
MacroHub - 通用巨集管理器
主程式入口點
"""
import os
import sys

# 確保可以找到模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import main

if __name__ == "__main__":
    main()
