from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import uuid

from app.db.models.scan import Scan, ScanStatus, RiskLevel
from app.db.models.pattern import DetectedPattern
from app.db.models.report import Report
from app.repositories.scan import ScanRepository
from app.repositories.pattern import PatternRepository
from app.services.ai_pipeline import PipelineResult
from app.services.detectors.rule_based import DetectionResult

logger = structlog.get_logger()


class ReportService:
    """
    Builds and persists scan reports.
    Called by the Celery task after the AI pipeline completes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scan_repo = ScanRepository(db)
        self.pattern_repo = PatternRepository(db)

    async def build_and_save(
        self,
        scan: Scan,
        pipeline_result: PipelineResult,
        scanner_data: dict,
    ) -> Report:
        """
        Persist all pipeline results to the database.

        Transaction boundary: all-or-nothing.
        If saving patterns fails, the scan status stays PROCESSING
        and the Celery task will retry.
        """
        # Save individual detected patterns
        pattern_records = []
        for detection in pipeline_result.detections:
            pattern = DetectedPattern(
                scan_id=scan.id,
                category=detection.category,
                detection_method=detection.method,
                confidence_score=detection.confidence,
                explanation=detection.explanation,
                flagged_text=detection.flagged_text,
                element_selector=detection.element_selector or "",
                bounding_box=detection.metadata,
                suggestion=detection.suggestion,
            )
            pattern_records.append(pattern)

        if pattern_records:
            await self.pattern_repo.bulk_create(pattern_records)

        # Map string risk level to enum
        risk_level_map = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }

        # Update scan record with results
        scan.status = ScanStatus.COMPLETED
        scan.risk_score = pipeline_result.risk_score
        scan.risk_level = risk_level_map[pipeline_result.risk_level]
        scan.patterns_found = pipeline_result.patterns_found
        scan.page_title = scanner_data.get("title", "")
        scan.screenshot_path = scanner_data.get("screenshot_path")
        scan.scan_metadata = scanner_data.get("metadata", {})
        await self.scan_repo.update(scan)

        # Build structured report JSON
        report_data = self._build_report_json(
            scan, pipeline_result, scanner_data
        )

        # Create report record
        report = Report(
            scan_id=scan.id,
            total_patterns=pipeline_result.patterns_found,
            risk_score=pipeline_result.risk_score,
            summary=self._generate_summary(pipeline_result),
            report_data=report_data,
        )
        self.db.add(report)
        await self.db.flush()

        logger.info(
            "Report saved",
            scan_id=str(scan.id),
            patterns=pipeline_result.patterns_found,
            risk_score=pipeline_result.risk_score,
        )

        return report

    def _build_report_json(
        self,
        scan: Scan,
        result: PipelineResult,
        scanner_data: dict,
    ) -> dict:
        """
        Build the complete structured report.
        This JSON is what the frontend renders and what PDFs are built from.
        """
        return {
            "scan_id": str(scan.id),
            "url": scan.url,
            "scanned_at": scan.created_at.isoformat(),
            "page_title": scanner_data.get("title", ""),
            "risk_score": result.risk_score,
            "risk_level": result.risk_level,
            "patterns_found": result.patterns_found,
            "detection_summary": result.detection_summary,
            "detections": [
                {
                    "category": d.category.value,
                    "confidence": d.confidence,
                    "method": d.method.value,
                    "explanation": d.explanation,
                    "flagged_text": d.flagged_text,
                    "suggestion": d.suggestion,
                }
                for d in result.detections
            ],
            "recommendations": self._generate_recommendations(result),
            "metadata": scanner_data.get("metadata", {}),
        }

    @staticmethod
    def _generate_summary(result: PipelineResult) -> str:
        if result.patterns_found == 0:
            return "No dark patterns detected. This website appears to follow ethical UX practices."

        level = result.risk_level.upper()
        patterns = ", ".join(
            d.category.value.replace("_", " ").title()
            for d in result.detections[:3]
        )
        return (
            f"{level} risk: {result.patterns_found} dark pattern(s) detected. "
            f"Key issues include {patterns}."
        )

    @staticmethod
    def _generate_recommendations(result: PipelineResult) -> list[dict]:
        """
        Top-level recommendations based on detected patterns.
        Ordered by confidence (most certain issues first).
        """
        return [
            {
                "priority": i + 1,
                "pattern": d.category.value,
                "action": d.suggestion,
                "confidence": d.confidence,
            }
            for i, d in enumerate(result.detections[:5])
        ]