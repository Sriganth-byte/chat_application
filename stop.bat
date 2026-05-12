@echo off
title MindConnect - Stopping Services
color 0C

echo.
echo  Stopping all MindConnect services...
echo.

taskkill /FI "WINDOWTITLE eq MindConnect - Redis*"   /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq MindConnect - Django*"  /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq MindConnect - React*"   /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Redis*"                 /F >nul 2>&1

:: Kill by process name as fallback
taskkill /IM redis-server.exe /F >nul 2>&1
taskkill /IM daphne.exe       /F >nul 2>&1

echo  All services stopped.
echo.
pause
