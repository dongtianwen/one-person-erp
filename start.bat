@echo off
cd /d "%~dp0"

echo ========================================
echo    ShuBiao Cloud Manager - Start
echo ========================================
echo.

if not exist "backend" (
    echo [ERROR] backend folder not found
    pause
    exit /b 1
)
if not exist "frontend" (
    echo [ERROR] frontend folder not found
    pause
    exit /b 1
)

where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv not found. Install: https://docs.astral.sh/uv/
    pause
    exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found. Install Node.js first.
    pause
    exit /b 1
)

echo [1/3] Starting backend...
cd backend
start "Backend" cmd /k "uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
cd ..
echo       Waiting for backend...
timeout /t 4 /nobreak >nul

echo [2/3] Starting frontend...
cd frontend
start "Frontend" cmd /k "npm run dev"
cd ..
echo       Waiting for frontend...
timeout /t 3 /nobreak >nul

echo.
echo [3/3] Opening browser...
start http://localhost:5173

echo.
echo ========================================
echo    Ready!
echo ========================================
echo.
echo  Backend API : http://localhost:8000
echo  API Docs    : http://localhost:8000/docs
echo  Frontend    : http://localhost:5173
echo.
echo  Login: admin / admin123
echo.
echo  Close the Backend/Frontend windows to stop.
echo.
pause
