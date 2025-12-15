@echo off
cd /d C:\apps\pipeline_server   REM <-- change to your deploy path
set PYTHONUNBUFFERED=1
call .venv\Scripts\activate
python main.py
