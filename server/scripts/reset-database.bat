@echo off
echo ETO Database Reset Script
echo ========================

cd /d "%~dp0\.."

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found at venv\
    echo Please run setup-venv.sh first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the database reset script
python scripts\reset-database.py %*

REM Deactivate virtual environment
deactivate

pause