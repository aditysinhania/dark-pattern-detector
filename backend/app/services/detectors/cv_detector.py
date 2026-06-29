import structlog
from pathlib import Path
from app.db.models.pattern import PatternCategory, DetectionMethod
from app.services.detectors.rule_based import DetectionResult

logger = structlog.get_logger()


class CVDetector:
    """
    Computer vision based dark pattern detection.

    What CV detects that text analysis can't:
    - Tiny grey "close" buttons on cookie banners
    - Confusing visual layouts (misdirection)
    - Important text in light grey on white (interface interference)
    - Deceptive button sizing (accept = large, reject = tiny)
    - Hidden unsubscribe links in small print

    Current implementation: rule-based CV using color analysis
    and element size comparison. This is the Phase 1 baseline.

    Phase 17 (model fine-tuning) will replace this with a
    fine-tuned ViT (Vision Transformer) or YOLO model trained
    on labeled screenshots of dark patterns.

    Why not start with ViT? We need labeled training data first.
    The rule-based CV gives us detections now that we can use
    as training signal for the ML model later.
    """

    def detect(self, scan_data: dict) -> list[DetectionResult]:
        """
        Analyze the screenshot for visual dark patterns.
        Returns DetectionResult list — same interface as other detectors.
        """
        screenshot_path = scan_data.get("screenshot_path")
        if not screenshot_path or not Path(screenshot_path).exists():
            logger.warning("No screenshot available for CV analysis")
            return []

        results = []

        try:
            import cv2
            import numpy as np
            from PIL import Image

            img = cv2.imread(screenshot_path)
            if img is None:
                return []

            pil_img = Image.open(screenshot_path)

            # Run each CV check
            results.extend(self._check_consent_button_asymmetry(img))
            results.extend(self._check_low_contrast_text(img))
            results.extend(self._check_popup_overlay(img))

        except ImportError:
            logger.warning("OpenCV not available, skipping CV detection")
        except Exception as e:
            logger.error("CV detection error", error=str(e))

        return results

    def _check_consent_button_asymmetry(
        self, img
    ) -> list[DetectionResult]:
        """
        Detects when "Accept" buttons are visually much larger or more
        prominent than "Reject" buttons on cookie consent banners.

        Method: Find button-like rectangles in the bottom third of the
        page (where consent banners typically appear). Compare sizes.
        If the largest button is >3x the area of the smallest, flag it.
        """
        import cv2
        import numpy as np

        results = []
        height, width = img.shape[:2]

        # Focus on bottom third (most consent banners are here)
        bottom_region = img[int(height * 0.6):, :]

        # Convert to grayscale and find edges
        gray = cv2.cvtColor(bottom_region, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Find contours (button outlines)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter to button-sized rectangles
        button_areas = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            aspect_ratio = w / h if h > 0 else 0
            # Typical button: wider than tall, reasonable size
            if (20 < w < 400 and 10 < h < 80 and
                    1.5 < aspect_ratio < 10 and area > 500):
                button_areas.append(area)

        if len(button_areas) >= 2:
            max_area = max(button_areas)
            min_area = min(button_areas)
            ratio = max_area / min_area if min_area > 0 else 1

            if ratio > 3.0:
                results.append(DetectionResult(
                    category=PatternCategory.INTERFACE_INTERFERENCE,
                    confidence=round(min(0.60 + (ratio - 3) * 0.05, 0.85), 2),
                    explanation=(
                        f"Consent buttons have asymmetric sizing (ratio: {ratio:.1f}x). "
                        "The accept button appears significantly larger than decline."
                    ),
                    flagged_text="Visual button size asymmetry in consent area",
                    suggestion=(
                        "Make accept and decline buttons the same size and visual weight."
                    ),
                    method=DetectionMethod.COMPUTER_VISION,
                ))

        return results

    def _check_low_contrast_text(self, img) -> list[DetectionResult]:
        """
        Detects text rendered in very low contrast (e.g. light grey on white).
        This is used to hide important information like cancellation terms.

        Method: Convert to LAB color space, find regions where
        text contrast (L channel difference) is very low.
        """
        import cv2
        import numpy as np

        results = []

        # Convert to LAB color space for perceptual contrast analysis
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]

        # Find very bright areas (white/near-white backgrounds)
        bright_mask = l_channel > 230

        # In bright areas, look for slightly-less-bright text
        # Low contrast text: L value between 200-229 in a 230+ background
        low_contrast_text = (l_channel > 200) & (l_channel < 230) & bright_mask

        low_contrast_ratio = low_contrast_text.sum() / bright_mask.sum() \
            if bright_mask.sum() > 0 else 0

        if low_contrast_ratio > 0.02:  # >2% of bright area has low contrast
            results.append(DetectionResult(
                category=PatternCategory.OBSTRUCTION,
                confidence=0.65,
                explanation=(
                    "Low contrast text detected. Important information may be "
                    "rendered in light grey to make it difficult to read."
                ),
                flagged_text="Low contrast text regions detected in screenshot",
                suggestion=(
                    "Ensure all text meets WCAG AA contrast ratio of at least 4.5:1. "
                    "Important terms must be as visible as promotional content."
                ),
                method=DetectionMethod.COMPUTER_VISION,
            ))

        return results

    def _check_popup_overlay(self, img) -> list[DetectionResult]:
        """
        Detects modal overlays that may be used to obstruct navigation
        or force interaction (e.g. forced email signup popups).
        """
        import cv2
        import numpy as np

        results = []
        height, width = img.shape[:2]

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Dark overlays darken the background
        # If a large portion of the image is semi-dark,
        # there's likely a modal overlay
        dark_pixel_ratio = (gray < 100).sum() / (height * width)

        if dark_pixel_ratio > 0.3:
            results.append(DetectionResult(
                category=PatternCategory.OBSTRUCTION,
                confidence=0.70,
                explanation=(
                    "Modal overlay detected covering significant page area. "
                    "Forced overlays obstruct access to content without consent."
                ),
                flagged_text="Dark overlay detected in screenshot",
                suggestion=(
                    "Do not use overlays that block page content without user "
                    "initiation. Ensure overlays can be easily dismissed."
                ),
                method=DetectionMethod.COMPUTER_VISION,
            ))

        return results