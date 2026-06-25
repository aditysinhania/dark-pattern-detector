from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Pydantic automatically reads from .env file and validates types.
    If a required variable is missing, the app fails at startup with
    a clear error — not silently at runtime.
    """

    # Application
    APP_NAME: str = "Dark Pattern Detector"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    DATABASE_URL: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Files
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 10

    # AI
    MODEL_PATH: str = "./ai/models"
    MODEL_VERSION: str = "v1"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Single instance used across the entire app
# Import this everywhere: from app.core.config import settings
settings = Settings()