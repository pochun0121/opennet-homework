"""All tunable parameters in one place. Values come from env vars / `.env` (see env.py and .env.example)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.constants.env import ROOT_DIR, get_bool, get_env
from src.constants.test_data import BASE_URL, DEFAULT_DEVICE, SEARCH_TERM

__all__ = ["ROOT_DIR", "Settings"]


@dataclass(frozen=True)
class Settings:
    # --- target ---
    base_url: str = field(default_factory=lambda: get_env("TWITCH_BASE_URL", BASE_URL))
    search_term: str = field(default_factory=lambda: get_env("TWITCH_SEARCH_TERM", SEARCH_TERM))

    # --- browser ---
    device_name: str = field(default_factory=lambda: get_env("TWITCH_DEVICE", DEFAULT_DEVICE))
    headless: bool = field(default_factory=lambda: get_bool("TWITCH_HEADLESS", False))
    timeout: float = field(default_factory=lambda: float(get_env("TWITCH_TIMEOUT", "15")))
    # Light mode: fewer animations / no autoplay media so heavy Twitch pages load and settle faster
    light_mode: bool = field(default_factory=lambda: get_bool("TWITCH_LIGHT_MODE", True))
    block_images: bool = field(default_factory=lambda: get_bool("TWITCH_BLOCK_IMAGES", False))
    # Container support: system Chromium + chromedriver, and flags Chrome needs when running as root in Docker
    no_sandbox: bool = field(default_factory=lambda: get_bool("TWITCH_NO_SANDBOX", False))
    # Extra Chrome command-line flags, whitespace separated, e.g. "--disable-quic --no-proxy-server"
    chrome_args: str = field(default_factory=lambda: get_env("TWITCH_CHROME_ARGS", ""))
    chrome_binary: str = field(default_factory=lambda: get_env("CHROME_BIN", ""))
    chromedriver_path: str = field(default_factory=lambda: get_env("CHROMEDRIVER_PATH", ""))

    # --- test run ---
    tags: str = field(default_factory=lambda: get_env("TWITCH_TAGS", ""))  # pytest -m expression, e.g. "smoke"
    screenshot_policy: str = field(default_factory=lambda: get_env("TWITCH_SCREENSHOT_POLICY", "on-failure"))
    video_policy: str = field(default_factory=lambda: get_env("TWITCH_VIDEO_POLICY", "on-failure"))
    skip_unit_gate: bool = field(default_factory=lambda: get_bool("TWITCH_SKIP_UNIT_GATE", False))

    # --- output ---
    html_report: str = field(default_factory=lambda: get_env("TWITCH_HTML_REPORT", "reports/report-{stage}.html"))  # "" = off
    junit_xml: str = field(default_factory=lambda: get_env("TWITCH_JUNIT_XML", ""))  # "" = off (CI sets it)
    screenshot_dir: Path = field(
        default_factory=lambda: Path(get_env("TWITCH_SCREENSHOT_DIR", str(ROOT_DIR / "reports" / "screenshots")))
    )
    video_dir: Path = field(
        default_factory=lambda: Path(get_env("TWITCH_VIDEO_DIR", str(ROOT_DIR / "reports" / "videos")))
    )
