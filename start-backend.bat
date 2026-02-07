@echo off
REM Start backend development server (Windows)

cd backend

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Install Playwright browsers (optional)
echo Installing Playwright browsers...
playwright install chromium

REM Start server
echo Starting backend server on http://localhost:8000
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
