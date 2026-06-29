from pydantic import BaseModel, HttpUrl, field_validator
from datetime import datetime
from typing import Optional
import uuid

from app.db.models.scan import ScanStatus, RiskLevel
from app.schemas.common import DataResponse


class ScanRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


class ScanResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    url: str
    status: ScanStatus
    risk_score: Optional[float] = None
    risk_level: Optional[RiskLevel] = None
    patterns_found: int
    page_title: Optional[str] = None
    screenshot_path: Optional[str] = None
    task_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime


class ScanDetailResponse(ScanResponse):
    """Full scan response including detected patterns."""
    detected_patterns: list[dict] = []


class PatternResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    category: str
    detection_method: str
    confidence_score: float
    explanation: str
    flagged_text: Optional[str] = None
    suggestion: Optional[str] = None