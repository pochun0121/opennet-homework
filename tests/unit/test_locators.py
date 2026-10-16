import pytest
from selenium.webdriver.common.by import By

from src.pages.locators import Locator


def test_css_builds_one_strategy_per_selector():
    loc = Locator.css("x", "a", "b")
    assert loc.strategies == ((By.CSS_SELECTOR, "a"), (By.CSS_SELECTOR, "b"))


def test_xpath_builds_xpath_strategy():
    assert Locator.xpath("x", "//a").strategies == ((By.XPATH, "//a"),)


def test_empty_strategies_rejected():
    with pytest.raises(ValueError):
        Locator("empty", ())


def test_str_is_name():
    assert str(Locator.css("home.search", "a")) == "home.search"
