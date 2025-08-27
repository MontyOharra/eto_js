@echo off
REM Clear Data Script for ETO System (Windows Batch)
REM This script clears data folders (logs, storage) without affecting database or code

echo 🗑️  ETO Data Cleanup (Windows)
echo ==============================
echo This will DELETE the following folders and their contents:
echo    - logs\ (all log files)
echo    - storage\ (all stored PDF files)
echo.
echo ⚠️  WARNING: PDF files in storage will be permanently lost!
echo    (They can be re-downloaded from emails if needed)
echo.

set /p confirm="Are you sure you want to continue? (type 'yes' to confirm): "
if /i not "%confirm%"=="yes" (
    echo ❌ Data cleanup cancelled
    exit /b 0
)

echo.
echo Starting data folder cleanup...

REM Change to server directory
cd /d "%~dp0.."

REM Clear logs folder
if exist "logs" (
    echo 🗑️  Removing logs folder...
    rmdir /s /q "logs"
    if %errorlevel% == 0 (
        echo ✅ Cleared folder: logs\
    ) else (
        echo ❌ Error clearing logs folder
    )
) else (
    echo 📂 Folder logs\ doesn't exist, skipping
)

REM Recreate logs folder
mkdir "logs" 2>nul
echo 📁 Recreated empty folder: logs\

REM Clear storage folder
if exist "storage" (
    echo 🗑️  Removing storage folder...
    rmdir /s /q "storage"
    if %errorlevel% == 0 (
        echo ✅ Cleared folder: storage\
    ) else (
        echo ❌ Error clearing storage folder
    )
) else (
    echo 📂 Folder storage\ doesn't exist, skipping
)

REM Recreate storage folder
mkdir "storage" 2>nul
echo 📁 Recreated empty folder: storage\

echo.
echo ✅ Data cleanup completed successfully!
echo    - logs\ folder cleared and recreated
echo    - storage\ folder cleared and recreated  
echo    - Ready for fresh data collection

pause