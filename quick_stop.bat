@echo off
echo Quick Stop - AI Sales Agent Server
echo ==================================
echo.
echo This will attempt to stop all Python processes running uvicorn.
echo Your data will be preserved due to proper shutdown handling.
echo.
set /p confirm="Continue? (y/n): "
if /i "%confirm%" neq "y" exit /b

echo Stopping server...
taskkill /IM python.exe /FI "WINDOWTITLE eq Administrator*" /T 2>nul
taskkill /F /IM python.exe /FI "MODULES eq uvicorn*" /T 2>nul

echo.
echo Server stop command sent.
echo Check your terminal window - the server should show shutdown messages.
echo.
echo Your data is safe in:
echo - data/app.db (SQLite database)
echo - uploads/ (uploaded files)
echo - outputs/ (generated files)
echo.
pause
