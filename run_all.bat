@echo off
setlocal
title Evidence Integrity Platform - One-Click Launcher

echo =====================================================================
echo        EVIDENCE INTEGRITY FORENSIC PLATFORM - SMART LAUNCHER
echo =====================================================================
echo.

cd /d "%~dp0"
set "BACKEND_DIR=%~dp0backend"
set "FRONTEND_DIR=%~dp0frontend"
set "VENV_PYTHON=%BACKEND_DIR%\.venv\Scripts\python.exe"

REM Add FFmpeg to PATH if installed via WinGet
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin" (
    set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin;%PATH%"
)

REM Verify Python backend environment
if exist "%VENV_PYTHON%" goto VENV_OK

echo [*] Setting up Python virtual environment (one-time setup)...
cd /d "%BACKEND_DIR%"
python -m venv .venv
if errorlevel 1 goto PYTHON_ERR

echo [*] Installing required backend packages...
"%VENV_PYTHON%" -m pip install -r requirements.txt
cd /d "%~dp0"

:VENV_OK
echo [OK] Backend virtual environment verified.

REM Check if npm is available
where npm >nul 2>&1
set "NPM_FOUND=%ERRORLEVEL%"

echo.
echo [*] Launching Backend Server on http://127.0.0.1:8000 ...
start "Evidence Integrity Platform - Backend (Port 8000)" cmd /k "cd /d "%BACKEND_DIR%" && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

if %NPM_FOUND% equ 0 goto LAUNCH_FRONTEND

echo [*] npm not found - serving pre-built UI via FastAPI on http://localhost:8000 ...
ping 127.0.0.1 -n 4 >nul
start http://localhost:8000
goto SHOW_CREDENTIALS

:LAUNCH_FRONTEND
echo [*] Launching Frontend Server on http://127.0.0.1:5173 ...
start "Evidence Integrity Platform - Frontend (Port 5173)" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev -- --host 127.0.0.1 --port 5173"

echo [*] Waiting for services to initialize...
ping 127.0.0.1 -n 4 >nul

echo [*] Opening Evidence Integrity Platform in your default web browser...
start http://localhost:5173

:SHOW_CREDENTIALS
echo.
echo =====================================================================
echo  PLATFORM SUCCESSFULLY LAUNCHED!
echo =====================================================================
echo.
echo  Access URLs:
echo    Web Application : http://localhost:5173  (or http://localhost:8000)
echo    API Documentation: http://localhost:8000/docs
echo.
echo  Default Login Accounts:
echo    Lead Developer / Admin:
echo      Username: Krishna  (or krishnadeshmukh721@gmail.com)
echo      Password: Krishna@0305
echo.
echo    Forensic Specialist:
echo      Username: nida
echo      Password: Nida@2026
echo.
echo    Examiner:
echo      Username: meera
echo      Password: ram@1234
echo.
echo =====================================================================
echo  Keep the opened server windows open while using the platform.
echo  To stop the application, simply close the terminal windows.
echo =====================================================================
echo.
pause
exit /b 0

:PYTHON_ERR
echo.
echo [ERROR] Python was not found on your system.
echo Please ensure Python 3.10+ is installed and check "Add Python to PATH".
echo.
pause
exit /b 1
