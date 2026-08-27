@echo off
:: Switch to the directory where this script is located
cd /d "%~dp0"

title HeritageVoice AI Launcher
echo ===================================================
echo   HeritageVoice AI - Multilingual Smart Tour Guide
echo   OMNIKON National Hackathon 2026
echo ===================================================
echo.

:: Diagnostics: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please install Python (and make sure to check "Add Python to PATH").
    echo.
    pause
    exit /b
)

:: Diagnostics: Check if Node.js is available
node -v >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in your system PATH!
    echo Please install Node.js from https://nodejs.org/
    echo.
    pause
    exit /b
)

:: Check for .env file setup
if exist "backend\.env" (
    echo [INFO] Found .env file in backend/
) else (
    echo [WARNING] backend/.env file not found.
    echo Copying backend/.env.example to backend/.env...
    copy backend\.env.example backend\.env
    echo [IMPORTANT] Please open backend/.env and add your Gemini API key.
    echo.
)

:: Start Backend in a separate window
echo [1/2] Starting FastAPI Backend on http://127.0.0.1:8000...
start "HeritageVoice Backend (FastAPI)" cmd /c "cd backend && python main.py"

:: Start Frontend in a separate window
echo [2/2] Starting Next.js Frontend on http://localhost:3000...
start "HeritageVoice Frontend (Next.js)" cmd /c "cd frontend && npm run dev"

echo.
echo ===================================================
echo   Both services are launching in separate windows!
echo   - Backend: http://127.0.0.1:8000
echo   - Frontend: http://localhost:3000
echo.
echo   If the new windows do not appear, you can run:
echo     1. Open command prompt in this folder
echo     2. Run the command: npm run dev --prefix frontend
echo     3. Run the command: python backend/main.py
echo ===================================================
echo.
echo Press any key to exit this launcher window...
pause >nul
