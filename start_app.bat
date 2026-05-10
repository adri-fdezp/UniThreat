@echo off
echo Starting UniThreat System...

:: ── Start services ─────────────────────────────────────────────────────────
echo.
echo Starting Backend...
start "UniThreat Backend" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\activate && python app.py"

echo Starting Frontend...
start "UniThreat Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo System Started!
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:5173
