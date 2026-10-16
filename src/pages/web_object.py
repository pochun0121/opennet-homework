"""Web-specific base object wrapping common Selenium operations; every Page / Component inherits it.

- Tests and pages never touch the Selenium API directly (waits, retries and screenshots live here)
- sleep is injectable so unit tests never really wait
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from src.pages.locators import Locator

logger = logging.getLogger(__name__)

POLL_INTERVAL = 0.1


class ElementNotFoundError(AssertionError):
    """The (visible) element was not found within the timeout."""


class WebObject:
    def __init__(
        self,
        driver: WebDriver,
        timeout: float = 10,
        screenshot_dir: Path | str = "reports/screenshots",
        sleep: Callable[[float], None] = time.sleep,
        recorder=None,
    ) -> None:
        self.driver = driver
        self.timeout = timeout
        self.screenshot_dir = Path(screenshot_dir)
        self._sleep = sleep
        self.recorder = recorder  # optional StepRecorder; one frame per action

    def _record(self) -> None:
        if self.recorder is not None:
            self.recorder.capture()

    # ---------- navigation ----------
    def open(self, url: str) -> None:
        logger.info("open %s", url)
        self.driver.get(url)
        self._record()

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    # ---------- lookup ----------
    def _first_visible(self, locator: Locator) -> WebElement | None:
        for by, value in locator.strategies:
            for element in self.driver.find_elements(by, value):
                try:
                    if element.is_displayed():
                        return element
                except StaleElementReferenceException:
                    continue
        return None

    def find(self, locator: Locator, timeout: float | None = None) -> WebElement:
        timeout = self.timeout if timeout is None else timeout
        try:
            # A busy page can make is_displayed()'s script time out; keep polling instead of giving up
            wait = WebDriverWait(
                self.driver, timeout, poll_frequency=POLL_INTERVAL, ignored_exceptions=(TimeoutException,)
            )
            return wait.until(lambda _: self._first_visible(locator))
        except TimeoutException as exc:
            raise ElementNotFoundError(f"Element '{locator}' not found (waited {timeout}s)") from exc

    def find_all(self, locator: Locator) -> list[WebElement]:
        """Return all visible elements, using the first strategy that yields any."""
        for by, value in locator.strategies:
            found = [e for e in self.driver.find_elements(by, value) if e.is_displayed()]
            if found:
                return found
        return []

    def is_present(self, locator: Locator, timeout: float = 2) -> bool:
        try:
            self.find(locator, timeout)
            return True
        except ElementNotFoundError:
            return False

    # ---------- actions ----------
    def click(self, locator: Locator, timeout: float | None = None) -> None:
        """Click; retry once (after scrolling into view) if intercepted or stale."""
        for attempt in (1, 2):
            element = self.find(locator, timeout)
            try:
                element.click()
                logger.info("click %s", locator)
                self._record()
                return
            except (ElementClickInterceptedException, StaleElementReferenceException):
                if attempt == 2:
                    raise
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
                self._sleep(0.3)

    def click_element(self, element: WebElement) -> None:
        element.click()
        self._record()

    def type_text(self, locator: Locator, text: str, clear: bool = True, submit: bool = False) -> None:
        element = self.find(locator)
        if clear:
            element.clear()
        element.send_keys(text)
        if submit:
            element.send_keys(Keys.ENTER)
        logger.info("type '%s' into %s", text, locator)
        self._record()

    def get_text(self, locator: Locator) -> str:
        return self.find(locator).text

    def scroll_down(self, times: int = 1, pause: float = 1.0) -> None:
        """Scroll one viewport height per iteration."""
        for _ in range(times):
            self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
            self._sleep(pause)
            self._record()
        logger.info("scrolled down %s time(s)", times)

    # ---------- waits ----------
    def wait_until(self, condition: Callable[[WebDriver], object], timeout: float | None = None, message: str = ""):
        timeout = self.timeout if timeout is None else timeout
        try:
            # A busy page can make a single execute_script call time out; just poll again
            wait = WebDriverWait(
                self.driver, timeout, poll_frequency=POLL_INTERVAL, ignored_exceptions=(TimeoutException,)
            )
            return wait.until(condition, message)
        except TimeoutException as exc:
            raise ElementNotFoundError(message or "wait_until timed out") from exc

    def wait_for_page_loaded(self, timeout: float | None = None) -> None:
        self.wait_until(
            # 'interactive' is enough: Twitch keeps streaming resources open and may never reach 'complete'
            lambda d: d.execute_script("return document.readyState") in ("interactive", "complete"),
            timeout,
            "Page readyState never reached interactive/complete",
        )

    # ---------- screenshots ----------
    def screenshot(self, name: str) -> Path:
        safe = re.sub(r"[^\w\-]+", "_", name).strip("_") or "screenshot"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = self.screenshot_dir / f"{datetime.now():%Y%m%d_%H%M%S_%f}_{safe}.png"
        try:
            ok = self.driver.save_screenshot(str(path))
        except WebDriverException as exc:
            raise RuntimeError(f"Screenshot failed: {exc}") from exc
        if not ok:
            raise RuntimeError(f"Screenshot failed: {path}")
        logger.info("screenshot saved: %s", path)
        return path
