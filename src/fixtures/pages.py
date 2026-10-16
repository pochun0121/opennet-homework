import pytest

from src.pages.home_page import HomePage
from src.pages.search_page import SearchPage
from src.pages.streamer_page import StreamerPage


@pytest.fixture
def page_kwargs(settings, recorder):
    return {"timeout": settings.timeout, "screenshot_dir": settings.screenshot_dir, "recorder": recorder}


@pytest.fixture
def home_page(driver, settings, page_kwargs):
    return HomePage(driver, settings.base_url, **page_kwargs)


@pytest.fixture
def search_page(driver, page_kwargs):
    return SearchPage(driver, **page_kwargs)


@pytest.fixture
def streamer_page(driver, page_kwargs):
    return StreamerPage(driver, **page_kwargs)
