"""WAP scenario: search Twitch for StarCraft II, pick a streamer, screenshot once the page has loaded.

The script only says what to do; how to do it lives in the page objects / WebObject.
"""
import pytest


@pytest.mark.timeout(900)  # real Twitch pages can be slow
@pytest.mark.smoke
@pytest.mark.regression
def test_search_starcraft_and_screenshot_streamer(home_page, search_page, streamer_page, settings):
    home_page.go_to()                                   # 1. go to Twitch
    home_page.click_search_icon()                       # 2. click search icon
    search_page.search(settings.search_term)            # 3. input StarCraft II
    search_page.scroll_down(times=2)                    # 4. scroll down 2 times
    channel = search_page.select_streamer()             # 5. select one streamer
    streamer_page.wait_until_loaded()                   # 6. wait until loaded (handles pop-up)
    screenshot = streamer_page.take_screenshot(channel)

    assert screenshot.exists() and screenshot.stat().st_size > 0
