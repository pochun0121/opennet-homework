"""Base fixtures: settings, driver, step recorder (screenshot / video policies come from pytest options)."""
from __future__ import annotations

import re

import pytest

from src.constants.settings import Settings
from src.utils.artifacts import StepRecorder, should_keep
from src.utils.report import register_artifact
from src.utils.driver_factory import create_driver


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


def _safe_name(node_name: str) -> str:
    return re.sub(r"[^\w\-]+", "_", node_name).strip("_")


@pytest.fixture
def driver(request, settings):
    drv = create_driver(settings)
    yield drv
    failed = bool(getattr(getattr(request.node, "rep_call", None), "failed", False))
    if should_keep(request.config.getoption("--screenshot"), failed):
        settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
        shot = settings.screenshot_dir / f"{_safe_name(request.node.name)}.png"
        drv.save_screenshot(str(shot))
        register_artifact(request.node, shot, "Screenshot")
        try:  # the page HTML makes it possible to see what blocked a click (e.g. a region-specific cookie banner)
            shot.with_suffix(".html").write_text(drv.page_source, encoding="utf-8")
        except Exception:
            pass
    drv.quit()


@pytest.fixture
def recorder(request, driver, settings):
    """StepRecorder when --video is not 'off'; the GIF is written to reports/videos only if the policy says so."""
    policy = request.config.getoption("--video")
    if policy == "off":
        yield None
        return
    rec = StepRecorder(driver)
    yield rec
    failed = bool(getattr(getattr(request.node, "rep_call", None), "failed", False))
    if should_keep(policy, failed):
        # The GIF is saved to disk only; the HTML report embeds screenshots (see register_artifact for the driver)
        rec.save(settings.video_dir / f"{_safe_name(request.node.name)}.gif")
