from __future__ import annotations

from selenium.webdriver.remote.webelement import WebElement

from src.pages.locators import Locator
from src.pages.web_object import ElementNotFoundError, WebObject

NON_NAME_LINES = frozenset({"live", ""})


def streamer_name_from_card_text(text: str | None) -> str | None:
    """First meaningful line of a result card, e.g. 'LIVE\\nWardiii\\n...' -> 'Wardiii'."""
    for line in (text or "").splitlines():
        line = line.strip()
        if line.lower() not in NON_NAME_LINES:
            return line
    return None


class SearchPage(WebObject):
    SEARCH_INPUT = Locator.css(
        "search.input",
        "input[type='search']",
        "input[data-a-target='tw-input']",
        "input[placeholder*='Search']",
    )
    # Mobile web renders live-channel result cards as <button> elements (no href); desktop-style layouts use links.
    STREAMER_CARDS = Locator.xpath(
        "search.streamer_cards",
        "//main//section//button[contains(., 'viewers')]",
        "//main//a[contains(@href, '/') and contains(., 'viewers')]",
    )

    def search(self, term: str) -> None:
        self.type_text(self.SEARCH_INPUT, term, submit=True)

    def _streamer_cards(self) -> list[tuple[str, WebElement]]:
        cards = []
        for element in self.find_all(self.STREAMER_CARDS):
            name = streamer_name_from_card_text(element.text)
            if name:
                cards.append((name, element))
        return cards

    def select_streamer(self, index: int = 0) -> str:
        """Click the streamer card at the given index and return the streamer name."""
        cards = self.wait_until(lambda _: self._streamer_cards() or False, message="No streamer cards in the search results")
        if index >= len(cards):
            raise ElementNotFoundError(f"Only {len(cards)} streamer(s) available, cannot select index={index}")
        name, element = cards[index]
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        self.click_element(element)
        return name
