@echo off
REM Auralis Training Interface - Quick Start Script
REM This script starts both the Flask backend and React frontend

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo AURALIS TRAINING INTERFACE - QUICK START
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Node/npm is available
npm --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js/npm is not installed or not in PATH
    pause
    exit /b 1
)

echo ✓ Python found
echo ✓ Node.js found
echo.

REM Check if audio config exists
if not exist "audio_config.json" (
    echo WARNING: audio_config.json not found
    echo Run: python utils/audio_config.py
    echo.
)

REM Start Flask backend in new window
echo Starting Flask API server on http://localhost:5000
echo ┌─────────────────────────────────────────┐
echo │ Flask Backend (Press Ctrl+C to stop)    │
echo └─────────────────────────────────────────┘
echo.

start "Auralis API Server" cmd /k python api_server.py

REM Wait for backend to start
timeout /t 3 /nobreak

REM Start React frontend in new window
echo.
echo Starting React UI on http://localhost:5173
echo ┌─────────────────────────────────────────┐
echo │ React Frontend (Press Ctrl+C to stop)   │
echo └─────────────────────────────────────────┘
echo.

cd ui\web
start "Auralis Training UI" cmd /k npm run dev

echo.
echo ============================================================
echo Both servers are starting...
echo.
echo Backend: http://localhost:5000
echo Frontend: http://localhost:5173
echo.
echo Press any key to close this window
echo (The servers will continue running in their own windows)
echo ============================================================
echo.

pause
