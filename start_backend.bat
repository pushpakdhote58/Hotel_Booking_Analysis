@echo off
title Hotel Analytics - Live Backend Server
cd /d "%~dp0"
echo ============================================================
echo   HOTEL BOOKING ANALYTICS - FASTAPI SERVER
echo ============================================================
echo   Live Web Dashboard: http://127.0.0.1:8000
echo   API Documentation:  http://127.0.0.1:8000/docs
echo   Database:           MySQL hotel_bookings_db
echo ============================================================
echo.
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server encountered an error and stopped.
    pause
)
