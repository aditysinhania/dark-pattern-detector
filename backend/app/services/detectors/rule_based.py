import re
from dataclasses import dataclass
from app.db.models.pattern import PatternCategory, DetectionMethod


@dataclass
class DetectionResult:
    """
    A single detected pattern from any detector.
    All detectors return this same shape —
    the ensemble can combine them uniformly.
    """
    category: PatternCategory
    confidence: float
    explanation: str
    flagged_text: str
    suggestion: str
    method: DetectionMethod = DetectionMethod.RULE_BASED
    element_selector: str = ""
    metadata: dict = None


class RuleBasedDetector:
    """
    Pattern detection using regex rules and keyword matching.

    Why rule-based as the first layer?
    1. Zero latency — no model loading
    2. 100% explainable — you can show the exact rule that fired
    3. High precision for obvious patterns
    4. Provides signal to the ensemble even when ML model is uncertain
    5. Easy to add new rules as patterns evolve

    Limitation: can't detect novel patterns or context-dependent
    deception. That's what the NLP and CV layers handle.

    Think of rule-based as the "obvious cases" detector.
    If a page says "Only 2 left!" it's almost certainly fake scarcity.
    No ML needed for that.
    """

    # ── Urgency patterns ──────────────────────────────────────────────────
    URGENCY_PATTERNS = [
        r"limited time (offer|deal|only)",
        r"offer expires? (in|at|soon)",
        r"(sale|deal) ends? (in|at|tonight|soon|today)",
        r"hurry[,!]?\s*(up)?",
        r"act now",
        r"don'?t miss (out|this)",
        r"time is running out",
        r"last chance",
        r"(today|tonight) only",
        r"expires? (today|tonight|soon|in \d+)",
        r"flash sale",
    ]

    # ── Scarcity patterns ─────────────────────────────────────────────────
    SCARCITY_PATTERNS = [
        r"only \d+ left (in stock)?",
        r"\d+ (people|others|customers) (are )?(viewing|watching|looking)",
        r"(almost|nearly) (sold out|gone)",
        r"selling (fast|quickly)",
        r"(high|popular|strong) demand",
        r"limited (stock|availability|quantity|supply)",
        r"just \d+ remaining",
        r"low stock",
        r"(\d+)% (claimed|sold|gone|taken)",
    ]

    # ── Confirm shaming patterns ───────────────────────────────────────────
    CONFIRM_SHAMING_PATTERNS = [
        r"no[,]? (thanks?|thank you)[,.]?\s*i (don'?t|do not) want",
        r"i'?m (ok|okay|fine) (with|being|staying) (paying|without|poor|fat|unhealthy)",
        r"no[,]? i (prefer|like|want|love) (paying|wasting|being)",
        r"i don'?t want to save",
        r"i hate (saving|discounts|deals|money)",
        r"decline and (remain|stay|keep)",
        r"no thanks[,]? i (already have|don'?t need|prefer)",
    ]

    # ── Forced continuity / subscription trap patterns ────────────────────
    SUBSCRIPTION_PATTERNS = [
        r"free (trial|period).{0,50}(then|after).{0,30}\$[\d.]+",
        r"cancel (anytime|any time)",
        r"auto.?renew",
        r"recurring (charge|billing|payment)",
        r"will be charged.{0,50}after (trial|period)",
        r"(subscription|membership).{0,50}(continues?|renews?|auto)",
        r"charged.{0,50}unless (you cancel|cancelled)",
    ]

    # ── Hidden costs patterns ─────────────────────────────────────────────
    HIDDEN_COST_PATTERNS = [
        r"processing fee",
        r"service (charge|fee)",
        r"\+ (tax|fees?|shipping)",
        r"additional (charges?|fees?|costs?)",
        r"taxes? (and|&) fees?",
        r"handling (fee|charge)",
        r"convenience fee",
        r"booking fee",
    ]

    # ── Privacy Zuckering patterns ─────────────────────────────────────────
    PRIVACY_PATTERNS = [
        r"(share|sell).{0,30}(data|information).{0,30}(partner|third.party|advertis)",
        r"(partner|third.party|advertis).{0,30}(access|receive|use)",
        r"personali[sz]ed (ads?|advertising|content)",
        r"targeted (ads?|advertising)",
        r"by (clicking|continuing|using).{0,50}(agree|accept|consent)",
        r"opt.?out.{0,50}(data|sharing|marketing)",
    ]

    # ── Roach motel patterns ───────────────────────────────────────────────
    ROACH_MOTEL_PATTERNS = [
        r"(call|phone|contact).{0,30}(cancel|unsubscribe)",
        r"to cancel.{0,50}(call|email|contact|visit|write)",
        r"cancel (by|via) (phone|mail|post|letter)",
        r"cancellation (request|form|process)",
        r"(difficult|hard|complicated).{0,30}cancel",
    ]

    def detect(self, scan_data: dict) -> list[DetectionResult]:
        """
        Run all rule-based detectors against the extracted content.
        Returns a list of DetectionResult objects.
        """
        results = []
        text = scan_data.get("text_content", "").lower()
        buttons = scan_data.get("buttons", [])
        forms = scan_data.get("forms", [])
        subscription_elements = scan_data.get("subscription_elements", [])
        consent_elements = scan_data.get("consent_elements", [])
        pricing_elements = scan_data.get("pricing_elements", [])
        timers = scan_data.get("timers", [])

        # ── Check fake urgency ────────────────────────────────────────────
        urgency_match = self._find_pattern_match(text, self.URGENCY_PATTERNS)
        if urgency_match:
            results.append(DetectionResult(
                category=PatternCategory.FAKE_URGENCY,
                confidence=0.85,
                explanation=(
                    f"Page contains urgency language designed to pressure "
                    f"users into quick decisions: '{urgency_match}'"
                ),
                flagged_text=urgency_match,
                suggestion=(
                    "Remove artificial urgency language. If there is a genuine "
                    "deadline, state it clearly with the exact date and reason."
                ),
            ))

        # ── Check fake countdown timers ───────────────────────────────────
        if timers:
            results.append(DetectionResult(
                category=PatternCategory.FAKE_COUNTDOWN,
                confidence=0.80,
                explanation=(
                    "Countdown timer detected. These are frequently reset or "
                    "fake, creating artificial urgency."
                ),
                flagged_text=timers[0].get("text", "Timer detected"),
                suggestion=(
                    "Remove countdown timers unless the deadline is genuinely "
                    "fixed and the timer accurately reflects remaining time."
                ),
            ))

        # ── Check scarcity messages ───────────────────────────────────────
        scarcity_match = self._find_pattern_match(text, self.SCARCITY_PATTERNS)
        if scarcity_match:
            results.append(DetectionResult(
                category=PatternCategory.SCARCITY_MESSAGES,
                confidence=0.82,
                explanation=(
                    f"False or unverifiable scarcity claim: '{scarcity_match}'. "
                    "These claims are often fabricated or dynamically inflated."
                ),
                flagged_text=scarcity_match,
                suggestion=(
                    "Only display stock counts if they are accurate and verified "
                    "in real time. Remove social proof counters if not genuine."
                ),
            ))

        # ── Check confirm shaming ─────────────────────────────────────────
        all_button_text = " ".join(b["text"] for b in buttons).lower()
        shame_match = self._find_pattern_match(
            all_button_text, self.CONFIRM_SHAMING_PATTERNS
        )
        if shame_match:
            results.append(DetectionResult(
                category=PatternCategory.CONFIRM_SHAMING,
                confidence=0.90,
                explanation=(
                    f"Decline option uses shame/guilt language: '{shame_match}'. "
                    "This manipulates users into accepting by making refusal feel negative."
                ),
                flagged_text=shame_match,
                suggestion=(
                    "Replace guilt-tripping decline text with neutral language "
                    "like 'No thanks' or 'Maybe later'."
                ),
            ))

        # ── Check subscription traps ──────────────────────────────────────
        sub_text = " ".join(
            el.get("text", "") for el in subscription_elements
        ).lower()
        sub_match = self._find_pattern_match(
            text + " " + sub_text, self.SUBSCRIPTION_PATTERNS
        )
        if sub_match:
            results.append(DetectionResult(
                category=PatternCategory.SUBSCRIPTION_TRAP,
                confidence=0.85,
                explanation=(
                    f"Subscription terms that may trap users: '{sub_match}'. "
                    "Auto-renewal without prominent disclosure is deceptive."
                ),
                flagged_text=sub_match,
                suggestion=(
                    "Display subscription costs, renewal terms, and cancellation "
                    "process prominently before purchase, not in fine print."
                ),
            ))

        # ── Check hidden costs ────────────────────────────────────────────
        pricing_text = " ".join(
            el.get("text", "") for el in pricing_elements
        ).lower()
        cost_match = self._find_pattern_match(
            text + " " + pricing_text, self.HIDDEN_COST_PATTERNS
        )
        if cost_match:
            results.append(DetectionResult(
                category=PatternCategory.HIDDEN_COSTS,
                confidence=0.78,
                explanation=(
                    f"Additional fees found that may not be shown upfront: "
                    f"'{cost_match}'"
                ),
                flagged_text=cost_match,
                suggestion=(
                    "Show total cost including all fees before the final checkout step."
                ),
            ))

        # ── Check privacy zuckering ───────────────────────────────────────
        consent_text = " ".join(
            el.get("text", "") for el in consent_elements
        ).lower()
        privacy_match = self._find_pattern_match(
            text + " " + consent_text, self.PRIVACY_PATTERNS
        )
        if privacy_match:
            results.append(DetectionResult(
                category=PatternCategory.PRIVACY_ZUCKERING,
                confidence=0.80,
                explanation=(
                    f"Consent mechanism may not be transparent: '{privacy_match}'. "
                    "Users may be agreeing to data sharing without realizing it."
                ),
                flagged_text=privacy_match,
                suggestion=(
                    "Use explicit opt-in checkboxes for data sharing. "
                    "Do not bundle consent with terms of service acceptance."
                ),
            ))

        # ── Check roach motel ─────────────────────────────────────────────
        roach_match = self._find_pattern_match(text, self.ROACH_MOTEL_PATTERNS)
        if roach_match:
            results.append(DetectionResult(
                category=PatternCategory.ROACH_MOTEL,
                confidence=0.83,
                explanation=(
                    f"Cancellation appears deliberately difficult: '{roach_match}'. "
                    "Easy signup but hard cancellation is a classic dark pattern."
                ),
                flagged_text=roach_match,
                suggestion=(
                    "Provide a simple, self-service online cancellation option "
                    "that is as easy to find as the signup flow."
                ),
            ))

        # ── Check sneak into basket (pre-checked forms) ───────────────────
        for form in forms:
            for inp in form.get("inputs", []):
                if inp.get("is_pre_checked") and inp.get("type") in [
                    "checkbox", "radio"
                ]:
                    label = inp.get("label", inp.get("name", "unknown option"))
                    results.append(DetectionResult(
                        category=PatternCategory.SNEAK_INTO_BASKET,
                        confidence=0.88,
                        explanation=(
                            f"Pre-checked option found: '{label}'. Users may "
                            "unknowingly accept additional items or services."
                        ),
                        flagged_text=f"Pre-checked: {label}",
                        suggestion=(
                            "Never pre-check optional items. All optional "
                            "add-ons must require explicit user action to select."
                        ),
                    ))

        return results

    @staticmethod
    def _find_pattern_match(text: str, patterns: list[str]) -> str | None:
        """
        Check text against a list of regex patterns.
        Returns the matched text if found, None otherwise.
        """
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                return text[start:end].strip()
        return None