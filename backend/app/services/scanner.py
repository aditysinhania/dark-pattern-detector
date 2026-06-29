import asyncio
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
import validators
import base64
import re
from pathlib import Path
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = structlog.get_logger()


class ScannerError(Exception):
    """Raised when scanning fails — caught by Celery task."""
    pass


class WebScanner:
    """
    Playwright-based web scraper.

    Why Playwright over requests/BeautifulSoup alone?
    Modern websites heavily use JavaScript. A simple HTTP
    request gets you the initial HTML shell — not the rendered
    content. React, Angular, Vue apps render in the browser.
    Playwright actually runs a headless Chromium browser,
    executes JavaScript, waits for content to load, THEN
    lets us read the rendered DOM.

    This is critical for detecting dark patterns because:
    - Fake countdown timers are JavaScript-rendered
    - Cookie consent banners appear after JS loads
    - Popup overlays are JS-triggered
    - Price displays are dynamically inserted
    """

    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_url(url: str) -> str:
        """
        Validate and normalize URLs before scanning.

        Security: without validation, someone could submit
        file:///etc/passwd or internal network addresses.
        We enforce http/https only.
        """
        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if not validators.url(url):
            raise ScannerError(f"Invalid URL: {url}")

        # Block internal/private addresses
        blocked_patterns = [
            r"localhost",
            r"127\.\d+\.\d+\.\d+",
            r"192\.168\.\d+\.\d+",
            r"10\.\d+\.\d+\.\d+",
            r"172\.(1[6-9]|2\d|3[01])\.\d+\.\d+",
            r"0\.0\.0\.0",
        ]
        for pattern in blocked_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                raise ScannerError(
                    "Scanning internal/private addresses is not allowed"
                )

        return url

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def scan(self, url: str, scan_id: str) -> dict:
        """
        Full page scan returning structured data for the AI pipeline.

        The @retry decorator automatically retries on failure —
        networks are unreliable, pages sometimes timeout on first load.
        tenacity handles exponential backoff so we don't hammer servers.
        """
        url = self.validate_url(url)
        logger.info("Starting scan", url=url, scan_id=scan_id)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",  # Required in Docker
                    "--disable-gpu",
                ]
            )

            try:
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    # Ignore HTTPS errors for scanning purposes
                    ignore_https_errors=True,
                )
                page = await context.new_page()

                result = await self._scan_page(page, url, scan_id)
                return result

            except ScannerError as e:
                logger.exception(
                    "ScannerError occurred",
                    error=str(e),
                    url=url,
                    scan_id=scan_id,
                )
                raise

            except Exception as e:
                logger.exception(
                    "Unexpected scanner exception",
                    error=str(e),
                    url=url,
                    scan_id=scan_id,
                )
                raise ScannerError(f"Failed to scan {url}: {str(e)}")

            finally:
                await browser.close()

    async def _scan_page(
        self, page: Page, url: str, scan_id: str
    ) -> dict:
        """
        Core page analysis — extracts everything the AI needs.
        """

        # Navigate with timeout
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            # If networkidle times out, try domcontentloaded
            # Some pages never fully settle (analytics, ads)
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)

        # Wait for any late-loading content
        await asyncio.sleep(2)

        # ── Screenshot ────────────────────────────────────────────────────
        screenshot_path = self.upload_dir / f"screenshot_{scan_id}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)

        # ── Page metadata ─────────────────────────────────────────────────
        title = await page.title()
        current_url = page.url  # May differ from input if redirected

        # ── Full HTML ─────────────────────────────────────────────────────
        html_content = await page.content()

        # ── Parse with BeautifulSoup ──────────────────────────────────────
        soup = BeautifulSoup(html_content, "lxml")

        # ── Extract structured content ────────────────────────────────────
        extracted = await self._extract_content(page, soup)

        logger.info(
            "Scan complete",
            url=url,
            elements_found=len(extracted["buttons"]) + len(extracted["forms"]),
        )

        return {
            "url": current_url,
            "title": title,
            "html": html_content,
            "screenshot_path": str(screenshot_path),
            "text_content": extracted["text_content"],
            "buttons": extracted["buttons"],
            "forms": extracted["forms"],
            "popups": extracted["popups"],
            "timers": extracted["timers"],
            "pricing_elements": extracted["pricing_elements"],
            "consent_elements": extracted["consent_elements"],
            "subscription_elements": extracted["subscription_elements"],
            "checkout_elements": extracted["checkout_elements"],
            "metadata": {
                "original_url": url,
                "final_url": current_url,
                "had_redirect": url != current_url,
            },
        }

    async def _extract_content(self, page: Page, soup: BeautifulSoup) -> dict:
        """
        Extract all elements relevant to dark pattern detection.
        Each extraction targets a specific category of dark patterns.
        """

        # ── Visible text (for NLP analysis) ──────────────────────────────
        # Remove script/style tags first — we want human-readable text
        for tag in soup(["script", "style", "meta", "link"]):
            tag.decompose()
        text_content = " ".join(soup.get_text().split())[:50000]  # Cap at 50k chars

        # ── Buttons (Confirm Shaming, Misdirection) ───────────────────────
        buttons = []
        for btn in soup.find_all(["button", "a", "input"],
                                  attrs={"type": ["button", "submit"]}):
            text = btn.get_text(strip=True)
            if text:
                buttons.append({
                    "text": text,
                    "type": btn.name,
                    "classes": " ".join(btn.get("class", [])),
                    "href": btn.get("href", ""),
                })

        # ── Forms (Sneak into Basket, Hidden Costs) ───────────────────────
        forms = []
        for form in soup.find_all("form"):
            inputs = []
            for inp in form.find_all(["input", "select", "checkbox"]):
                inp_type = inp.get("type", "text")
                # Pre-checked checkboxes are a key dark pattern signal
                is_checked = inp.get("checked") is not None
                inputs.append({
                    "type": inp_type,
                    "name": inp.get("name", ""),
                    "value": inp.get("value", ""),
                    "is_pre_checked": is_checked,
                    "label": self._find_label(soup, inp.get("id", "")),
                })
            forms.append({
                "action": form.get("action", ""),
                "method": form.get("method", "get"),
                "inputs": inputs,
            })

        # ── Countdown timers (Fake Urgency) ───────────────────────────────
        timers = []
        # Look for timer-like elements by common patterns
        timer_selectors = [
            "[class*='countdown']",
            "[class*='timer']",
            "[id*='countdown']",
            "[id*='timer']",
            "[data-countdown]",
            "[data-timer]",
        ]
        for selector in timer_selectors:
            elements = soup.select(selector)
            for el in elements:
                timers.append({
                    "text": el.get_text(strip=True),
                    "html": str(el)[:500],
                    "selector": selector,
                })

        # Also check for JavaScript-based timers
        js_timer_patterns = [
            r"setTimeout",
            r"setInterval",
            r"countdown",
            r"timeLeft",
            r"expires",
        ]
        scripts = soup.find_all("script")
        js_has_timer = any(
            re.search(pat, script.get_text(), re.IGNORECASE)
            for script in scripts
            for pat in js_timer_patterns
        )
        if js_has_timer:
            timers.append({"text": "JavaScript timer detected", "js_based": True})

        # ── Pricing elements (Hidden Costs) ───────────────────────────────
        pricing_elements = []
        price_patterns = soup.find_all(
            string=re.compile(
                r"(\$|€|£|₹|USD|EUR)\s*[\d,]+\.?\d*|free|trial|subscribe",
                re.IGNORECASE
            )
        )
        for el in price_patterns[:20]:  # Cap to avoid huge lists
            parent = el.parent
            if parent:
                pricing_elements.append({
                    "text": el.strip(),
                    "context": parent.get_text(strip=True)[:200],
                    "tag": parent.name,
                })

        # ── Consent banners (Privacy Zuckering) ───────────────────────────
        consent_elements = []
        consent_keywords = [
            "cookie", "consent", "gdpr", "privacy", "accept all",
            "agree", "tracking", "advertising"
        ]
        for el in soup.find_all(["div", "section", "aside", "dialog"]):
            text = el.get_text(strip=True).lower()
            if any(kw in text for kw in consent_keywords) and len(text) > 20:
                consent_elements.append({
                    "text": el.get_text(strip=True)[:500],
                    "tag": el.name,
                    "classes": " ".join(el.get("class", [])),
                })
                if len(consent_elements) >= 5:
                    break

        # ── Subscription elements (Subscription Trap, Forced Continuity) ──
        subscription_elements = []
        sub_keywords = [
            "subscribe", "subscription", "cancel", "membership",
            "auto-renew", "recurring", "billing"
        ]
        for el in soup.find_all(string=re.compile(
            "|".join(sub_keywords), re.IGNORECASE
        )):
            parent = el.parent
            if parent:
                subscription_elements.append({
                    "text": el.strip(),
                    "context": parent.get_text(strip=True)[:300],
                })
                if len(subscription_elements) >= 10:
                    break

        # ── Checkout elements (Sneak into Basket, Hidden Costs) ───────────
        checkout_elements = []
        checkout_keywords = ["checkout", "cart", "basket", "order", "purchase"]
        for el in soup.find_all(
            ["div", "section", "form"],
            class_=lambda c: c and any(kw in " ".join(c).lower()
                                       for kw in checkout_keywords)
        ):
            checkout_elements.append({
                "text": el.get_text(strip=True)[:500],
                "classes": " ".join(el.get("class", [])),
            })
            if len(checkout_elements) >= 5:
                break

        # ── Popup/overlay detection ────────────────────────────────────────
        popups = []
        popup_selectors = [
            "[class*='modal']", "[class*='popup']", "[class*='overlay']",
            "[class*='dialog']", "[role='dialog']", "[aria-modal='true']",
        ]
        for selector in popup_selectors:
            for el in soup.select(selector)[:3]:
                text = el.get_text(strip=True)
                if text:
                    popups.append({
                        "text": text[:300],
                        "selector": selector,
                    })

        return {
            "text_content": text_content,
            "buttons": buttons[:50],        # Cap all lists
            "forms": forms[:10],
            "timers": timers[:10],
            "pricing_elements": pricing_elements,
            "consent_elements": consent_elements,
            "subscription_elements": subscription_elements,
            "checkout_elements": checkout_elements,
            "popups": popups,
        }

    @staticmethod
    def _find_label(soup: BeautifulSoup, element_id: str) -> str:
        """Find the label text associated with a form input by its ID."""
        if not element_id:
            return ""
        label = soup.find("label", attrs={"for": element_id})
        return label.get_text(strip=True) if label else ""