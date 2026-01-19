@echo off
REM Database Reset Script for Windows
REM
REM This script:
REM   1. Clears logs and storage directories
REM   2. Drops and recreates the database with all tables

REM Change to the directory where this script is located
cd /d "%~dp0"

echo ============================================================
echo   Database Reset Script
echo ============================================================
echo.

REM Step 1: Clear logs and storage
echo Cleaning up logs and storage directories...
if exist logs\* del /q logs\* 2>nul
if exist storage\* del /q /s storage\* 2>nul
for /d %%d in (storage\*) do rd /s /q "%%d" 2>nul
echo Cleaned up logs and storage data
echo.

REM Step 2: Reset database using CLI
echo Resetting database...
call .venv\Scripts\activate
python -m src.cli db reset --confirm

echo.
echo ============================================================
echo   Reset Complete
echo ============================================================
pause
