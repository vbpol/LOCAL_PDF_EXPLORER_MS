@echo off
set VENV_PATH=d:\Py_2025\12-2025\GML_free\FILE_ORGANIZER\.env

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Virtual environment not found. Creating...
    python -m venv "%VENV_PATH%"
    call "%VENV_PATH%\Scripts\activate.bat"
    pip install -r requirements.txt
) else (
    call "%VENV_PATH%\Scripts\activate.bat"
)

python run_cli.py %*
