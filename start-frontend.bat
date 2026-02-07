@echo off
REM Start frontend development server (Windows)

cd frontend

REM Install dependencies if node_modules doesn't exist
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
)

REM Start dev server
echo Starting frontend on http://localhost:3000
npm run dev
