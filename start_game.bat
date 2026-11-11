@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist ".\venv_py310\Scripts\python.exe" (
    ".\venv_py310\Scripts\python.exe" main.py
) else if exist ".\.venv\Scripts\python.exe" (
    ".\.venv\Scripts\python.exe" main.py
) else (
    python main.py
)
if errorlevel 1 (
    echo.
    echo [启动失败] 请先安装 Python 3.10+ 并执行: pip install -r requirements.txt
)
pause
