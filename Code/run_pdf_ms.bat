@echo off
cd /d "%~dp0"
:: Navigate to project root (one level up)
cd ..
set ROOT_DIR=%CD%
set VENV_PATH=%ROOT_DIR%\.env

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Virtual environment not found at %VENV_PATH%.
    echo Please ensure the environment is set up correctly.
    pause
    exit /b 1
)

call "%VENV_PATH%\Scripts\activate.bat"

:: Set PYTHONPATH to project root so 'src' module can be found
set PYTHONPATH=%ROOT_DIR%

:: Run the app
start "PDF Management System" pythonw Code/run_pdf_ms.py %*
