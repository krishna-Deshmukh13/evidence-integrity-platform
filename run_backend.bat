@echo off
setlocal
title Evidence Integrity Platform - Backend (Port 8000)

echo =====================================================================
echo    Evidence Integrity Platform - Backend Server (FastAPI)
echo =====================================================================
echo.

cd /d "%~dp0backend"

REM Add FFmpeg to PATH if installed via WinGet
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin" (
    set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin;%PATH%"
)

if not exist .venv\Scripts\python.exe (
    echo [ERROR] Python virtual environment not found in backend\.venv
    echo Run: python -m venv .venv
    echo Then: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo Starting FastAPI backend on http://127.0.0.1:8000 ...
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
