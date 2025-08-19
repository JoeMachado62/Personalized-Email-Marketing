"""
Main FastAPI application entry point.
Handles application initialization, middleware setup, and route registration.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import sys
import time
from pathlib import Path
import asyncio

from app.db.connection import init_db
from app.api import jobs, health, column_mapper
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log") if Path("app.log").parent.exists() else logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info("Initializing database...")
    
    try:
        init_db()
        logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Ensure directories exist
    settings.UPLOAD_DIR.mkdir(exist_ok=True)
    settings.OUTPUT_DIR.mkdir(exist_ok=True)
    settings.DATA_DIR.mkdir(exist_ok=True)
    
    logger.info(f"Upload directory: {settings.UPLOAD_DIR}")
    logger.info(f"Output directory: {settings.OUTPUT_DIR}")
    logger.info(f"Data directory: {settings.DATA_DIR}")
    
    # Log configuration
    logger.info(f"Max file size: {settings.MAX_FILE_SIZE_MB}MB")
    logger.info(f"Max records per job: {settings.MAX_RECORDS_PER_JOB}")
    logger.info(f"Max concurrent enrichments: {settings.MAX_CONCURRENT_ENRICHMENTS}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"LLM Model: {settings.LLM_MODEL}")
    logger.info(f"API Key configured: {'Yes' if settings.LLM_API_KEY else 'No'}")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Autonomous email enrichment and generation platform for sales teams",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = time.time()
    
    # Log request
    logger.info(f"{request.method} {request.url.path} - Client: {request.client.host}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    
    return response

# Register routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(column_mapper.router, prefix="/api/v1/mapping", tags=["column_mapping"])

# Mount static files (if frontend directory exists)
static_dir = Path("frontend")
if static_dir.exists():
    # Mount under /static for CSS/JS
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    # Also mount at root for HTML files
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    logger.info(f"Mounted static files from {static_dir}")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.VERSION,
        "description": "Autonomous email enrichment and generation platform",
        "docs": "/docs",
        "health": "/api/v1/health",
        "api_version": "v1"
    }

@app.get("/api/v1")
async def api_info():
    """API version information"""
    return {
        "api_version": "v1",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "endpoints": {
            "jobs": "/api/v1/jobs/",
            "health": "/api/v1/health",
            "docs": "/docs"
        }
    }

# Error handlers
from fastapi.responses import JSONResponse

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"The requested resource '{request.url.path}' was not found"
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )

if __name__ == "__main__":
    import uvicorn
    import time
    
    # Add batch monitor endpoints
    @app.get("/api/v1/batch-monitor")
    async def get_batch_monitor():
        """Get batch processing monitor data"""
        import subprocess
        import json
        from pathlib import Path
        
        try:
            # Run the monitor script to get JSON data
            result = subprocess.run(
                ["python", "monitor_batch_advanced.py", "--once", "--json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                # Add recent logs
                log_file = Path("batch_processing.log")
                if log_file.exists():
                    logs = subprocess.run(
                        ["tail", "-10", str(log_file)],
                        capture_output=True,
                        text=True
                    ).stdout.split('\n')
                    data['recent_logs'] = [line for line in logs if line.strip()]
                
                return data
            else:
                return {"error": "Failed to get monitor data", "process_running": False}
                
        except Exception as e:
            return {"error": str(e), "process_running": False}
    
    @app.post("/api/v1/batch-monitor/stop")
    async def stop_batch_monitor():
        """Stop the batch processing"""
        import subprocess
        
        try:
            subprocess.run(["pkill", "-f", "simple_batch_processor"], check=False)
            return {"success": True, "message": "Stop signal sent"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )