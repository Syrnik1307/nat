@echo off
echo ========================================
echo   Teaching Panel - Frontend Setup
echo ========================================
echo.

cd frontend

echo [1/2] Installing npm packages...
call npm install

echo.
echo [2/2] Starting React development server...
echo.
echo Frontend will open at: http://localhost:3000
echo.

call npm start
