from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def make_element(displayed: bool = True, href: str | None = None) -> MagicMock:
    el = MagicMock(name="WebElement")
    el.is_displayed.return_value = displayed
    el.get_attribute.side_effect = lambda attr: href if attr == "href" else None
    return el


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch, tmp_path):
    """Unit tests must not depend on a developer's real .env file."""
    monkeypatch.setenv("TWITCH_ENV_FILE", str(tmp_path / "missing.env"))


@pytest.fixture
def driver() -> MagicMock:
    """Fake WebDriver: finds no elements by default."""
    drv = MagicMock(name="WebDriver")
    drv.find_elements.return_value = []
    drv.save_screenshot.return_value = True
    return drv


@pytest.fixture
def no_sleep():
    return lambda _seconds: None
