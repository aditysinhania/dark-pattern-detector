from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Text, JSON, Boolean
import uuid

from app.db.base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    """
    A generated report for a completed scan.

    Separate from Scan because report generation is its own
    async step — a scan completes, then a report is generated.
    Reports can also be regenerated without re-scanning.

    Reports are what users save, share, and download.
    """
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"),
        unique=True,    # One report per scan
        nullable=False,
    )

    # Summary fields (denormalized for fast dashboard queries)
    # These duplicate data from Scan/DetectedPattern but avoid
    # expensive JOINs when listing reports
    total_patterns: Mapped[int] = mapped_column(default=0)
    risk_score: Mapped[float] = mapped_column(default=0.0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Full structured report data as JSON
    # Includes pattern breakdown, recommendations, metadata
    report_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Path to generated PDF (if user requested it)
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Whether the user has saved/bookmarked this report
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False)

    # Share token — allows sharing report via URL without login
    share_token: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )

    # Relationship
    scan: Mapped["Scan"] = relationship("Scan", back_populates="report")

    def __repr__(self) -> str:
        return f"<Report id={self.id} scan_id={self.scan_id}>"