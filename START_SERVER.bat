@echo off
echo ============================================
echo    Starting Django Deduplication Server
echo ============================================
echo.
cd /d "%~dp0\Removing-Multiple-Votes-by-using-De-duplication-analysis-main"

set "PY_CMD=py -3.11"
if exist "..\.venv\Scripts\python.exe" (
    set "PY_CMD=..\.venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
)

echo Running database migrations...
%PY_CMD% manage.py migrate
echo.
echo Starting server at http://127.0.0.1:8000/
echo Press Ctrl+C to stop the server.
echo.
%PY_CMD% manage.py runserver 127.0.0.1:8000
pause
