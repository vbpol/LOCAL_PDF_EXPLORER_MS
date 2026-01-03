@echo off
REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
set "VENV_PATH=%SCRIPT_DIR%.venv"

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Virtual environment not found. Creating...
    python -m venv "%VENV_PATH%"
    call "%VENV_PATH%\Scripts\activate.bat"
    pip install -r "%SCRIPT_DIR%requirements.txt"
) else (
    call "%VENV_PATH%\Scripts\activate.bat"
)

python "%SCRIPT_DIR%src\main.py" %*
