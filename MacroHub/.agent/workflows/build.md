---
description: 如何將 MacroHub 打包成 EXE 執行檔
---

# MacroHub 打包指南

## 前置條件
- 已安裝 Anaconda（或其他有 `customtkinter` 的 Python 環境）
- 已安裝 PyInstaller（腳本會自動安裝）

## 打包步驟

### 方法一：使用終端機（推薦）

1. 開啟 **Anaconda Prompt** 或 **PowerShell**

2. 切換到專案目錄：
   ```powershell
   cd C:\Users\mitof\Documents\dream\MacroHub
   ```

3. 執行打包腳本：
   ```powershell
   # 使用 Anaconda Python（重要！不要用其他 Python）
   C:\ProgramData\anaconda3\python.exe build_exe.py
   ```

4. 等待約 1-2 分鐘，完成後 EXE 會出現在 `dist` 資料夾

### 方法二：直接雙擊（需設定）

1. 右鍵點擊 `build_exe.py`
2. 選擇「開啟方式」→「選擇其他應用程式」
3. 找到 `C:\ProgramData\anaconda3\python.exe`
4. 勾選「一律使用此應用程式」
5. 之後雙擊 `build_exe.py` 即可打包

## 打包後的檔案位置

```
MacroHub/
├── dist/
│   └── MacroHub.exe    ← 這就是您的程式！
├── macros/             ← 複製這個到 dist 資料夾
└── ...
```

## 常見問題

### Q: 出現 `ModuleNotFoundError: No module named 'customtkinter'`
**A:** 您使用了錯誤的 Python。請確保使用 Anaconda 的 Python：
```powershell
C:\ProgramData\anaconda3\python.exe build_exe.py
```

### Q: 打包後巨集不見了？
**A:** 把 `macros` 資料夾複製到 `dist` 資料夾裡（放在 EXE 旁邊）

### Q: 想要更新程式？
**A:** 修改程式碼後，重新執行打包腳本即可。新的 EXE 會覆蓋舊的。

## 快速指令（複製貼上用）

```powershell
cd C:\Users\mitof\Documents\dream\MacroHub && C:\ProgramData\anaconda3\python.exe build_exe.py
```
