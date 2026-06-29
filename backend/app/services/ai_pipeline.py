import asyncio
import structlog
from dataclasses import dataclass
from app.db.models.pattern import PatternCategory, DetectionMethod
from app.services.detectors.rule_based import RuleBasedDetector, DetectionResult
from app.services.detectors.nlp_detector import NLPDetector
from app.services.detectors.cv_detector import CVDetector

logger = structlog.get_logger()


@dataclass
class PipelineResult:
    """
    Final output of the complete AI pipeline for one scan.
    """
    detections: list[DetectionResult]
    risk_score: float
    risk_level: str
    patterns_found: int
    detection_summary: dict


class AIPipeline:
    """
    Orchestrates all detection methods and combines results.

    Pipeline architecture:
    1. Rule-based runs first (fast, high precision)
    2. NLP runs on text elements (context-aware)
    3. CV runs on screenshot (visual patterns)
    4. Ensemble deduplicates and weights results

    Why run all three?
    - Rule-based: catches obvious patterns fast
    - NLP: catches subtle language manipulation
    - CV: catches visual tricks invisible to text analysis
    - Together: much higher recall than any single method

    Ensemble strategy:
    - If multiple methods detect the SAME category, boost confidence
    - If only one method detects it, use that confidence as-is
    - Deduplication: one result per category (highest confidence wins)

    This is similar to how ensemble models work in ML —
    combining weak learners into a stronger predictor.
    """

    def __init__(self):
        self.rule_detector = RuleBasedDetector()
        self.nlp_detector = NLPDetector()
        self.cv_detector = CVDetector()

    async def run(self, scan_data: dict) -> PipelineResult:
        """
        Run the full detection pipeline.
        NLP and CV run concurrently to minimize total latency.
        """
        logger.info("Starting AI pipeline", url=scan_data.get("url"))

        # Rule-based is synchronous and fast — run first
        rule_results = self.rule_detector.detect(scan_data)
        logger.info("Rule-based detection complete",
                    found=len(rule_results))

        # NLP and CV are independent — run them concurrently
        # asyncio.gather runs both in the event loop concurrently
        # Total time = max(nlp_time, cv_time) instead of nlp_time + cv_time
        nlp_results, cv_results = await asyncio.gather(
            asyncio.get_event_loop().run_in_executor(
                None, self.nlp_detector.detect, scan_data
            ),
            asyncio.get_event_loop().run_in_executor(
                None, self.cv_detector.detect, scan_data
            ),
        )

        logger.info("NLP detection complete", found=len(nlp_results))
        logger.info("CV detection complete", found=len(cv_results))

        # Combine and deduplicate results
        all_results = rule_results + nlp_results + cv_results
        final_detections = self._ensemble(all_results)

        # Calculate risk score
        risk_score = self._calculate_risk_score(final_detections)
        risk_level = self._risk_level(risk_score)

        # Build summary by category
        detection_summary = {}
        for det in final_detections:
            detection_summary[det.category.value] = {
                "confidence": det.confidence,
                "method": det.method.value,
            }

        logger.info(
            "AI pipeline complete",
            patterns_found=len(final_detections),
            risk_score=risk_score,
            risk_level=risk_level,
        )

        return PipelineResult(
            detections=final_detections,
            risk_score=risk_score,
            risk_level=risk_level,
            patterns_found=len(final_detections),
            detection_summary=detection_summary,
        )

    def _ensemble(
        self, results: list[DetectionResult]
    ) -> list[DetectionResult]:
        """
        Deduplicate results and boost confidence when multiple
        methods agree on the same category.

        Ensemble logic:
        - Group detections by category
        - If 1 method detected it: keep original confidence
        - If 2 methods detected it: boost by 10%
        - If 3 methods detected it: boost by 20%, mark as ENSEMBLE
        - Always keep the result with highest confidence as base
        """
        if not results:
            return []

        # Group by category
        by_category: dict[PatternCategory, list[DetectionResult]] = {}
        for result in results:
            if result.category not in by_category:
                by_category[result.category] = []
            by_category[result.category].append(result)

        final = []
        for category, detections in by_category.items():
            # Sort by confidence, keep the best one
            detections.sort(key=lambda d: d.confidence, reverse=True)
            best = detections[0]

            # Boost confidence based on agreement
            n_methods = len(set(d.method for d in detections))
            if n_methods == 2:
                best.confidence = min(best.confidence + 0.10, 0.99)
            elif n_methods >= 3:
                best.confidence = min(best.confidence + 0.20, 0.99)
                best.method = DetectionMethod.ENSEMBLE

            final.append(best)

        # Sort final results by confidence descending
        final.sort(key=lambda d: d.confidence, reverse=True)
        return final

    @staticmethod
    def _calculate_risk_score(detections: list[DetectionResult]) -> float:
        """
        Compute overall risk score from individual detections.

        Formula: weighted average of detection confidences,
        with diminishing returns for additional patterns.
        A site with 1 pattern at 0.95 should score lower than
        a site with 8 patterns each at 0.80.

        Score range: 0.0 (no patterns) to 1.0 (extremely deceptive)
        """
        if not detections:
            return 0.0

        # Base score: average confidence of all detections
        avg_confidence = sum(d.confidence for d in detections) / len(detections)

        # Volume multiplier: more patterns = higher risk
        # log scale to prevent runaway scores
        import math
        volume_multiplier = min(1.0 + math.log(len(detections) + 1) * 0.2, 1.8)

        raw_score = avg_confidence * volume_multiplier
        return round(min(raw_score, 1.0), 3)

    @staticmethod
    def _risk_level(score: float) -> str:
        if score < 0.3:
            return "low"
        elif score < 0.6:
            return "medium"
        elif score < 0.8:
            return "high"
        else:
            return "critical"