@echo off
REM Development startup script for Windows

echo 🚀 Starting Agentic Transformational Layer API in development mode...

REM Check if .env file exists
if not exist .env (
    echo ⚠️  .env file not found. Creating from .env.example...
    copy .env.example .env
    echo 📝 Please edit .env file with your configuration before running again.
    pause
    exit /b 1
)

REM Set development environment variables
set DEBUG=true
set RELOAD=true

REM Start the server
python main.py

pause
