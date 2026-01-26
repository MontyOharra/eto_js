@echo off
REM Database Migration Script for Windows
REM Equivalent to: alembic upgrade head
REM
REM This script applies any pending Alembic migrations to the database.
REM Safe to re-run at any time - if no pending migrations, does nothing.
REM
REM FIRST-TIME SETUP (one-time only, before running this script):
REM   .venv\Scripts\activate
REM   alembic stamp 83cd3c12da09

REM Change to the directory where this script is located
cd /d "%~dp0"

echo ============================================================
echo   Database Migration Script
echo ============================================================
echo.

call .venv\Scripts\activate

echo Current migration state:
alembic current
echo.

echo Applying pending migrations...
alembic upgrade head
echo.

echo Final migration state:
alembic current
echo.

echo ============================================================
echo   Migration Complete!
echo ============================================================
