@echo off
setlocal
title Evidence Integrity Platform - Frontend (Port 5173)

echo =====================================================================
echo    Evidence Integrity Platform - Frontend Server (Vite)
echo =====================================================================
echo.

cd /d "%~dp0frontend"

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js and npm were not found on your system.
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

echo Starting Vite Dev Server on http://127.0.0.1:5173 ...
npm run dev -- --host 127.0.0.1 --port 5173

pause
