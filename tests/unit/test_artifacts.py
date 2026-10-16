import io

import pytest
from PIL import Image

from src.utils.artifacts import StepRecorder, should_keep
from src.pages.web_object import WebObject


def _png(color="red", size=(400, 800)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.parametrize(
    "policy,failed,expected",
    [("off", True, False), ("off", False, False), ("on-failure", True, True),
     ("on-failure", False, False), ("always", True, True), ("always", False, True)],
    ids=["off-failed", "off-passed", "on_failure-failed", "on_failure-passed", "always-failed", "always-passed"],
)
def test_should_keep(policy, failed, expected):
    assert should_keep(policy, failed) is expected


def test_should_keep_rejects_unknown_policy():
    with pytest.raises(ValueError):
        should_keep("sometimes", True)


class TestStepRecorder:
    def test_capture_downscales_and_saves_gif(self, driver, tmp_path):
        driver.get_screenshot_as_png.side_effect = [_png("red"), _png("blue")]  # identical frames would be merged
        rec = StepRecorder(driver, width=100)
        rec.capture()
        rec.capture()
        out = rec.save(tmp_path / "sub" / "run.gif")
        assert len(rec) == 2 and out.exists()
        with Image.open(out) as gif:
            assert gif.size == (100, 200) and gif.n_frames == 2

    def test_max_frames_cap(self, driver):
        driver.get_screenshot_as_png.return_value = _png()
        rec = StepRecorder(driver, max_frames=2)
        for _ in range(5):
            rec.capture()
        assert len(rec) == 2

    def test_capture_failure_never_raises(self, driver):
        driver.get_screenshot_as_png.side_effect = RuntimeError("browser gone")
        rec = StepRecorder(driver)
        rec.capture()
        assert len(rec) == 0

    def test_save_without_frames_returns_none(self, driver, tmp_path):
        assert StepRecorder(driver).save(tmp_path / "x.gif") is None


class TestWebObjectRecording:
    def test_actions_record_frames(self, driver, no_sleep, tmp_path):
        from unittest.mock import MagicMock
        from src.pages.locators import Locator
        from tests.unit.conftest import make_element

        rec = MagicMock()
        driver.find_elements.return_value = [make_element()]
        web = WebObject(driver, timeout=0.3, screenshot_dir=tmp_path, sleep=no_sleep, recorder=rec)
        loc = Locator.css("x", "#x")
        web.open("u"); web.click(loc); web.type_text(loc, "a"); web.scroll_down(2)
        assert rec.capture.call_count == 5

    def test_no_recorder_is_fine(self, driver, no_sleep, tmp_path):
        WebObject(driver, screenshot_dir=tmp_path, sleep=no_sleep).open("u")
