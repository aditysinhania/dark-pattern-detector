from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.core.config import settings
from app.db.session import engine
from app.db.base import Base

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting Dark Pattern Detector API",
        version="0.1.0",
        environment=settings.APP_ENV,
    )
    yield
    logger.info("Shutting down — closing database connections")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered dark pattern detection API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "0.1.0",
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Dark Pattern Detector API",
        "docs": "/docs",
        "health": "/health",
    }