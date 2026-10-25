@echo off
title Vela AI Concierge
echo ========================================================
echo   ⚡ ANTIGRAVITY AI - DIGITAL RETAIL CONCIERGE ⚡
echo ========================================================
echo.
echo Launching backend server on http://127.0.0.1:8000...
echo Opening browser in 2 seconds...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000
python app.py
pause

