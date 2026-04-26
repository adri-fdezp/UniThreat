@echo off
setlocal disabledelayedexpansion
echo Starting UniThreat System...

:: ── Load API key from .env file ──────────────────────────────────────────
set ENV_FILE=%~dp0.env
set ANTHROPIC_API_KEY=

if exist "%ENV_FILE%" (
    for /f "tokens=1,* delims==" %%A in ('findstr /i "ANTHROPIC_API_KEY" "%ENV_FILE%"') do (
        set ANTHROPIC_API_KEY=%%B
    )
)

:: If key is missing or still a placeholder, ask the user and save it
if "%ANTHROPIC_API_KEY%"=="" goto :ask_key
if "%ANTHROPIC_API_KEY%"=="sk-ant-..." goto :ask_key
goto :start

:ask_key
echo.
echo No ANTHROPIC_API_KEY found in .env
set /p ANTHROPIC_API_KEY=Paste your Anthropic API key:
echo ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY%> "%ENV_FILE%"
echo Key saved to .env

:start
:: ── Start services ────────────────────────────────────────────────────────
echo.
echo Starting Backend...
start "UniThreat Backend" cmd /k "cd /d "%~dp0backend" && set ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY% && .venv\Scripts\python app.py"

echo Starting Frontend...
start "UniThreat Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo System Started!
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:5173

