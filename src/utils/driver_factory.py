"""Create a WebDriver with the Chrome Mobile Emulator enabled.

Option building is separate from driver creation so the former can be unit tested without a browser.
"""
from __future__ import annotations

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from src.constants.settings import Settings


def build_chrome_options(settings: Settings) -> Options:
    options = Options()
    options.add_experimental_option("mobileEmulation", {"deviceName": settings.device_name})
    # Twitch keeps streaming resources open, so waiting for the full load event is slow and can hang
    options.page_load_strategy = "eager"
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=en-US")
    options.add_experimental_option("prefs", {"intl.accept_languages": "en-US,en"})
    if settings.light_mode:
        options.add_argument("--autoplay-policy=user-gesture-required")  # no video autoplay
        options.add_argument("--mute-audio")
        options.add_argument("--disable-gpu")  # no hardware acceleration
        options.add_argument("--disable-dev-shm-usage")  # avoid /dev/shm exhaustion stalls
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-extensions")
    if settings.block_images:
        options.add_argument("--blink-settings=imagesEnabled=false")
    for arg in settings.chrome_args.split():
        options.add_argument(arg)
    if settings.chrome_binary:
        options.binary_location = settings.chrome_binary
    if settings.no_sandbox:
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    if settings.headless:
        options.add_argument("--headless=new")
    return options


def create_driver(settings: Settings) -> webdriver.Chrome:
    # Without an explicit path, Selenium Manager (>=4.6) resolves chromedriver automatically
    service = Service(settings.chromedriver_path) if settings.chromedriver_path else Service()
    driver = webdriver.Chrome(service=service, options=build_chrome_options(settings))
    if settings.light_mode:
        # Ask the page for reduced motion (CSS animations/transitions are minimized)
        driver.execute_cdp_cmd(
            "Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]}
        )
    driver.set_page_load_timeout(max(settings.timeout * 3, 30))
    return driver
