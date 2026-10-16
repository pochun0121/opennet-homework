"""Handle modals / pop-ups that Twitch shows at random (mature content gate, cookie consent, app promo, ...).

Supporting a new pop-up only needs one more Locator in DISMISS_LOCATORS; no page or test changes.
"""
from __future__ import annotations

import logging

from src.pages.locators import Locator
from src.pages.web_object import WebObject

logger = logging.getLogger(__name__)

_UPPER, _LOWER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"

# Button texts (lower case) that accept / dismiss a consent or promo overlay
ACCEPT_TEXTS = (
    "accept all", "accept all cookies", "accept cookies", "accept", "i accept",
    "agree", "i agree", "allow all", "ok", "got it",
    "proceed",  # Twitch "Cookies and Advertising Choices" banner (its other button, "Cookies & Ads Choices", opens settings)
)


def _lower_text_in(texts: tuple[str, ...]) -> str:
    return " or ".join(f"translate(normalize-space(.), '{_UPPER}', '{_LOWER}')='{t}'" for t in texts)


# Finds what covers `target`, then looks for an accept-like button in the smallest ancestor that has one.
# Returns [button | null, description-of-the-blocker] or null when nothing covers the target.
FIND_BLOCKER_JS = """
const target = arguments[0], texts = arguments[1];
const r = target.getBoundingClientRect();
const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
if (!hit || hit === target || target.contains(hit)) return null;
const norm = s => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
let node = hit;
for (let i = 0; i < 8 && node && node !== document.body; i++, node = node.parentElement) {
  for (const c of node.querySelectorAll('button, a, [role="button"]')) {
    if (texts.includes(norm(c.innerText || c.textContent))) {
      return [c, norm(node.innerText).slice(0, 200)];
    }
  }
}
return [null, hit.outerHTML.slice(0, 300)];
"""

DISMISS_LOCATORS: tuple[Locator, ...] = (
    # Mobile web "open in app" bottom sheet (text depends on browser language)
    Locator.xpath(
        "continue_on_web",
        "//*[self::a or self::button][.//*[normalize-space()='Continue on web' or normalize-space()='Continue using web' or normalize-space()='Keep using web' or normalize-space()='繼續使用網頁版']"
        " or normalize-space()='Keep using web' or normalize-space()='繼續使用網頁版']",
    ),
    Locator.css("mature_content_start_watching", "button[data-a-target='content-classification-gate-overlay-start-watching-button']"),
    Locator.xpath("start_watching_text", "//button[.//div[normalize-space()='Start Watching'] or normalize-space()='Start Watching']"),
    Locator.css("cookie_accept", "button[data-a-target='consent-banner-accept']"),
    # Seen on CI runners: purple bottom banner "Cookies and Advertising Choices" with [Cookies & Ads Choices] [Proceed]
    Locator.xpath("cookie_proceed", "//button[normalize-space()='Proceed']"),
    # Consent / cookie banners whose markup we do not know: accept-like button inside a dialog or consent container
    Locator.xpath(
        "cookie_accept_text",
        "//*[@role='dialog' or contains(@data-a-target,'consent') or contains(@id,'cookie') or contains(@id,'consent')]"
        f"//button[{_lower_text_in(ACCEPT_TEXTS)}]",
    ),
    Locator.xpath("generic_not_now", "//button[normalize-space()='Not now' or normalize-space()='Not Now' or normalize-space()='Close']"),
    Locator.css("dialog_close", "[role='dialog'] button[aria-label='Close']"),
)


class ModalHandler(WebObject):
    def __init__(self, *args, locators: tuple[Locator, ...] = DISMISS_LOCATORS, probe_timeout: float = 1.5, **kwargs):
        super().__init__(*args, **kwargs)
        self.locators = locators
        self.probe_timeout = probe_timeout

    def dismiss_all(self, max_rounds: int = 3) -> int:
        """Repeatedly dismiss every detected pop-up (some appear in sequence); return how many were closed."""
        dismissed = 0
        for _ in range(max_rounds):
            closed_this_round = 0
            for locator in self.locators:
                if self.is_present(locator, timeout=self.probe_timeout):
                    logger.info("dismiss modal via %s", locator)
                    self.click(locator)
                    closed_this_round += 1
            dismissed += closed_this_round
            if not closed_this_round:
                break
        return dismissed

    def dismiss_blocker_of(self, locator: Locator) -> bool:
        """Something covers `locator` (click intercepted): find the overlay and click its accept-like button.

        Works without knowing the overlay's markup. When nothing suitable is found, the blocker's content is logged
        so the CI log shows exactly what to add to DISMISS_LOCATORS. Returns True if a button was clicked.
        """
        target = self.find(locator)
        result = self.driver.execute_script(FIND_BLOCKER_JS, target, list(ACCEPT_TEXTS))
        if not result:
            return False
        button, info = result
        if button is None:
            logger.warning("%s is covered by an unrecognised overlay: %s", locator, info)
            return False
        logger.warning("%s is covered by an overlay (%s); clicking its accept button", locator, info)
        self.click_element(button)
        self._sleep(0.5)
        return True
