@echo off
echo Gracefully stopping AI Sales Agent Server...
echo ==========================================

:: Find the running uvicorn process
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo table ^| findstr uvicorn') do (
    set PID=%%i
    goto :found
)

:: Alternative: look for any python process running app.main
for /f "tokens=2" %%i in ('wmic process where "name='python.exe' and CommandLine like '%%app.main%%'" get ProcessId /value ^| findstr ProcessId') do (
    set PID=%%i
    if defined PID goto :found
)

echo No running server process found.
echo.
echo Possible reasons:
echo - Server is not currently running
echo - Server was started differently (not via start_server.bat)
echo - Process is running under a different name
echo.
echo To manually check for running processes:
echo   tasklist ^| findstr python
echo.
pause
exit /b 1

:found
if not defined PID (
    echo No server process found to stop.
    pause
    exit /b 1
)

echo Found server process with PID: %PID%
echo Sending graceful termination signal...

:: Send CTRL+C signal to gracefully shutdown
taskkill /PID %PID% /T

:: Wait a moment for graceful shutdown
echo Waiting for graceful shutdown...
timeout /t 3 /nobreak > nul

:: Check if process is still running
tasklist /FI "PID eq %PID%" 2>nul | find /I "%PID%" >nul
if %ERRORLEVEL% EQU 0 (
    echo Process still running, forcing termination...
    taskkill /PID %PID% /F /T
    timeout /t 1 /nobreak > nul
) else (
    echo Server stopped gracefully.
)

:: Final verification
tasklist /FI "PID eq %PID%" 2>nul | find /I "%PID%" >nul
if %ERRORLEVEL% EQU 0 (
    echo Warning: Process may still be running. Manual intervention may be required.
) else (
    echo Server successfully stopped.
    echo.
    echo Your data has been preserved:
    echo - Database: data/app.db
    echo - Uploads: uploads/ directory  
    echo - Outputs: outputs/ directory
    echo - Logs: app.log
)

echo.
echo ==========================================
pause
