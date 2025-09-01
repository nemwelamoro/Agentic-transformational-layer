#!/bin/bash
# Development startup script for Unix/Linux/Mac

echo "🚀 Starting Agentic Transformational Layer API in development mode..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration before running again."
    exit 1
fi

# Set development environment variables
export DEBUG=true
export RELOAD=true

# Start the server
python main.py
