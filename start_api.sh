#!/bin/bash
# Startup script for AI Chat Flow API Server (Linux/Mac)
# This script activates the virtual environment and starts the API

echo "============================================"
echo "  AI Chat Flow - Starting API Server"
echo "============================================"
echo ""

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Warning: No virtual environment found!"
    echo "Please create one with: python -m venv venv"
    echo ""
fi

# Start the API server
echo "Starting API server on http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
