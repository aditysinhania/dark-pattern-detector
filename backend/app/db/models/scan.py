from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Integer, ForeignKey, Enum as SAEnum, Text, JSON
import enum
import uuid

from app.db.base import Base, TimestampMixin


class ScanStatus(str, enum.Enum):
    """
    Tracks exactly where a scan is in its lifecycle.

    Why this matters: scans are async (run via Celery).
    The API returns immediately with status=PENDING,
    and the client polls until status=COMPLETED or FAILED.
    This is the standard pattern for long-running async jobs.
    """
    PENDING = "pending"       # Job queued, not started
    PROCESSING = "processing" # Celery worker picked it up
    COMPLETED = "completed"   # Analysis done
    FAILED = "failed"         # Something went wrong


class RiskLevel(str, enum.Enum):
    """
    Bucketed risk levels for UI display.
    The raw risk_score (0.0-1.0) is precise,
    but humans need a label.
    """
    LOW = "low"           # 0.0 - 0.3
    MEDIUM = "medium"     # 0.3 - 0.6
    HIGH = "high"         # 0.6 - 0.8
    CRITICAL = "critical" # 0.8 - 1.0


class Scan(Base, TimestampMixin):
    """
    Represents one complete website scan request.

    A scan is the central entity — everything else
    (patterns, reports) belongs to a scan.

    raw_html and screenshot_path are stored separately
    because they're large — we don't want them in every
    query, only when explicitly needed.
    """
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(
        String(2048),    # Max URL length
        nullable=False,
    )
    status: Mapped[ScanStatus] = mapped_column(
        SAEnum(ScanStatus),
        default=ScanStatus.PENDING,
        nullable=False,
        index=True,      # We frequently filter by status
    )

    # AI analysis results
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,   # Null until scan completes
    )
    risk_level: Mapped[RiskLevel | None] = mapped_column(
        SAEnum(RiskLevel),
        nullable=True,
    )
    patterns_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    # Raw data from scraper
    page_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Celery task ID — used to check job status
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Error message if scan failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata from scraper (load time, element counts, etc.)
    scan_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="scans")
    detected_patterns: Mapped[list["DetectedPattern"]] = relationship(
        "DetectedPattern",
        back_populates="scan",
        cascade="all, delete-orphan",
    )
    report: Mapped["Report | None"] = relationship(
        "Report",
        back_populates="scan",
        uselist=False,      # One-to-one: one scan has one report
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Scan id={self.id} url={self.url} status={self.status}>"