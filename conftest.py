"""Global conftest: pytest options, the "unit tests must pass before specs" gate and result hooks.
Fixtures live in src/fixtures (registered below as plugins).

Gate rules
- Unit and e2e selected in the same run: unit tests run first; any unit failure skips every e2e test
- Only e2e selected (pytest src/specs): tests/unit runs first in a subprocess; on failure the session aborts
- Emergency bypass: pytest --skip-unit-gate
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from src.constants.settings import ROOT_DIR, Settings
from src.utils.artifacts import POLICIES
from src.utils.report import apply_report_options, attach_artifacts, detect_stage
from src.utils.test_location import is_e2e, is_unit

pytest_plugins = ["src.fixtures.auto_markers", "src.fixtures.base_test", "src.fixtures.pages"]

_CHILD_ENV = "TWITCH_UNIT_GATE_CHILD"


def pytest_addoption(parser):
    # Defaults come from env vars / .env (see .env.example); command-line flags still win.
    defaults = Settings()
    parser.addoption("--screenshot", choices=POLICIES, default=defaults.screenshot_policy, help="Save a screenshot at test end")
    parser.addoption("--video", choices=POLICIES, default=defaults.video_policy, help="Save a step-by-step GIF recording")
    parser.addoption(
        "--skip-unit-gate", action="store_true", default=defaults.skip_unit_gate,
        help="Bypass the unit test gate (not recommended)",
    )


@pytest.hookimpl(tryfirst=True)  # must run before pytest-html / junitxml read their options in their own configure
def pytest_configure(config):
    """Apply env-driven defaults: -m expression (TWITCH_TAGS) and report paths. Explicit CLI flags always win."""
    if os.environ.get(_CHILD_ENV):  # the gate's unit subprocess must not overwrite the real reports
        return
    settings = Settings()
    tags = settings.tags.strip()
    if tags and not config.option.markexpr:
        config.option.markexpr = tags
    apply_report_options(config.option, settings, ROOT_DIR, detect_stage(config.args, ROOT_DIR))


def pytest_sessionstart(session):
    """Show the run configuration in the HTML report's Environment table."""
    try:
        from pytest_metadata.plugin import metadata_key
    except ImportError:
        return
    settings = Settings()
    session.config.stash.get(metadata_key, {}).update(
        {
            "Device": settings.device_name,
            "Headless": settings.headless,
            "Light mode": settings.light_mode,
            "Tags": settings.tags or "(all)",
            "Target": settings.base_url,
        }
    )


def pytest_html_report_title(report):
    report.title = "Twitch WAP E2E Test Report"


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):  # runs after -m / -k deselection
    has_unit = any(is_unit(i) for i in items)
    has_e2e = any(is_e2e(i) for i in items)
    config._unit_failed = False
    config._gate_enabled = (
        has_e2e
        and not config.getoption("--skip-unit-gate")
        and not config.option.collectonly
        and not os.environ.get(_CHILD_ENV)
    )
    if not config._gate_enabled:
        return

    if has_unit:
        items.sort(key=lambda i: 0 if is_unit(i) else 1)  # Unit tests always first (sort is stable)
        return

    # Only e2e selected: run the unit suite separately
    print("\n[gate] running unit tests first ...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT_DIR / "tests" / "unit"), "-q", "-p", "no:cacheprovider"],
        cwd=ROOT_DIR,
        env={**os.environ, _CHILD_ENV: "1"},
    )
    if result.returncode != 0:
        pytest.exit("[gate] unit tests failed, aborting e2e scenarios", returncode=result.returncode)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
    if report.when == "call" and report.failed and is_unit(item):
        item.config._unit_failed = True
    if report.when == "teardown":
        # Fixtures save screenshots / GIFs during teardown; embed them in the HTML report
        try:
            import pytest_html.extras as html_extras
        except ImportError:
            return
        attach_artifacts(report, item, html_extras)


def pytest_runtest_setup(item):
    if is_e2e(item) and getattr(item.config, "_gate_enabled", False) and item.config._unit_failed:
        pytest.skip("unit tests did not pass, skipping e2e scenario")
