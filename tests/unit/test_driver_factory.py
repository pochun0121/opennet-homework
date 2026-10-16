from src.constants.settings import Settings
from src.utils.driver_factory import build_chrome_options


def test_mobile_emulation_uses_configured_device(monkeypatch):
    monkeypatch.setenv("TWITCH_DEVICE", "iPhone 12 Pro")
    opts = build_chrome_options(Settings())
    assert opts.experimental_options["mobileEmulation"] == {"deviceName": "iPhone 12 Pro"}


def test_browser_language_forced_to_english():
    opts = build_chrome_options(Settings())
    assert opts.experimental_options["prefs"]["intl.accept_languages"].startswith("en-US")


def test_headless_flag_only_when_enabled(monkeypatch):
    monkeypatch.setenv("TWITCH_HEADLESS", "true")
    assert "--headless=new" in build_chrome_options(Settings()).arguments
    monkeypatch.setenv("TWITCH_HEADLESS", "false")
    assert "--headless=new" not in build_chrome_options(Settings()).arguments


def test_settings_defaults(monkeypatch):
    for key in ("TWITCH_DEVICE", "TWITCH_SEARCH_TERM", "TWITCH_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    s = Settings()
    assert (s.device_name, s.search_term, s.base_url) == ("Pixel 7", "StarCraft II", "https://www.twitch.tv")


def test_container_flags_and_binary(monkeypatch):
    monkeypatch.setenv("TWITCH_NO_SANDBOX", "true")
    monkeypatch.setenv("CHROME_BIN", "/usr/bin/chromium")
    opts = build_chrome_options(Settings())
    assert "--no-sandbox" in opts.arguments and "--disable-dev-shm-usage" in opts.arguments
    assert opts.binary_location == "/usr/bin/chromium"


def test_no_container_flags_by_default(monkeypatch):
    monkeypatch.delenv("TWITCH_NO_SANDBOX", raising=False)
    monkeypatch.delenv("CHROME_BIN", raising=False)
    opts = build_chrome_options(Settings())
    assert "--no-sandbox" not in opts.arguments and not opts.binary_location


def test_eager_page_load_strategy():
    assert build_chrome_options(Settings()).page_load_strategy == "eager"


def test_light_mode_disables_autoplay_and_audio(monkeypatch):
    monkeypatch.setenv("TWITCH_LIGHT_MODE", "true")
    args = build_chrome_options(Settings()).arguments
    assert "--autoplay-policy=user-gesture-required" in args and "--mute-audio" in args
    assert "--disable-gpu" in args and "--disable-dev-shm-usage" in args


def test_light_mode_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("TWITCH_LIGHT_MODE", "false")
    assert "--mute-audio" not in build_chrome_options(Settings()).arguments


def test_images_blocked_only_when_requested(monkeypatch):
    monkeypatch.setenv("TWITCH_BLOCK_IMAGES", "true")
    assert "--blink-settings=imagesEnabled=false" in build_chrome_options(Settings()).arguments
    monkeypatch.delenv("TWITCH_BLOCK_IMAGES")
    assert "--blink-settings=imagesEnabled=false" not in build_chrome_options(Settings()).arguments


def test_create_driver_applies_reduced_motion(monkeypatch):
    from unittest.mock import MagicMock, patch

    from src.utils.driver_factory import create_driver

    fake = MagicMock()
    with patch("src.utils.driver_factory.webdriver.Chrome", return_value=fake):
        create_driver(Settings())
    cmd, params = fake.execute_cdp_cmd.call_args.args
    assert cmd == "Emulation.setEmulatedMedia" and params["features"][0]["value"] == "reduce"
    fake.set_page_load_timeout.assert_called_once()


def test_extra_chrome_args_from_env(monkeypatch):
    monkeypatch.setenv("TWITCH_CHROME_ARGS", "--disable-quic   --no-proxy-server")
    args = build_chrome_options(Settings()).arguments
    assert "--disable-quic" in args and "--no-proxy-server" in args
