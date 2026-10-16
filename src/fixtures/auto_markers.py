"""Auto-mark tests by location before -m / TWITCH_TAGS filtering runs."""
from __future__ import annotations

import pytest

from src.utils.test_location import is_e2e, is_unit


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    for item in items:
        if is_unit(item):
            item.add_marker(pytest.mark.unit)
        elif is_e2e(item):
            item.add_marker(pytest.mark.e2e)
