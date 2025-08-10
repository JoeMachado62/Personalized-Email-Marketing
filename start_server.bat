@echo off
echo Starting AI Sales Agent Server with Live Logs...
echo ================================================
echo.
echo Server will run at: http://localhost:8000
echo Web Interface: http://localhost:3000/test.html
echo Column Mapper: http://localhost:3000/mapper.html
echo API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo ================================================
echo.
cd /d "C:\Users\joema\OneDrive\Documents\EZWAI\Personalized Email Marketing"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info --access-log