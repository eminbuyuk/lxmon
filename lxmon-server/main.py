"""
lxmon-server - FastAPI Backend for System Monitoring
Main application entry point with all routes and middleware.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
import logging
from datetime import datetime

from core.config import settings
from core.database import create_tables, get_db
from middleware.rate_limit import RateLimitMiddleware
from routers import agents, servers, auth, alerts
from database.redis_client import redis_client
from utils.exceptions import LxmonException, create_error_response
from utils.background_tasks import background_tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting lxmon-server...")

    # Create database tables
    await create_tables()

    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise

    # Start background tasks
    await background_tasks.start()

    logger.info("✅ lxmon-server started successfully")
    logger.info(f"📊 API Documentation: http://localhost:{settings.PORT}/docs")

    yield

    # Shutdown
    logger.info("🛑 Shutting down lxmon-server...")
    await background_tasks.stop()
    await redis_client.close()

# Create FastAPI application
app = FastAPI(
    title="lxmon-server",
    description="System monitoring server with agent management and metrics collection",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add custom middleware
app.add_middleware(RateLimitMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handlers
@app.exception_handler(LxmonException)
async def lxmon_exception_handler(request: Request, exc: LxmonException):
    """Handle custom lxmon exceptions."""
    error_response = create_error_response(exc)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict(),
        headers=exc.headers
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {"errors": exc.errors()},
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint with detailed status."""
    health_status = {
        "status": "healthy",
        "service": "lxmon-server",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # Check database
    try:
        from sqlalchemy import text
        from core.database import get_background_db_session
        db = await get_background_db_session()
        try:
            await db.execute(text("SELECT 1"))
            health_status["checks"]["database"] = "healthy"
        finally:
            await db.close()
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check Redis
    try:
        await redis_client.ping()
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check background tasks
    health_status["checks"]["background_tasks"] = "running" if background_tasks.is_running else "stopped"
    if not background_tasks.is_running:
        health_status["status"] = "unhealthy"

    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(status_code=status_code, content=health_status)

# Metrics endpoint for monitoring
@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint."""
    metrics_data = []
    metrics_data.append("# lxmon-server metrics")
    metrics_data.append(f'# Timestamp: {datetime.utcnow().isoformat()}')

    # Add custom metrics here if needed
    metrics_data.append("# Add your custom metrics here")

    return "\n".join(metrics_data)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(agents.router, prefix="/api/agent", tags=["Agent"])
app.include_router(servers.router, prefix="/api/servers", tags=["Servers"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
