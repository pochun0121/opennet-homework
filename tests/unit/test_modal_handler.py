from src.pages.components.modal_handler import ModalHandler
from src.pages.locators import Locator
from tests.unit.conftest import make_element

POPUP_A = Locator.css("popup_a", "#a")
POPUP_B = Locator.css("popup_b", "#b")


def _handler(driver, no_sleep, tmp_path):
    return ModalHandler(
        driver, locators=(POPUP_A, POPUP_B), probe_timeout=0.2, timeout=0.2, screenshot_dir=tmp_path, sleep=no_sleep
    )


def test_no_popup_returns_zero(driver, no_sleep, tmp_path):
    assert _handler(driver, no_sleep, tmp_path).dismiss_all() == 0


def test_dismisses_present_popup(driver, no_sleep, tmp_path):
    el = make_element()
    state = {"open": True}

    def find(by, value):
        return [el] if value == "#a" and state["open"] else []

    driver.find_elements.side_effect = find
    el.click.side_effect = lambda: state.update(open=False)
    assert _handler(driver, no_sleep, tmp_path).dismiss_all() == 1
    el.click.assert_called_once()


def test_dismisses_chained_popups(driver, no_sleep, tmp_path):
    a, b = make_element(), make_element()
    state = {"a": True, "b": True}
    driver.find_elements.side_effect = lambda by, v: ([a] if v == "#a" and state["a"] else []) + (
        [b] if v == "#b" and state["b"] else []
    )
    a.click.side_effect = lambda: state.update(a=False)
    b.click.side_effect = lambda: state.update(b=False)
    assert _handler(driver, no_sleep, tmp_path).dismiss_all() == 2


def test_max_rounds_prevents_infinite_loop(driver, no_sleep, tmp_path):
    driver.find_elements.return_value = [make_element()]  # can never be closed
    assert _handler(driver, no_sleep, tmp_path).dismiss_all(max_rounds=2) == 4


class TestDismissBlocker:
    TARGET = Locator.css("target", "#t")

    def _handler(self, driver, no_sleep, tmp_path):
        return ModalHandler(driver, locators=(), probe_timeout=0.2, timeout=0.2, screenshot_dir=tmp_path, sleep=no_sleep)

    def test_clicks_the_accept_button_found_in_the_overlay(self, driver, no_sleep, tmp_path):
        target, accept = make_element(), make_element()
        driver.find_elements.return_value = [target]
        driver.execute_script.return_value = [accept, "we use cookies accept all"]
        assert self._handler(driver, no_sleep, tmp_path).dismiss_blocker_of(self.TARGET) is True
        accept.click.assert_called_once()
        script, passed_target, texts = driver.execute_script.call_args.args
        assert passed_target is target and "accept all" in texts

    def test_returns_false_when_nothing_covers_the_target(self, driver, no_sleep, tmp_path):
        driver.find_elements.return_value = [make_element()]
        driver.execute_script.return_value = None
        assert self._handler(driver, no_sleep, tmp_path).dismiss_blocker_of(self.TARGET) is False

    def test_unknown_overlay_is_logged_not_clicked(self, driver, no_sleep, tmp_path, caplog):
        driver.find_elements.return_value = [make_element()]
        driver.execute_script.return_value = [None, '<div class="weird-banner">Hello</div>']
        with caplog.at_level("WARNING"):
            assert self._handler(driver, no_sleep, tmp_path).dismiss_blocker_of(self.TARGET) is False
        assert "weird-banner" in caplog.text  # the CI log shows what to add to DISMISS_LOCATORS


def test_cookie_banner_locator_matches_accept_text_case_insensitively():
    from src.pages.components.modal_handler import DISMISS_LOCATORS

    xpath = next(loc for loc in DISMISS_LOCATORS if loc.name == "cookie_accept_text").strategies[0][1]
    assert "translate(" in xpath and "'accept all'" in xpath and "@role='dialog'" in xpath


def test_twitch_cookie_banner_proceed_button_is_known():
    from src.pages.components.modal_handler import ACCEPT_TEXTS, DISMISS_LOCATORS

    assert "proceed" in ACCEPT_TEXTS
    proceed = next(loc for loc in DISMISS_LOCATORS if loc.name == "cookie_proceed")
    assert proceed.strategies[0][1] == "//button[normalize-space()='Proceed']"


def test_settings_button_is_never_treated_as_accept():
    from src.pages.components.modal_handler import ACCEPT_TEXTS

    # "Cookies & Ads Choices" opens a preferences page instead of closing the banner
    assert not any("choices" in text or "manage" in text or "settings" in text for text in ACCEPT_TEXTS)
