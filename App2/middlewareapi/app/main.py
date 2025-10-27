from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

# Import config, routers, and handlers
from .config import POLICY_API_BASE_URL
from .routes import root_router, api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Insurance Policy Processor API",
    description="Middleware for processing insurance policies with NLP and premium calculation",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# ==================== Startup & Shutdown ====================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Insurance Policy Processor API started")
    logger.info(f"Policy API URL: {POLICY_API_BASE_URL}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Insurance Policy Processor API shutting down")

# ==================== Include Routers ====================

# Include the routers from our routes.py file
app.include_router(root_router)
app.include_router(api_router)
