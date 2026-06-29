import structlog
from dataclasses import dataclass, field
from app.db.models.pattern import PatternCategory, DetectionMethod
from app.services.detectors.rule_based import DetectionResult

logger = structlog.get_logger()


class NLPDetector:
    """
    Text-based dark pattern detection using a zero-shot classifier.

    Why zero-shot classification?
    Training a custom classifier requires a labeled dataset of
    thousands of examples per category — which we're building in
    Phase 16. Until then, zero-shot classification from HuggingFace
    gives us strong detection without any training data.

    Model: facebook/bart-large-mnli
    - BART fine-tuned on Multi-Genre Natural Language Inference
    - Zero-shot: you give it labels, it classifies without training
    - Strong at detecting deceptive intent in text

    Alternative: fine-tuned DistilBERT on our custom dataset (Phase 16)
    That will outperform zero-shot but requires labeled data first.

    How zero-shot works:
    For each text chunk, the model asks:
    "Does this text entail the label [fake urgency]?"
    If entailment probability > threshold → pattern detected.

    Limitation: slow for large pages. We run it on extracted
    key elements (buttons, forms, consent text), not the full HTML.
    """

    # Labels the zero-shot model uses for classification
    # These descriptions are carefully worded — better descriptions
    # = better zero-shot accuracy
    CATEGORY_LABELS = {
        PatternCategory.FAKE_URGENCY: (
            "artificial urgency pressure tactics to force immediate purchase"
        ),
        PatternCategory.CONFIRM_SHAMING: (
            "guilt-tripping or shaming language in opt-out or decline options"
        ),
        PatternCategory.HIDDEN_COSTS: (
            "unexpected fees or charges revealed late in checkout process"
        ),
        PatternCategory.SCARCITY_MESSAGES: (
            "false or exaggerated scarcity claims about limited stock or availability"
        ),
        PatternCategory.SUBSCRIPTION_TRAP: (
            "misleading subscription terms with difficult cancellation"
        ),
        PatternCategory.PRIVACY_ZUCKERING: (
            "confusing privacy settings that trick users into sharing more data"
        ),
        PatternCategory.ROACH_MOTEL: (
            "easy to sign up but deliberately difficult to cancel or leave"
        ),
        PatternCategory.MISDIRECTION: (
            "visual design that draws attention away from important information"
        ),
    }

    CONFIDENCE_THRESHOLD = 0.65  # Minimum score to report a detection

    def __init__(self):
        self._classifier = None
        self._model_loaded = False

    def _load_model(self):
        """
        Lazy loading — only import and load the model when first needed.

        Why lazy? The model is ~1.6GB. Loading it at startup would:
        - Slow server startup significantly
        - Use memory even when no scans are running
        - Cause Docker health checks to fail during loading

        The first scan will be slower, but subsequent scans use the
        cached model. In production, you'd warm the model on startup
        with a dummy request during deployment.
        """
        if self._model_loaded:
            return

        try:
            from transformers import pipeline
            logger.info("Loading NLP zero-shot classifier")
            self._classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1,  # -1 = CPU, 0 = first GPU
            )
            self._model_loaded = True
            logger.info("NLP model loaded successfully")
        except Exception as e:
            logger.error("Failed to load NLP model", error=str(e))
            self._classifier = None

    def detect(self, scan_data: dict) -> list[DetectionResult]:
        """
        Run zero-shot classification on key text elements.

        We don't classify the entire page text — that's slow and noisy.
        Instead we classify the high-signal elements:
        - Button text (confirm shaming, misdirection)
        - Consent banner text (privacy zuckering)
        - Subscription text (subscription trap)
        - Pricing context (hidden costs)
        """
        self._load_model()

        if self._classifier is None:
            logger.warning("NLP classifier unavailable, skipping NLP detection")
            return []

        results = []

        # Build targeted text chunks for classification
        text_chunks = self._build_text_chunks(scan_data)

        for chunk_text, chunk_label in text_chunks:
            if not chunk_text or len(chunk_text.strip()) < 20:
                continue

            try:
                detection = self._classify_chunk(chunk_text, chunk_label)
                if detection:
                    results.append(detection)
            except Exception as e:
                logger.error("NLP classification error", error=str(e))
                continue

        return results

    def _build_text_chunks(self, scan_data: dict) -> list[tuple[str, str]]:
        """
        Build (text, label) pairs for targeted classification.
        Label is used for logging/debugging only.
        """
        chunks = []

        # Button text — high signal for confirm shaming
        button_texts = [
            b["text"] for b in scan_data.get("buttons", [])
            if len(b["text"]) > 5
        ]
        if button_texts:
            chunks.append((
                "Button options: " + " | ".join(button_texts[:10]),
                "buttons"
            ))

        # Consent banner text
        for el in scan_data.get("consent_elements", [])[:2]:
            if el.get("text"):
                chunks.append((el["text"][:1000], "consent"))

        # Subscription text
        sub_texts = [
            el.get("text", "") for el in scan_data.get("subscription_elements", [])
        ]
        if sub_texts:
            chunks.append((
                " ".join(sub_texts[:5])[:1000],
                "subscription"
            ))

        # Pricing context
        pricing_texts = [
            el.get("context", "") for el in scan_data.get("pricing_elements", [])
        ]
        if pricing_texts:
            chunks.append((
                " ".join(pricing_texts[:5])[:1000],
                "pricing"
            ))

        # Popup text
        for popup in scan_data.get("popups", [])[:2]:
            if popup.get("text"):
                chunks.append((popup["text"][:500], "popup"))

        return chunks

    def _classify_chunk(
        self, text: str, chunk_label: str
    ) -> DetectionResult | None:
        """
        Run zero-shot classification on one text chunk.
        Returns DetectionResult if any category exceeds threshold.
        """
        candidate_labels = list(self.CATEGORY_LABELS.values())
        category_keys = list(self.CATEGORY_LABELS.keys())

        result = self._classifier(
            text,
            candidate_labels=candidate_labels,
            multi_label=True,  # Multiple patterns can coexist
        )

        # Find highest scoring label above threshold
        best_score = 0.0
        best_category = None

        for label, score in zip(result["labels"], result["scores"]):
            if score > self.CONFIDENCE_THRESHOLD and score > best_score:
                best_score = score
                # Map label back to category
                for cat, cat_label in self.CATEGORY_LABELS.items():
                    if cat_label == label:
                        best_category = cat
                        break

        if best_category is None:
            return None

        return DetectionResult(
            category=best_category,
            confidence=round(best_score, 3),
            explanation=(
                f"NLP classifier detected {best_category.value.replace('_', ' ')} "
                f"with {best_score:.0%} confidence in {chunk_label} text."
            ),
            flagged_text=text[:200],
            suggestion=self._get_suggestion(best_category),
            method=DetectionMethod.NLP,
        )

    @staticmethod
    def _get_suggestion(category: PatternCategory) -> str:
        suggestions = {
            PatternCategory.FAKE_URGENCY: (
                "Remove time pressure language unless the deadline is genuine "
                "and clearly explained."
            ),
            PatternCategory.CONFIRM_SHAMING: (
                "Use neutral, non-judgmental language for all decline options."
            ),
            PatternCategory.HIDDEN_COSTS: (
                "Display all fees and taxes on the first pricing screen."
            ),
            PatternCategory.SUBSCRIPTION_TRAP: (
                "Make cancellation as simple as signup. Provide clear renewal notices."
            ),
            PatternCategory.PRIVACY_ZUCKERING: (
                "Use separate, clearly labeled consent for each data use case."
            ),
            PatternCategory.ROACH_MOTEL: (
                "Provide a self-service cancellation link in the account dashboard."
            ),
            PatternCategory.SCARCITY_MESSAGES: (
                "Only show verified, real-time stock information."
            ),
            PatternCategory.MISDIRECTION: (
                "Ensure visual hierarchy highlights important information, "
                "not just desired actions."
            ),
        }
        return suggestions.get(category, "Review and revise this element.")