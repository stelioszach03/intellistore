@echo off
REM IntelliStore Startup Script for Windows
REM This script starts all IntelliStore components

setlocal enabledelayedexpansion

REM Function to print colored output (Windows 10+)
set "ESC="

REM Check command line argument
set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=start"

goto :%ACTION% 2>nul || goto :usage

:start
echo.
echo 🚀 Starting IntelliStore...
echo.

REM Check if setup was run
if not exist "intellistore-api\venv" (
    echo ⚠️  Setup not detected. Running setup first...
    python setup.py
    echo.
)

if not exist "intellistore-ml\venv" (
    echo ⚠️  Setup not detected. Running setup first...
    python setup.py
    echo.
)

if not exist "intellistore-frontend\node_modules" (
    echo ⚠️  Setup not detected. Running setup first...
    python setup.py
    echo.
)

REM Create logs directory
if not exist "logs" mkdir logs

REM Start Core Server
if exist "intellistore-core" (
    echo ✓ Starting Core Server...
    start "IntelliStore Core Server" /D "intellistore-core" bin\server.exe
    timeout /t 2 /nobreak >nul
)

REM Start API Server
if exist "intellistore-api" (
    echo ✓ Starting API Server...
    start "IntelliStore API Server" /D "intellistore-api" venv\Scripts\python.exe main.py
    timeout /t 3 /nobreak >nul
)

REM Start ML Service
if exist "intellistore-ml" (
    echo ✓ Starting ML Service...
    start "IntelliStore ML Service" /D "intellistore-ml" venv\Scripts\python.exe simple_main.py
    timeout /t 2 /nobreak >nul
)

REM Start Tier Controller
if exist "intellistore-tier-controller" (
    echo ✓ Starting Tier Controller...
    start "IntelliStore Tier Controller" /D "intellistore-tier-controller" bin\tier-controller.exe
    timeout /t 2 /nobreak >nul
)

REM Wait for backend services
echo ⏳ Waiting for backend services to initialize...
timeout /t 5 /nobreak >nul

REM Start Frontend
if exist "intellistore-frontend" (
    echo ✓ Starting Frontend...
    start "IntelliStore Frontend" /D "intellistore-frontend" npm run dev
)

echo.
echo 🎉 IntelliStore started successfully!
echo.
echo 📍 Access points:
echo   • Frontend: http://localhost:51017
echo   • API: http://localhost:8000
echo   • API Docs: http://localhost:8000/docs
echo.
echo 💡 Use 'start.bat stop' to stop all services
echo 💡 Use 'start.bat status' to check service status
goto :end

:stop
echo.
echo 🛑 Stopping IntelliStore components...

REM Kill processes by window title
taskkill /FI "WINDOWTITLE:IntelliStore*" /F >nul 2>&1

REM Kill by process name
taskkill /IM "server.exe" /F >nul 2>&1
taskkill /IM "tier-controller.exe" /F >nul 2>&1
taskkill /F /IM python.exe /FI "COMMANDLINE:*main.py*" >nul 2>&1
taskkill /F /IM python.exe /FI "COMMANDLINE:*inference*" >nul 2>&1
taskkill /F /IM node.exe /FI "COMMANDLINE:*vite*" >nul 2>&1

echo ✓ All IntelliStore components stopped
goto :end

:restart
call :stop
timeout /t 2 /nobreak >nul
call :start
goto :end

:status
echo.
echo 📊 IntelliStore Component Status:
echo.

REM Check if processes are running
tasklist /FI "IMAGENAME eq server.exe" 2>nul | find /I "server.exe" >nul
if %ERRORLEVEL%==0 (
    echo   Core Server: ✅ RUNNING
) else (
    echo   Core Server: ❌ STOPPED
)

tasklist /FI "COMMANDLINE:*main.py*" 2>nul | find /I "python.exe" >nul
if %ERRORLEVEL%==0 (
    echo   API Server: ✅ RUNNING
) else (
    echo   API Server: ❌ STOPPED
)

tasklist /FI "COMMANDLINE:*inference*" 2>nul | find /I "python.exe" >nul
if %ERRORLEVEL%==0 (
    echo   ML Service: ✅ RUNNING
) else (
    echo   ML Service: ❌ STOPPED
)

tasklist /FI "IMAGENAME eq tier-controller.exe" 2>nul | find /I "tier-controller.exe" >nul
if %ERRORLEVEL%==0 (
    echo   Tier Controller: ✅ RUNNING
) else (
    echo   Tier Controller: ❌ STOPPED
)

tasklist /FI "COMMANDLINE:*vite*" 2>nul | find /I "node.exe" >nul
if %ERRORLEVEL%==0 (
    echo   Frontend: ✅ RUNNING
) else (
    echo   Frontend: ❌ STOPPED
)

echo.
goto :end

:usage
echo.
echo Usage: start.bat {start^|stop^|restart^|status}
echo.
echo Commands:
echo   start    - Start all IntelliStore components
echo   stop     - Stop all IntelliStore components
echo   restart  - Restart all IntelliStore components
echo   status   - Show status of all components
echo.
goto :end

:end
endlocal