"""
FastAPI application definition for the Agentic Transformational Layer.
This module initializes the FastAPI app and includes the API routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add parent directory to path so we can import from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import API routes
from app.api import router as api_router

def create_app():
    """Create and configure the FastAPI application."""
    
    # Get configuration from environment variables (loaded in main.py)
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_CREDENTIALS = os.getenv("CORS_CREDENTIALS", "true").lower() == "true"
    CORS_METHODS = os.getenv("CORS_METHODS", "*").split(",")
    CORS_HEADERS = os.getenv("CORS_HEADERS", "*").split(",")

    # Initialize FastAPI app
    app = FastAPI(
        title="Agentic Transformational Layer API",
        description="API for CSV processing, smart filtering, preprocessing, schema mapping, and Supabase integration",
        version="1.0.0",
        debug=DEBUG
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=CORS_CREDENTIALS,
        allow_methods=CORS_METHODS,
        allow_headers=CORS_HEADERS,
    )

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint providing API information."""
        return {
            "message": "Agentic Transformational Layer API",
            "version": "1.0.0",
            "docs": "/docs",
            "endpoints": {
                "upload_csv": "/api/v1/upload-csv",
                "smart_filter": "/api/v1/smart-filter", 
                "preprocess": "/api/v1/preprocess",
                "schema_map": "/api/v1/schema-map",
                "save_db": "/api/v1/save-db"
            }
        }

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "agentic-transformational-layer"}
    
    return app

# Create the app instance
app = create_app()