@echo off
echo Starting AI Sales Agent Server with Live Logs...
echo ================================================
echo.

echo Clearing ports 3000 and 8000 before starting...
echo.

:: Kill any process using port 8000 (Backend API)
echo Checking port 8000 (Backend API)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo   Killing existing process %%a on port 8000...
    taskkill /PID %%a /F 2>nul
)

:: Kill any process using port 3000 (Frontend Server)
echo Checking port 3000 (Frontend Server)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do (
    echo   Killing existing process %%a on port 3000...
    taskkill /PID %%a /F 2>nul
)

:: Also kill any lingering Python HTTP server or uvicorn processes
for /f "tokens=2" %%i in ('wmic process where "name='python.exe' and CommandLine like '%%http.server%%3000%%'" get ProcessId /value 2^>nul ^| findstr ProcessId') do (
    for /f "tokens=2 delims==" %%j in ("%%i") do (
        echo   Killing Python HTTP server process %%j...
        taskkill /PID %%j /F /T 2>nul
    )
)

for /f "tokens=2" %%i in ('wmic process where "name='python.exe' and CommandLine like '%%app.main%%'" get ProcessId /value 2^>nul ^| findstr ProcessId') do (
    for /f "tokens=2 delims==" %%j in ("%%i") do (
        echo   Killing uvicorn process %%j...
        taskkill /PID %%j /F /T 2>nul
    )
)

:: Wait for ports to be released
echo.
echo Waiting for ports to clear...
timeout /t 3 /nobreak > nul

echo.
echo Ports cleared. Starting servers...
echo.
echo ================================================
echo Starting Backend API Server (Port 8000)
echo Starting Frontend Server (Port 3000)
echo ================================================
echo.
echo Access Points:
echo   Main Interface:     http://localhost:3000/unified.html
echo   Column Mapper:      http://localhost:3000/mapper.html
echo   Job Status:         http://localhost:3000/status.html
echo   History:            http://localhost:3000/history.html
echo   API Docs:           http://localhost:8000/docs
echo   API Base:           http://localhost:8000/api/v1
echo.
echo Starting in 3 seconds...
timeout /t 3 /nobreak > nul
echo.
echo ================================================
echo Press Ctrl+C to stop the servers
echo ================================================
echo.

:: Change to project directory
cd /d "C:\Users\joema\OneDrive\Documents\EZWAI\Personalized Email Marketing"

:: Run the Python server script which starts both frontend and backend
python run_server.py