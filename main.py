"""
 * ASA Policy App - FastAPI Backend
 * Main application entry point
 *
 * This file contains the FastAPI application setup and configuration
 * for the ASA Policy Management System backend.
 *
 * Public Functions:
 *    root() --> dict
 *        Returns API welcome message and status
 *    health_check() --> dict
 *        Returns API health status
 *    global_exception_handler(request: Request, exc: Exception) --> JSONResponse
 *        Handles all unhandled exceptions globally
 *
 * @author: ASA Policy App Development Team
 * @date: January 2026
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.routers import policies, bylaws, suggestions, auth
from app.core.config import settings

app = FastAPI(
    title="ASA Policy App API",
    description="Backend API for the Augustana Students' Association Policy Management System",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(policies.router, prefix="/api/policies", tags=["Policies"])
app.include_router(bylaws.router, prefix="/api/bylaws", tags=["Bylaws"])
app.include_router(suggestions.router, prefix="/api/suggestions", tags=["Suggestions"])


@app.get("/")
async def root() -> Dict[str, str]:
    """
    Root endpoint - Returns API welcome message and status
    
    Returns:
        dict: Dictionary containing API message, version, and status
    """
    return {
        "message": "ASA Policy App API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint - Used to verify API is running
    
    Returns:
        dict: Dictionary containing health status
    """
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler - Catches all unhandled exceptions
    
    Args:
        request: The HTTP request that caused the exception
        exc: The exception that was raised
        
    Returns:
        JSONResponse: JSON response with error details
    """
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
