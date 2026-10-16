from __future__ import annotations

from selenium.common.exceptions import ElementClickInterceptedException

from src.pages.components.modal_handler import ModalHandler
from src.pages.locators import Locator
from src.pages.web_object import WebObject


class HomePage(WebObject):
    SEARCH_ICON = Locator.css(
        "home.search_icon",
        # Mobile web: search lives behind the magnifier/Browse tab in the bottom nav (opens /directory with a search box)
        "a[href='/directory']",
        "a[href='/search']",
        "[data-a-target='search-icon']",
        "button[aria-label='Search']",
    )

    def __init__(self, driver, base_url: str, modal_handler: ModalHandler | None = None, **kwargs):
        super().__init__(driver, **kwargs)
        self.base_url = base_url
        self.modal_handler = modal_handler or ModalHandler(driver, **kwargs)

    def go_to(self) -> "HomePage":
        self.open(self.base_url)
        self.wait_for_page_loaded()
        self.modal_handler.dismiss_all()  # app-install sheet blocks the header on mobile web
        return self

    def click_search_icon(self) -> None:
        try:
            self.click(self.SEARCH_ICON)
        except ElementClickInterceptedException:
            # A sheet / banner can show up late (app-install sheet, cookie consent depending on region): close it, retry
            self.modal_handler.dismiss_all()
            try:
                self.click(self.SEARCH_ICON)
            except ElementClickInterceptedException:
                # Still covered by something we have no locator for: find it and press its accept button
                if not self.modal_handler.dismiss_blocker_of(self.SEARCH_ICON):
                    raise
                self.click(self.SEARCH_ICON)
