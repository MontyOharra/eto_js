@echo off
REM Change to the directory where this script is located
cd /d "%~dp0"
echo Starting Transformation Pipeline Server...
set PYTHONUNBUFFERED=1
call .venv\Scripts\activate
python main.py
