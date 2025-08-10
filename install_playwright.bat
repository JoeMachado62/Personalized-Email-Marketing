@echo off
echo Installing Playwright for web scraping...
echo ================================================
echo.
pip install playwright
echo.
echo Installing Chromium browser...
playwright install chromium
echo.
echo ================================================
echo Playwright installation complete!
echo.
pause