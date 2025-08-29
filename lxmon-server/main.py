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
from datetime import datetime, timedelta

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
    description="""
    # lxmon - Advanced System Monitoring Platform 🚀

    A comprehensive, production-ready system monitoring solution built with modern technologies.

    ## Features

    * **Real-time Monitoring**: Continuous system metrics collection from distributed agents
    * **Multi-tenant Architecture**: Support for multiple organizations and environments
    * **Alert Management**: Configurable alert rules with severity levels and notifications
    * **Command Execution**: Remote command execution with security controls
    * **RESTful API**: Complete REST API for integration with external systems
    * **Web Dashboard**: Modern React-based dashboard with dark mode support
    * **Background Processing**: Asynchronous task processing for metrics aggregation
    * **Rate Limiting**: Built-in rate limiting to prevent abuse
    * **Health Monitoring**: Comprehensive health checks and system status

    ## Architecture

    * **Backend**: FastAPI (Python) with async PostgreSQL and Redis
    * **Frontend**: React + TypeScript with Tailwind CSS
    * **Agent**: Go-based monitoring agent for system metrics collection
    * **Database**: PostgreSQL for persistent data storage
    * **Cache**: Redis for caching and background job queues

    ## Authentication

    The API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:
    ```
    Authorization: Bearer <your-jwt-token>
    ```

    ## Quick Start

    1. Start the services: `docker-compose up -d`
    2. Access dashboard: http://localhost:3000
    3. View API docs: http://localhost:8000/docs
    4. Check health: http://localhost:8000/health
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "lxmon Support",
        "url": "https://github.com/eminbuyuk/lxmon",
        "email": "support@lxmon.dev"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
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
@app.get("/health", tags=["System"])
async def health_check():
    """
    Comprehensive health check endpoint with detailed system status.

    Returns detailed information about:
    - Database connectivity
    - Redis connectivity
    - Background task status
    - System uptime and version info

    **Response Codes:**
    - 200: All systems healthy
    - 503: One or more systems unhealthy
    """
    import psutil
    import platform
    from datetime import datetime, timezone

    health_status = {
        "status": "healthy",
        "service": "lxmon-server",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": "unknown",
        "system": {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available
        },
        "checks": {}
    }

    # Get system uptime
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = datetime.now().timestamp() - boot_time
        health_status["uptime"] = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"
    except Exception as e:
        health_status["uptime"] = f"error: {str(e)}"

    # Check database
    try:
        from sqlalchemy import text
        from core.database import get_background_db_session
        db = await get_background_db_session()
        try:
            # Get database stats
            result = await db.execute(text("SELECT COUNT(*) as server_count FROM servers"))
            server_count = result.scalar()
            result = await db.execute(text("SELECT COUNT(*) as metric_count FROM metrics"))
            metric_count = result.scalar()

            health_status["checks"]["database"] = {
                "status": "healthy",
                "servers_registered": server_count,
                "total_metrics": metric_count
            }
        finally:
            await db.close()
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"

    # Check Redis
    try:
        pong = await redis_client.ping()
        # Get Redis stats
        info = await redis_client.get_info()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory_human", "unknown"),
            "uptime_days": info.get("uptime_in_days", 0)
        }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"

    # Check background tasks
    health_status["checks"]["background_tasks"] = {
        "status": "running" if background_tasks.is_running else "stopped",
        "active_tasks": len(background_tasks.tasks) if hasattr(background_tasks, 'tasks') else 0
    }
    if not background_tasks.is_running:
        health_status["status"] = "unhealthy"

    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(status_code=status_code, content=health_status)

# Metrics endpoint for monitoring
@app.get("/metrics", tags=["System"])
async def metrics():
    """
    Prometheus-style metrics endpoint for monitoring and alerting.

    Returns metrics in Prometheus exposition format that can be scraped by Prometheus
    or other monitoring systems.

    **Metrics Included:**
    - lxmon_server_uptime_seconds: Server uptime in seconds
    - lxmon_server_requests_total: Total HTTP requests (by method and status)
    - lxmon_database_connections_active: Active database connections
    - lxmon_redis_connected_clients: Redis connected clients
    - lxmon_servers_total: Total registered servers
    - lxmon_metrics_total: Total collected metrics
    """
    import psutil
    import time
    from datetime import datetime

    metrics_data = []
    timestamp = datetime.now().timestamp()

    # System metrics
    metrics_data.append("# lxmon-server system metrics")
    metrics_data.append(f'# Timestamp: {datetime.now().isoformat()}')

    # Server uptime
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        metrics_data.append(f"lxmon_server_uptime_seconds {uptime_seconds}")
    except:
        metrics_data.append("lxmon_server_uptime_seconds 0")

    # Memory usage
    memory = psutil.virtual_memory()
    metrics_data.append(f"lxmon_server_memory_used_bytes {memory.used}")
    metrics_data.append(f"lxmon_server_memory_available_bytes {memory.available}")
    metrics_data.append(f"lxmon_server_memory_total_bytes {memory.total}")

    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    metrics_data.append(f"lxmon_server_cpu_usage_percent {cpu_percent}")

    # Database metrics
    try:
        from sqlalchemy import text
        from core.database import get_background_db_session
        db = await get_background_db_session()
        try:
            # Server count
            result = await db.execute(text("SELECT COUNT(*) FROM servers"))
            server_count = result.scalar()
            metrics_data.append(f"lxmon_servers_total {server_count}")

            # Metric count
            result = await db.execute(text("SELECT COUNT(*) FROM metrics"))
            metric_count = result.scalar()
            metrics_data.append(f"lxmon_metrics_total {metric_count}")

            # Recent metrics (last hour)
            one_hour_ago = datetime.now() - timedelta(hours=1)
            result = await db.execute(
                text("SELECT COUNT(*) FROM metrics WHERE collected_at > :timestamp"),
                {"timestamp": one_hour_ago}
            )
            recent_metrics = result.scalar()
            metrics_data.append(f"lxmon_metrics_recent_total {recent_metrics}")

        finally:
            await db.close()
    except Exception as e:
        metrics_data.append(f"# Database metrics error: {e}")

    # Redis metrics
    try:
        info = await redis_client.get_info()
        metrics_data.append(f"lxmon_redis_connected_clients {info.get('connected_clients', 0)}")
        metrics_data.append(f"lxmon_redis_used_memory_bytes {info.get('used_memory', 0)}")
        metrics_data.append(f"lxmon_redis_uptime_seconds {info.get('uptime_in_seconds', 0)}")
    except Exception as e:
        metrics_data.append(f"# Redis metrics error: {e}")

    # Background tasks status
    tasks_running = 1 if background_tasks.is_running else 0
    metrics_data.append(f"lxmon_background_tasks_running {tasks_running}")

    return "\n".join(metrics_data)

# System info endpoint
@app.get("/api/system/info", tags=["System"])
async def system_info():
    """
    Get detailed system information and statistics.

    Returns comprehensive information about the monitoring system including:
    - System resources (CPU, memory, disk)
    - Database statistics
    - Redis statistics
    - Active servers and metrics
    - Background task status
    """
    import psutil
    import platform
    from datetime import datetime, timezone

    system_info = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system": {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "hostname": platform.node()
        },
        "resources": {
            "cpu": {
                "count": psutil.cpu_count(),
                "count_logical": psutil.cpu_count(logical=True),
                "usage_percent": psutil.cpu_percent(interval=1)
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "usage_percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "free": psutil.disk_usage('/').free,
                "used": psutil.disk_usage('/').used,
                "usage_percent": psutil.disk_usage('/').percent
            }
        }
    }

    # Database statistics
    try:
        from sqlalchemy import text
        from core.database import get_background_db_session
        db = await get_background_db_session()
        try:
            # Get various counts
            result = await db.execute(text("SELECT COUNT(*) FROM servers"))
            system_info["database"] = {
                "servers_count": result.scalar(),
                "connection_status": "healthy"
            }

            result = await db.execute(text("SELECT COUNT(*) FROM metrics"))
            system_info["database"]["metrics_count"] = result.scalar()

            result = await db.execute(text("SELECT COUNT(*) FROM alerts WHERE status = 'active'"))
            system_info["database"]["active_alerts_count"] = result.scalar()

            result = await db.execute(text("SELECT COUNT(*) FROM alert_rules WHERE enabled = true"))
            system_info["database"]["enabled_alert_rules_count"] = result.scalar()

        finally:
            await db.close()
    except Exception as e:
        system_info["database"] = {
            "connection_status": "unhealthy",
            "error": str(e)
        }

    # Redis statistics
    try:
        info = await redis_client.get_info()
        system_info["redis"] = {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "uptime_days": info.get("uptime_in_days", 0),
            "status": "healthy"
        }
    except Exception as e:
        system_info["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Background tasks status
    system_info["background_tasks"] = {
        "running": background_tasks.is_running,
        "active_tasks": len(background_tasks.tasks) if hasattr(background_tasks, 'tasks') else 0
    }

    return system_info

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
