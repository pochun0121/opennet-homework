"""Failure artifacts: screenshot and step-based video, both controlled by pytest options.

Policies: off | on-failure | always
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

POLICIES = ("off", "on-failure", "always")


def should_keep(policy: str, failed: bool) -> bool:
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy '{policy}', expected one of {POLICIES}")
    return policy == "always" or (policy == "on-failure" and failed)


class StepRecorder:
    """Records one frame after every WebObject action and saves them as an animated GIF.

    Frames are captured synchronously (no background thread), so recording never races with
    WebDriver commands. Frames are downscaled and capped to keep memory bounded.
    """

    def __init__(self, driver, max_frames: int = 150, width: int = 360, frame_ms: int = 700) -> None:
        self.driver = driver
        self.max_frames = max_frames
        self.width = width
        self.frame_ms = frame_ms
        self._frames: list[Image.Image] = []

    def __len__(self) -> int:
        return len(self._frames)

    def capture(self) -> None:
        if len(self._frames) >= self.max_frames:
            return
        try:
            png = self.driver.get_screenshot_as_png()
            image = Image.open(io.BytesIO(png)).convert("RGB")
        except Exception as exc:  # recording must never break a test
            logger.warning("frame capture failed: %s", exc)
            return
        ratio = self.width / image.width
        self._frames.append(image.resize((self.width, max(1, int(image.height * ratio)))))

    def save(self, path: Path | str) -> Path | None:
        if not self._frames:
            return None
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        first, rest = self._frames[0], self._frames[1:]
        first.save(path, save_all=True, append_images=rest, duration=self.frame_ms, loop=0)
        logger.info("video saved: %s (%d frames)", path, len(self._frames))
        return path
