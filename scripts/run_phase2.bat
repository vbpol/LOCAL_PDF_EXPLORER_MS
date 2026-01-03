@echo off
set VENV_PATH=%~dp0..\.env

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Virtual environment not found at %VENV_PATH%
    exit /b 1
)

call "%VENV_PATH%\Scripts\activate.bat"
python "%~dp0..\src\run_phase2.py"
pause
