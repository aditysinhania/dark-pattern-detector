# Import all models here.
# This ensures SQLAlchemy's metadata knows about every table
# when Alembic runs autogenerate. If you forget to import a model
# here, Alembic won't see it and won't generate its migration.

from app.db.models.user import User, UserRole
from app.db.models.scan import Scan, ScanStatus, RiskLevel
from app.db.models.pattern import DetectedPattern, PatternCategory, DetectionMethod
from app.db.models.report import Report

__all__ = [
    "User",
    "UserRole",
    "Scan",
    "ScanStatus",
    "RiskLevel",
    "DetectedPattern",
    "PatternCategory",
    "DetectionMethod",
    "Report",
]