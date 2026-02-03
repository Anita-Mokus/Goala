@echo off
REM Startup script for AI Chat Flow API Server
REM This script activates the virtual environment and starts the API

echo ============================================
echo   AI Chat Flow - Starting API Server
echo ============================================
echo.

REM Activate virtual environment
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo Warning: No virtual environment found!
    echo Please create one with: python -m venv venv
    echo.
)

REM Start the API server
echo Starting API server on http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
