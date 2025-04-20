@echo off
setlocal

:: Get current directory
set "SCRIPT_DIR=%~dp0"

:: Change to script directory
cd /d "%SCRIPT_DIR%"

echo [%time%] : Starting early appointment checker in continuous mode...
echo [%time%] : Press Ctrl+C to stop the script

:: Use Python executable
python check_early_appointments.py

echo [%time%] : Script has stopped.

endlocal 