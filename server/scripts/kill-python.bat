@echo off
echo Killing all Python processes...

REM Kill python.exe processes
taskkill /f /im python.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Killed python.exe processes
) else (
    echo - No python.exe processes found
)

REM Kill pythonw.exe processes (background Python)
taskkill /f /im pythonw.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Killed pythonw.exe processes
) else (
    echo - No pythonw.exe processes found
)

REM Kill any Python processes from different installations
for /f "tokens=1" %%i in ('tasklist /fi "imagename eq python*" /fo csv /nh 2^>nul ^| findstr /i python') do (
    set "process=%%i"
    setlocal enabledelayedexpansion
    set "process=!process:"=!"
    taskkill /f /im "!process!" >nul 2>&1
    endlocal
)

echo.
echo Done! All Python processes terminated.
echo You can now restart the server safely.

pause