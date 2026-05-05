#!/bin/bash

# Auralis Training Interface - Quick Start Script
# This script starts both the Flask backend and React frontend

echo ""
echo "============================================================"
echo "AURALIS TRAINING INTERFACE - QUICK START"
echo "============================================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    exit 1
fi

# Check if Node/npm is available
if ! command -v npm &> /dev/null; then
    echo "ERROR: Node.js/npm is not installed"
    exit 1
fi

echo "✓ Python found: $(python3 --version)"
echo "✓ Node.js found: $(npm --version)"
echo ""

# Check if audio config exists
if [ ! -f "audio_config.json" ]; then
    echo "WARNING: audio_config.json not found"
    echo "Run: python3 utils/audio_config.py"
    echo ""
fi

# Function to handle cleanup
cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up trap for Ctrl+C
trap cleanup SIGINT

# Start Flask backend
echo "Starting Flask API server on http://localhost:5000"
echo "┌─────────────────────────────────────────┐"
echo "│ Flask Backend (Ctrl+C to stop)          │"
echo "└─────────────────────────────────────────┘"
echo ""

python3 api_server.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

echo ""
echo "Starting React UI on http://localhost:5173"
echo "┌─────────────────────────────────────────┐"
echo "│ React Frontend (Ctrl+C to stop)         │"
echo "└─────────────────────────────────────────┘"
echo ""

cd ui/web
npm run dev &
FRONTEND_PID=$!

echo ""
echo "============================================================"
echo "Both servers are running!"
echo ""
echo "Backend:  http://localhost:5000"
echo "Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "============================================================"
echo ""

# Wait for both processes
wait
