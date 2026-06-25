from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog

from app.core.config import settings
from app.db.session import engine
from app.api.v1 import auth, users

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting Dark Pattern Detector API",
        version="0.2.0",
        environment=settings.APP_ENV,
    )
    yield
    logger.info("Shutting down")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered dark pattern detection API",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches any unhandled exception and returns a clean JSON response
    instead of a 500 HTML page. Never expose stack traces in production.
    """
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An internal error occurred",
            "detail": str(exc) if settings.DEBUG else None,
        },
    )


# ── Routers ──────────────────────────────────────────────────────────────────

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)


# ── System endpoints ─────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "0.2.0",
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Dark Pattern Detector API",
        "docs": "/docs",
        "health": "/health",
    }