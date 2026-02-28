@echo off
cd /d "%~dp0"
set BROWSER=none

echo.
echo  ================================================
echo   MCP Inspector
echo   URL: http://localhost:6274/
echo  ================================================
echo.

uv run mcp dev server.py
pause
