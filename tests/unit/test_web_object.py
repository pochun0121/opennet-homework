from unittest.mock import MagicMock

import pytest
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.keys import Keys

from src.pages.locators import Locator
from src.pages.web_object import ElementNotFoundError, WebObject
from tests.unit.conftest import make_element

LOC = Locator.css("demo", "#a", "#b")


@pytest.fixture
def web(driver, no_sleep, tmp_path):
    return WebObject(driver, timeout=0.3, screenshot_dir=tmp_path, sleep=no_sleep)


class TestFind:
    def test_returns_visible_element(self, web, driver):
        el = make_element()
        driver.find_elements.return_value = [el]
        assert web.find(LOC) is el

    def test_skips_hidden_elements(self, web, driver):
        hidden, visible = make_element(displayed=False), make_element()
        driver.find_elements.return_value = [hidden, visible]
        assert web.find(LOC) is visible

    def test_falls_back_to_second_strategy(self, web, driver):
        el = make_element()
        driver.find_elements.side_effect = lambda by, value: [el] if value == "#b" else []
        assert web.find(LOC) is el

    def test_raises_when_not_found(self, web):
        with pytest.raises(ElementNotFoundError, match="demo"):
            web.find(LOC)

    def test_stale_element_is_ignored(self, web, driver):
        stale = make_element()
        stale.is_displayed.side_effect = StaleElementReferenceException()
        driver.find_elements.return_value = [stale]
        with pytest.raises(ElementNotFoundError):
            web.find(LOC)

    def test_busy_page_script_timeout_is_retried(self, web, driver):
        busy = make_element()
        busy.is_displayed.side_effect = [TimeoutException("script timeout"), True]
        driver.find_elements.return_value = [busy]
        assert web.find(LOC) is busy

    def test_is_present_true_and_false(self, web, driver):
        assert web.is_present(LOC, timeout=0.2) is False
        driver.find_elements.return_value = [make_element()]
        assert web.is_present(LOC, timeout=0.2) is True

    def test_find_all_returns_only_visible(self, web, driver):
        v, h = make_element(), make_element(displayed=False)
        driver.find_elements.return_value = [v, h]
        assert web.find_all(LOC) == [v]


class TestActions:
    def test_click(self, web, driver):
        el = make_element()
        driver.find_elements.return_value = [el]
        web.click(LOC)
        el.click.assert_called_once()

    def test_click_retries_once_after_intercept(self, web, driver):
        el = make_element()
        el.click.side_effect = [ElementClickInterceptedException(), None]
        driver.find_elements.return_value = [el]
        web.click(LOC)
        assert el.click.call_count == 2
        driver.execute_script.assert_called_once()

    def test_click_raises_after_second_failure(self, web, driver):
        el = make_element()
        el.click.side_effect = ElementClickInterceptedException()
        driver.find_elements.return_value = [el]
        with pytest.raises(ElementClickInterceptedException):
            web.click(LOC)

    def test_type_text_clears_and_submits(self, web, driver):
        el = make_element()
        driver.find_elements.return_value = [el]
        web.type_text(LOC, "StarCraft II", submit=True)
        el.clear.assert_called_once()
        assert [c.args[0] for c in el.send_keys.call_args_list] == ["StarCraft II", Keys.ENTER]

    def test_type_text_without_clear_or_submit(self, web, driver):
        el = make_element()
        driver.find_elements.return_value = [el]
        web.type_text(LOC, "x", clear=False)
        el.clear.assert_not_called()
        el.send_keys.assert_called_once_with("x")

    def test_scroll_down_n_times(self, web, driver):
        sleeps = []
        web._sleep = sleeps.append
        web.scroll_down(times=2, pause=0.7)
        assert driver.execute_script.call_count == 2
        assert "scrollBy" in driver.execute_script.call_args.args[0]
        assert sleeps == [0.7, 0.7]


class TestWaits:
    def test_wait_for_page_loaded_ok(self, web, driver):
        driver.execute_script.return_value = "complete"
        web.wait_for_page_loaded()

    def test_wait_tolerates_script_timeout_then_succeeds(self, web, driver):
        from selenium.common.exceptions import TimeoutException

        driver.execute_script.side_effect = [TimeoutException(), "complete"]
        web.wait_for_page_loaded()

    def test_wait_for_page_loaded_accepts_interactive(self, web, driver):
        driver.execute_script.return_value = "interactive"
        web.wait_for_page_loaded()

    def test_wait_for_page_loaded_timeout(self, web, driver):
        driver.execute_script.return_value = "loading"
        with pytest.raises(ElementNotFoundError, match="readyState"):
            web.wait_for_page_loaded()


class TestScreenshot:
    def test_saves_into_dir_with_sanitized_name(self, web, driver, tmp_path):
        path = web.screenshot("streamer ninja/!")
        assert path.parent == tmp_path
        assert path.suffix == ".png" and "streamer_ninja" in path.name
        driver.save_screenshot.assert_called_once_with(str(path))

    def test_raises_when_driver_reports_failure(self, web, driver):
        driver.save_screenshot.return_value = False
        with pytest.raises(RuntimeError):
            web.screenshot("x")


def test_open_delegates_to_driver(web, driver):
    web.open("https://example.com")
    driver.get.assert_called_once_with("https://example.com")
