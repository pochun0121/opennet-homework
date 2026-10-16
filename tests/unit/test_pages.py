from unittest.mock import MagicMock

import pytest

from src.pages.home_page import HomePage
from src.pages.search_page import SearchPage, streamer_name_from_card_text
from src.pages.streamer_page import StreamerPage
from src.pages.web_object import ElementNotFoundError
from tests.unit.conftest import make_element

KW = dict(timeout=0.3)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("LIVE\nWardiii\nStarCraft II\n324 viewers", "Wardiii"),
        ("Wardiii\nLIVE", "Wardiii"),
        ("  \n LIVE \n ESL_SC2 \n", "ESL_SC2"),
        ("LIVE", None),
        ("", None),
        (None, None),
    ],
)
def test_streamer_name_from_card_text(text, expected):
    assert streamer_name_from_card_text(text) == expected


def card(text):
    el = make_element()
    el.text = text
    return el


class TestHomePage:
    def test_go_to_opens_base_url_and_dismisses_modals(self, driver, tmp_path):
        driver.execute_script.return_value = "complete"
        modal = MagicMock()
        HomePage(driver, "https://www.twitch.tv", modal_handler=modal, screenshot_dir=tmp_path, **KW).go_to()
        driver.get.assert_called_once_with("https://www.twitch.tv")
        modal.dismiss_all.assert_called_once()

    def test_click_search_icon_retries_after_modal_blocks_click(self, driver, tmp_path):
        from selenium.common.exceptions import ElementClickInterceptedException

        icon = make_element()
        icon.click.side_effect = [ElementClickInterceptedException()] * 2 + [None]
        driver.find_elements.return_value = [icon]
        modal = MagicMock()
        HomePage(driver, "u", modal_handler=modal, screenshot_dir=tmp_path, sleep=lambda _: None, **KW).click_search_icon()
        modal.dismiss_all.assert_called_once()
        assert icon.click.call_count == 3

    def test_unknown_overlay_is_handled_through_its_accept_button(self, driver, tmp_path):
        from selenium.common.exceptions import ElementClickInterceptedException

        icon = make_element()
        icon.click.side_effect = [ElementClickInterceptedException()] * 4 + [None]  # two attempts, twice
        driver.find_elements.return_value = [icon]
        modal = MagicMock()
        modal.dismiss_blocker_of.return_value = True
        HomePage(driver, "u", modal_handler=modal, screenshot_dir=tmp_path, sleep=lambda _: None, **KW).click_search_icon()
        modal.dismiss_all.assert_called_once()
        modal.dismiss_blocker_of.assert_called_once()
        assert icon.click.call_count == 5

    def test_gives_up_when_overlay_cannot_be_dismissed(self, driver, tmp_path):
        from selenium.common.exceptions import ElementClickInterceptedException

        icon = make_element()
        icon.click.side_effect = ElementClickInterceptedException()
        driver.find_elements.return_value = [icon]
        modal = MagicMock()
        modal.dismiss_blocker_of.return_value = False
        page = HomePage(driver, "u", modal_handler=modal, screenshot_dir=tmp_path, sleep=lambda _: None, **KW)
        with pytest.raises(ElementClickInterceptedException):
            page.click_search_icon()

    def test_click_search_icon(self, driver, tmp_path):
        icon = make_element()
        driver.find_elements.return_value = [icon]
        HomePage(driver, "u", screenshot_dir=tmp_path, **KW).click_search_icon()
        icon.click.assert_called_once()


class TestSearchPage:
    def test_search_types_term_and_submits(self, driver, tmp_path):
        box = make_element()
        driver.find_elements.return_value = [box]
        SearchPage(driver, screenshot_dir=tmp_path, **KW).search("StarCraft II")
        assert box.send_keys.call_args_list[0].args[0] == "StarCraft II"

    def test_select_streamer_clicks_first_card_and_returns_name(self, driver, tmp_path):
        first, second = card("LIVE\nserral\n10 viewers"), card("LIVE\nmaru\n5 viewers")
        driver.find_elements.return_value = [first, second]
        assert SearchPage(driver, screenshot_dir=tmp_path, **KW).select_streamer() == "serral"
        first.click.assert_called_once()
        second.click.assert_not_called()

    def test_select_streamer_by_index(self, driver, tmp_path):
        driver.find_elements.return_value = [card("LIVE\na"), card("LIVE\nb")]
        assert SearchPage(driver, screenshot_dir=tmp_path, **KW).select_streamer(1) == "b"

    def test_select_streamer_index_out_of_range(self, driver, tmp_path):
        driver.find_elements.return_value = [card("LIVE\na")]
        with pytest.raises(ElementNotFoundError):
            SearchPage(driver, screenshot_dir=tmp_path, **KW).select_streamer(3)

    def test_select_streamer_no_cards(self, driver, tmp_path):
        with pytest.raises(ElementNotFoundError):
            SearchPage(driver, screenshot_dir=tmp_path, **KW).select_streamer()


class TestStreamerPage:
    def test_wait_until_loaded_dismisses_modal_around_player_wait(self, driver, tmp_path):
        driver.execute_script.return_value = "complete"
        driver.find_elements.return_value = [make_element()]
        modal = MagicMock()
        StreamerPage(driver, modal_handler=modal, screenshot_dir=tmp_path, **KW).wait_until_loaded()
        assert modal.dismiss_all.call_count == 2

    def test_wait_until_loaded_fails_without_player(self, driver, tmp_path):
        driver.execute_script.return_value = "complete"
        with pytest.raises(ElementNotFoundError, match="streamer.player"):
            StreamerPage(driver, modal_handler=MagicMock(), screenshot_dir=tmp_path, timeout=0.2).wait_until_loaded()

    def test_take_screenshot_names_file_after_channel(self, driver, tmp_path):
        path = StreamerPage(driver, modal_handler=MagicMock(), screenshot_dir=tmp_path, **KW).take_screenshot("serral")
        assert "streamer_serral" in path.name
