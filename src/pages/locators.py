"""Locator: one logical element with several fallback location strategies.

Twitch changes its DOM often. Keeping locators as class attributes on each page
means a redesign only touches the locator, not the scenarios or the action logic.
"""
from __future__ import annotations

from dataclasses import dataclass

from selenium.webdriver.common.by import By

Strategy = tuple[str, str]


@dataclass(frozen=True)
class Locator:
    name: str
    strategies: tuple[Strategy, ...]

    def __post_init__(self) -> None:
        if not self.strategies:
            raise ValueError(f"Locator '{self.name}' needs at least one location strategy")

    @classmethod
    def css(cls, name: str, *selectors: str) -> "Locator":
        return cls(name, tuple((By.CSS_SELECTOR, s) for s in selectors))

    @classmethod
    def xpath(cls, name: str, *expressions: str) -> "Locator":
        return cls(name, tuple((By.XPATH, e) for e in expressions))

    def __str__(self) -> str:
        return self.name
