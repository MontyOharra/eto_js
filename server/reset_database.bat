@echo off
REM Database Reset Script for Windows
REM
REM This script:
REM   1. Clears logs and storage directories
REM   2. Drops and recreates the database with all tables

REM Change to the directory where this script is located
cd /d "%~dp0"

echo ============================================================
echo   DATABASE RESET SCRIPT - DESTRUCTIVE OPERATION
echo ============================================================
echo.
echo WARNING: This will permanently delete:
echo   - All logs
echo   - All stored files (PDFs, attachments, etc.)
echo   - The entire database (all tables, all data)
echo.
echo ============================================================
echo.

REM First confirmation
set /p confirm1="Are you sure you want to reset the entire server? (yes/no): "
if /i not "%confirm1%"=="yes" (
    echo.
    echo Reset cancelled.
    pause
    exit /b 0
)

echo.
echo ============================================================
echo   FINAL WARNING - THIS CANNOT BE UNDONE
echo ============================================================
echo.
echo Type exactly: yes i do
echo.
set /p confirm2="I REALLY DO WANT TO DESTROY EVERYTHING: "
if not "%confirm2%"=="yes i do" (
    echo.
    echo Reset cancelled. You must type exactly "yes i do" to confirm.
    pause
    exit /b 0
)

echo.
echo Proceeding with reset...
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
