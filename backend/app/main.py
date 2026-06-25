from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.core.config import settings

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager runs on startup and shutdown.
    This replaced the older @app.on_event("startup") pattern in FastAPI 0.95+.
    On startup: connect to DB, warm up caches, load models.
    On shutdown: close connections cleanly.
    """
    logger.info("Starting Dark Pattern Detector API", version="0.1.0")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered dark pattern detection API",
    version="0.1.0",
    docs_url="/docs",          # Swagger UI at /docs
    redoc_url="/redoc",        # ReDoc at /redoc
    lifespan=lifespan,
)

# CORS — controls which frontends can call this API
# In production this will be your actual domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    Used by Docker healthchecks, load balancers, and monitoring tools.
    Returns 200 if the server is running.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Dark Pattern Detector API",
        "docs": "/docs",
    }