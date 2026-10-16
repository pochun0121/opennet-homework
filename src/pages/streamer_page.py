from __future__ import annotations

from pathlib import Path

from src.pages.components.modal_handler import ModalHandler
from src.pages.locators import Locator
from src.pages.web_object import WebObject


class StreamerPage(WebObject):
    PLAYER = Locator.css(
        "streamer.player",
        # Mobile web embeds the player in an iframe; desktop-style layouts expose <video> directly
        "iframe[src*='player.twitch.tv']",
        "main iframe",
        "video",
        "[data-a-target='video-player']",
        "[data-a-target='player-overlay-click-handler']",
    )

    def __init__(self, driver, modal_handler: ModalHandler | None = None, **kwargs):
        super().__init__(driver, **kwargs)
        self.modal_handler = modal_handler or ModalHandler(driver, **kwargs)

    def wait_until_loaded(self) -> None:
        """Dismiss pop-ups, wait for page and player, then dismiss pop-ups that appear after the player loads."""
        self.wait_for_page_loaded()
        self.modal_handler.dismiss_all()
        self.find(self.PLAYER)
        self.modal_handler.dismiss_all()
        self.wait_for_page_loaded()

    def take_screenshot(self, channel: str) -> Path:
        return self.screenshot(f"streamer_{channel}")
