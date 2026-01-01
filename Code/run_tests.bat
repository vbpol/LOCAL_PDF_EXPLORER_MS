@echo off
echo Running Startup Tests...
.\.env\Scripts\python.exe tests/test_startup.py
if %errorlevel% neq 0 (
    echo Startup Test Failed!
    exit /b %errorlevel%
)

echo.
echo Running All Tests...
.\.env\Scripts\python.exe -m unittest discover tests
if %errorlevel% neq 0 (
    echo Tests Failed!
    exit /b %errorlevel%
)

echo.
echo All Tests Passed. App is ready to start.
pause
