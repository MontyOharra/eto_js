@echo off
REM Setup Script for Windows
REM Equivalent to: make setup
REM
REM This script:
REM   1. Creates Python virtual environment (.venv)
REM   2. Upgrades pip
REM   3. Installs production and development dependencies
REM   4. Creates logs and storage directories

REM Change to the directory where this script is located
cd /d "%~dp0"

echo ============================================================
echo   Setup Script
echo ============================================================
echo.

REM Step 1: Create virtual environment
echo Creating Python virtual environment...
if exist .venv (
    echo Virtual environment already exists, skipping creation
) else (
    py -m venv .venv
    echo Virtual environment created
)
echo.

REM Step 2: Upgrade pip
echo Upgrading pip...
.venv\Scripts\python -m pip install --upgrade pip
echo.

REM Step 3: Install dependencies
echo Installing production dependencies...
.venv\Scripts\pip install -r requirements.txt
echo.

echo Installing development dependencies...
.venv\Scripts\pip install -r requirements-dev.txt
echo.

REM Step 4: Create directories
echo Creating logs and storage directories...
if not exist logs mkdir logs
if not exist storage mkdir storage
echo Directories created: logs/, storage/
echo.

echo ============================================================
echo   Setup Complete!
echo   Run 'run_server.bat' to start the development server
echo ============================================================
