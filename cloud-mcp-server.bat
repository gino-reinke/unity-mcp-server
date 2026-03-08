@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo  ================================================
echo   Cloud MCP Server (Claude Web via ngrok)
echo   Transport: streamable-http on port 8000
echo  ================================================
echo.

:: Start ngrok in a new window
echo Starting ngrok on port 8000...
start "ngrok" cmd /k "ngrok http 8000"

:: Wait for ngrok to initialize
echo Waiting for ngrok to start...
timeout /t 3 /nobreak >nul

:: Try to auto-detect ngrok URL via its local API
echo Fetching ngrok public URL...
for /f "delims=" %%i in ('powershell -NoProfile -Command "try { $r = Invoke-RestMethod http://localhost:4040/api/tunnels; ($r.tunnels | Where-Object { $_.proto -eq 'https' } | Select-Object -First 1).public_url } catch { '' }"') do set NGROK_URL=%%i

if defined NGROK_URL (
    if not "!NGROK_URL!"=="" (
        echo.
        echo  Detected ngrok URL: !NGROK_URL!
        echo  Updating .env PUBLIC_URL automatically...
        powershell -NoProfile -Command "(Get-Content .env) -replace '^PUBLIC_URL=.*', 'PUBLIC_URL=!NGROK_URL!' | Set-Content .env"
        echo  .env updated.
        goto :run_server
    )
)

:: Fallback: manual URL entry
echo.
echo  Could not auto-detect ngrok URL.
echo  Check the ngrok window for your HTTPS URL (e.g. https://abc123.ngrok-free.app)
echo.
set /p NGROK_URL=  Enter the ngrok HTTPS URL:
echo.
echo  Updating .env PUBLIC_URL...
powershell -NoProfile -Command "(Get-Content .env) -replace '^PUBLIC_URL=.*', 'PUBLIC_URL=!NGROK_URL!' | Set-Content .env"
echo  .env updated.

:run_server
echo.
echo  ================================================
echo   Starting MCP Server
echo   Public URL: !NGROK_URL!
echo  ================================================
echo.

.venv\Scripts\python.exe server.py --transport streamable-http --public-url !NGROK_URL!
pause
