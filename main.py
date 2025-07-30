from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from app.core.config import settings
from app.api.auth.auth import router as auth_router
from app.api.documents.documents import router as documents_router
from app.api.search.search import router as search_router
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered document intelligence platform with secure processing and RAG-based search",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(search_router)


@app.get("/")
async def root():
    return {
        "message": "Document Intelligence Platform API",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version
    }


@app.get("/status")
async def status_check():
    from app.services.document_processing_service import DocumentProcessingService
    from app.utils.redis_client import get_redis_client

    try:
        processing_service = DocumentProcessingService()
        services_status = processing_service.get_processing_services_status()
        
        # Check Redis connection
        redis_client = get_redis_client()
        redis_status = "connected" if redis_client.ping() else "disconnected"
        
        # Check Celery worker status (basic check)
        try:
            from app.celery_app import celery_app
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            worker_status = "running" if active_workers else "not running"
        except Exception:
            worker_status = "unknown"

        return {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.app_version,
            "services": services_status,
            "redis": redis_status,
            "celery_worker": worker_status
        }
    except Exception as e:
        return {
            "status": "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.app_version,
            "error": str(e)
        }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return {
        "error": "Internal server error",
        "status_code": 500,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings  # ← Make sure this points to your config

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",  # Use localhost for local testing
        port=8000,
        reload=settings.debug
    )
