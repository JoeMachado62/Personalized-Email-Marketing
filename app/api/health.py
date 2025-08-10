"""
Health check endpoints for monitoring application status.
"""

from fastapi import APIRouter, HTTPException
from app.config import settings
from app.db.connection import get_db
import sqlite3
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": settings.APP_NAME,
        "version": settings.VERSION
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including database connectivity"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "checks": {}
    }
    
    # Check database connectivity
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM jobs")
            job_count = cursor.fetchone()[0]
            health_status["checks"]["database"] = {
                "status": "healthy",
                "job_count": job_count
            }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check file system access
    try:
        settings.UPLOAD_DIR.exists()
        settings.OUTPUT_DIR.exists()
        settings.DATA_DIR.exists()
        health_status["checks"]["filesystem"] = {
            "status": "healthy",
            "upload_dir": str(settings.UPLOAD_DIR),
            "output_dir": str(settings.OUTPUT_DIR),
            "data_dir": str(settings.DATA_DIR)
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["filesystem"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check configuration
    health_status["checks"]["configuration"] = {
        "status": "healthy",
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "max_records_per_job": settings.MAX_RECORDS_PER_JOB,
        "max_concurrent_enrichments": settings.MAX_CONCURRENT_ENRICHMENTS,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "has_api_key": bool(settings.LLM_API_KEY)
    }
    
    return health_status