#!/usr/bin/env python3
"""
Main entry point for the Agentic Transformational Layer API.
This script starts the FastAPI server with configuration from environment variables.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main function to start the FastAPI server."""
    import uvicorn
    
    # Get configuration from environment variables
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8001"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    RELOAD = os.getenv("RELOAD", "false").lower() == "true"
    
    print("="*50)
    print("🚀 Agentic Transformational Layer API")
    print("="*50)
    print(f"📍 Host: {HOST}")
    print(f"🔌 Port: {PORT}")
    print(f"🐛 Debug: {DEBUG}")
    print(f"🔄 Reload: {RELOAD}")
    print(f"📚 Docs: http://{HOST}:{PORT}/docs")
    print(f"🏥 Health: http://{HOST}:{PORT}/health")
    print("="*50)
    
    # Start the server
    uvicorn.run(
        "app.app:app",  # Use import string instead of app object
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level="debug" if DEBUG else "info",
        access_log=DEBUG
    )

if __name__ == "__main__":
    main()
