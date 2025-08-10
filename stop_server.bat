@echo off
echo Forcefully stopping AI Sales Agent Server and clearing ports...
echo ==========================================
echo.

echo Step 1: Killing processes on port 8000 (Backend API)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo   Found process %%a on port 8000
    taskkill /PID %%a /F 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo   Successfully killed process %%a
    ) else (
        echo   Process %%a already terminated or access denied
    )
)

echo.
echo Step 2: Killing processes on port 3000 (Frontend Server)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do (
    echo   Found process %%a on port 3000
    taskkill /PID %%a /F 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo   Successfully killed process %%a
    ) else (
        echo   Process %%a already terminated or access denied
    )
)

echo.
echo Step 3: Killing any Python/uvicorn processes...
:: Kill any uvicorn processes
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo table ^| findstr uvicorn') do (
    echo   Found Python process %%i running uvicorn
    taskkill /PID %%i /F /T 2>nul
)

:: Kill any python processes with app.main
for /f "tokens=2" %%i in ('wmic process where "name='python.exe' and CommandLine like '%%app.main%%'" get ProcessId /value 2^>nul ^| findstr ProcessId') do (
    for /f "tokens=2 delims==" %%j in ("%%i") do (
        echo   Found Python process %%j running app.main
        taskkill /PID %%j /F /T 2>nul
    )
)

:: Kill any python HTTP server processes on port 3000
for /f "tokens=2" %%i in ('wmic process where "name='python.exe' and CommandLine like '%%http.server%%3000%%'" get ProcessId /value 2^>nul ^| findstr ProcessId') do (
    for /f "tokens=2 delims==" %%j in ("%%i") do (
        echo   Found Python HTTP server process %%j
        taskkill /PID %%j /F /T 2>nul
    )
)

echo.
echo Waiting for ports to be released...
timeout /t 2 /nobreak > nul

echo.
echo Verifying ports are clear...
netstat -ano | findstr :8000 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   [OK] Port 8000 is now free (Backend API)
) else (
    echo   [WARNING] Port 8000 may still be in use
    echo   You may need to manually kill the process or wait a moment
)

netstat -ano | findstr :3000 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   [OK] Port 3000 is now free (Frontend Server)
) else (
    echo   [WARNING] Port 3000 may still be in use
    echo   You may need to manually kill the process or wait a moment
)

echo.
echo Server stopping process complete.
echo.
echo Your data has been preserved:
echo - Database: data/app.db
echo - Uploads: uploads/ directory  
echo - Outputs: outputs/ directory
echo - Logs: app.log
echo.
echo ==========================================
pause