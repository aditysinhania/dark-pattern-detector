from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, ForeignKey, Enum as SAEnum, Text, JSON
import enum
import uuid

from app.db.base import Base, TimestampMixin


class PatternCategory(str, enum.Enum):
    """
    The 13 dark pattern categories we detect.
    Each maps to a specific detection strategy in the AI pipeline.
    """
    CONFIRM_SHAMING = "confirm_shaming"
    FORCED_CONTINUITY = "forced_continuity"
    HIDDEN_COSTS = "hidden_costs"
    FAKE_URGENCY = "fake_urgency"
    FAKE_COUNTDOWN = "fake_countdown"
    SCARCITY_MESSAGES = "scarcity_messages"
    SNEAK_INTO_BASKET = "sneak_into_basket"
    PRIVACY_ZUCKERING = "privacy_zuckering"
    ROACH_MOTEL = "roach_motel"
    INTERFACE_INTERFERENCE = "interface_interference"
    OBSTRUCTION = "obstruction"
    MISDIRECTION = "misdirection"
    SUBSCRIPTION_TRAP = "subscription_trap"


class DetectionMethod(str, enum.Enum):
    """
    Which part of the AI pipeline detected this pattern.
    Critical for explainability — users can see HOW it was detected.
    Also lets us evaluate which detection methods perform best.
    """
    RULE_BASED = "rule_based"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"
    ML_CLASSIFIER = "ml_classifier"
    LLM = "llm"
    ENSEMBLE = "ensemble"


class DetectedPattern(Base, TimestampMixin):
    """
    One detected dark pattern instance within a scan.

    A single scan can detect many patterns. Each pattern
    stores exactly what was found, where, how confident
    the AI is, and a human-readable explanation.

    This granular storage lets us:
    - Show users exactly which element is problematic
    - Build training data from confirmed detections
    - Track pattern frequency across websites
    """
    __tablename__ = "detected_patterns"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[PatternCategory] = mapped_column(
        SAEnum(PatternCategory),
        nullable=False,
        index=True,
    )
    detection_method: Mapped[DetectionMethod] = mapped_column(
        SAEnum(DetectionMethod),
        nullable=False,
    )

    # Confidence score from the AI model (0.0 - 1.0)
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Human-readable explanation of WHY this was flagged
    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # The actual text content that was flagged (e.g. "Only 2 left!")
    flagged_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # CSS selector or XPath to the element in the DOM
    element_selector: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Bounding box coordinates for screenshot highlighting
    # Stored as JSON: {"x": 100, "y": 200, "width": 300, "height": 50}
    bounding_box: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Suggestion for how the website could fix this
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extra data specific to the detection method
    # e.g. NLP stores token attention weights, CV stores heatmap path
    pattern_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationship
    scan: Mapped["Scan"] = relationship("Scan", back_populates="detected_patterns")

    def __repr__(self) -> str:
        return (
            f"<DetectedPattern "
            f"category={self.category} "
            f"confidence={self.confidence_score:.2f}>"
        )