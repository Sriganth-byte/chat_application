@echo off
title MindConnect Startup
color 0A
setlocal

echo.
echo  ==========================================
echo   MindConnect - Starting All Services
echo  ==========================================
echo.

:: ── 1. Redis ────────────────────────────────────────────────────
echo  [1/5] Starting Redis...
:: Try default install path first, then PATH
if exist "C:\Program Files\Redis\redis-server.exe" (
    start "MindConnect - Redis" cmd /k "color 0B && title MindConnect - Redis && C:\Program Files\Redis\redis-server.exe --port 6379"
) else if exist "C:\Program Files\Microsoft Visual Studio\Shared\Python39_64\Scripts\redis-server.exe" (
    start "MindConnect - Redis" cmd /k "color 0B && title MindConnect - Redis && redis-server --port 6379"
) else (
    start "MindConnect - Redis" cmd /k "color 0B && title MindConnect - Redis && redis-server --port 6379"
)
timeout /t 3 /nobreak >nul

:: ── 2. Django / Daphne ASGI ─────────────────────────────────────
echo  [2/5] Starting Django (Daphne ASGI on :8000)...
start "MindConnect - Django" cmd /k "color 0E && title MindConnect - Django && cd /d c:\Projects\MindConnect && call venv\Scripts\activate.bat && python manage.py migrate --run-syncdb && daphne -b 0.0.0.0 -p 8000 backend.asgi:application"
timeout /t 6 /nobreak >nul

:: ── 3. Celery Worker ────────────────────────────────────────────
echo  [3/5] Starting Celery Worker...
start "MindConnect - Celery Worker" cmd /k "color 06 && title MindConnect - Celery Worker && cd /d c:\Projects\MindConnect && call venv\Scripts\activate.bat && celery -A backend worker --loglevel=info --concurrency=2 -P solo"
timeout /t 3 /nobreak >nul

:: ── 4. Celery Beat ──────────────────────────────────────────────
echo  [4/5] Starting Celery Beat (scheduler)...
start "MindConnect - Celery Beat" cmd /k "color 05 && title MindConnect - Celery Beat && cd /d c:\Projects\MindConnect && call venv\Scripts\activate.bat && celery -A backend beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler"
timeout /t 2 /nobreak >nul

:: ── 5. React / Vite Frontend ────────────────────────────────────
echo  [5/5] Starting React frontend (Vite on :3000)...
start "MindConnect - React" cmd /k "color 0D && title MindConnect - React && cd /d c:\Projects\MindConnect\frontend && npm run dev"
timeout /t 4 /nobreak >nul

echo.
echo  ==========================================
echo   All 5 services launched!
echo  ==========================================
echo.
set "LAN_IP="
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /C:"IPv4 Address"') do (
    if not defined LAN_IP (
        for /f "tokens=* delims= " %%B in ("%%A") do set "LAN_IP=%%B"
    )
)
echo   App (local)  : https://localhost:3000
if defined LAN_IP (
    echo   App (network): https://%LAN_IP%:3000
) else (
    echo   App (network): Run ipconfig and use your Wi-Fi IPv4 address on port 3000
)
echo   API          : http://localhost:8000/api/
echo   Admin panel  : http://localhost:8000/admin/
echo   API Docs     : http://localhost:8000/api/docs/
echo   Health check : http://localhost:8000/api/health/
echo.
echo   Login (demo) : alice_j@demo.mindconnect.app / Demo@123!
echo   Login (admin): admin / Admin@123!
echo.
echo   To seed test data:
echo   cd c:\Projects\MindConnect
echo   venv\Scripts\python.exe manage.py seed_data
echo.
timeout /t 5 /nobreak >nul
start http://localhost:3000
