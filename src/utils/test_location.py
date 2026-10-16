"""Classify collected tests by location: tests/unit -> unit, src/specs -> e2e."""
from __future__ import annotations

from pathlib import Path

from src.constants.env import ROOT_DIR


def _parts(item) -> tuple[str, ...]:
    return Path(str(item.fspath)).relative_to(ROOT_DIR).parts


def is_unit(item) -> bool:
    return "unit" in _parts(item)


def is_e2e(item) -> bool:
    return "specs" in _parts(item)
