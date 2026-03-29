@echo off
echo Starting UniThreat System...

echo Starting Backend...
start "UniThreat Backend" cmd /k "cd backend && .venv\Scripts\python app.py"

echo Starting Frontend...
start "UniThreat Frontend" cmd /k "cd frontend && npm run dev"

echo System Started!
echo Backend: http://localhost:5000
echo Frontend: http://localhost:5173
pause
