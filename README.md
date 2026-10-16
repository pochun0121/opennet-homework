# Twitch WAP test framework

End-to-end test framework for Twitch mobile web (WAP): **pytest + Selenium (Python)**, Chrome mobile emulator,
**Page Object model**, runnable locally or in **Docker**, wired to **GitHub Actions**.

The sample scenario: open Twitch -> click search -> search `StarCraft II` -> scroll twice -> pick a streamer ->
wait for the streamer page (handling pop-ups) -> take a screenshot.

## How to run it

There are two ways to run the tests. Pick one.

### Option A: run it on GitHub (nothing to install)

1. Open the repository on GitHub and go to the **Actions** tab.
2. Select the **twitch-wap-tests** workflow in the left list, then click **Run workflow**.
   Optional inputs: search term (default `StarCraft II`), device (default `Pixel 7`), tags (a pytest `-m`
   expression such as `smoke`), and video policy.
3. Open the finished run:
   - the **Summary** at the bottom shows a results table (passed / failed / duration, failed test names);
   - **Artifacts** has `reports-<run id>`: unzip it and open `report-e2e.html` for the report with the screenshot,
     `screenshots/` for the streamer-page screenshot, and `e2e-junit.xml` for the raw result.

The workflow also runs automatically on every push to `main`, on pull requests, and nightly. The `unit` job runs
first; the browser scenario (`e2e` job) only starts when it passes.

### Option B: clone it and run it locally

    git clone https://github.com/pochun0121/opennet-homework.git
    cd opennet-homework

With Docker (recommended: same environment as CI, no local Chrome needed):

    docker build -t twitch-wap-tests .
    docker run --rm --shm-size=1g -v "$PWD/reports:/app/reports" twitch-wap-tests src/specs
    open reports/report-e2e.html

Without Docker (needs Google Chrome):

    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env                 # optional: every variable has a default
    pytest tests/unit                    # fast, browserless -> reports/report-unit.html
    pytest src/specs                     # the browser scenario (unit tests run first as a gate)
    open reports/report-e2e.html

`pytest` with no arguments runs everything and writes a single `reports/report-all.html`. Running locally on a busy
machine can be much slower than in Docker or CI; see *Known limitations*.

## Project layout

    .github/workflows/e2e-tests.yml   CI: unit job, then e2e job (needs: unit)
    src/
      pages/                Page objects (POM core)
        web_object.py       WebObject: web-specific base class (find / click / type / scroll / wait / screenshot)
        locators.py         Locator: one logical element, several fallback strategies
        home_page.py, search_page.py, streamer_page.py
        components/         Cross-page components (modal_handler.py: pop-up dismissal)
      specs/                Test scenarios, grouped by feature (steps only, no Selenium calls)
        search/test_search_starcraft.py
      fixtures/             pytest plugins: base_test.py (settings, driver, recorder), pages.py, auto_markers.py
      utils/                UI-independent helpers
        driver_factory.py   Chrome + mobile emulation options
        artifacts.py        screenshot / GIF policies and the step recorder
        report.py           pytest-html and JUnit wiring
        junit_summary.py    JUnit XML -> Markdown table for the GitHub job summary
        test_location.py    classify tests as unit / e2e by path
      constants/            env.py (.env loading), settings.py (all options), test_data.py (static data)
    tests/unit/             Browserless unit tests (mock driver) for src/pages and src/utils
    conftest.py             pytest options, unit-before-e2e gate, result hooks
    pytest.ini, .coveragerc, requirements.txt, .env.example
    Dockerfile, docker-compose.yml, .dockerignore, .gitignore

Design rules: scenarios only describe *what* to do; *how* lives in page objects / `WebObject`; element locators are
class attributes on each page, so a Twitch redesign only touches the locator.

## Running tests

    pytest                       # tests/unit then src/specs; specs are skipped if any unit test fails
    pytest tests/unit            # unit only
    pytest tests/unit --cov      # + coverage, fails below 85% (.coveragerc)
    pytest src/specs             # scenarios only (the unit suite runs first in a subprocess; failure aborts)
    pytest -m smoke              # select by marker (smoke, regression, unit, e2e)
    pytest -o log_cli=true src/specs   # watch live logs of a browser run
    pytest --skip-unit-gate      # run scenarios even if unit tests fail (not recommended)

**Unit-test gate.** Browser scenarios run only after the unit tests for the page objects / utils pass. Unit tests that
were deselected (for example by `-m`) are still run first in a subprocess, and the gate is skipped for `--collect-only`.

## Configuration (one place)

Every runtime variable is documented in **`.env.example`**. Copy it to `.env` and uncomment only what you change.

Precedence: **real env vars / CLI flags > `.env` > defaults in `src/constants/settings.py`**.

    TWITCH_HEADLESS=true TWITCH_TAGS=smoke pytest      # one-off override
    pytest -m "regression and not smoke"               # CLI -m beats TWITCH_TAGS

| Variable | Default | Purpose |
|---|---|---|
| `TWITCH_BASE_URL`, `TWITCH_SEARCH_TERM` | `https://www.twitch.tv`, `StarCraft II` | target and search keyword |
| `TWITCH_DEVICE` | `Pixel 7` | Chrome DevTools emulated device |
| `TWITCH_HEADLESS` | `false` | run without a visible window |
| `TWITCH_TIMEOUT` | `15` | element wait timeout (seconds) |
| `TWITCH_LIGHT_MODE` | `true` | no autoplay, muted, reduced motion, no GPU |
| `TWITCH_BLOCK_IMAGES` | `false` | skip images (faster, but screenshots lose images) |
| `TWITCH_NO_SANDBOX` | `false` | needed when Chrome runs as root, i.e. in Docker |
| `TWITCH_CHROME_ARGS` | empty | extra Chrome flags, whitespace separated |
| `CHROME_BIN`, `CHROMEDRIVER_PATH` | empty | custom browser / driver (set in the Docker image) |
| `TWITCH_TAGS` | empty | default pytest `-m` expression |
| `TWITCH_SCREENSHOT_POLICY`, `TWITCH_VIDEO_POLICY` | `on-failure` | `off` / `on-failure` / `always` |
| `TWITCH_SKIP_UNIT_GATE` | `false` | run scenarios even if unit tests fail |
| `TWITCH_HTML_REPORT` | `reports/report-{stage}.html` | pytest-html path, empty = off |
| `TWITCH_JUNIT_XML` | empty | JUnit XML path, empty = off (CI sets it) |
| `TWITCH_SCREENSHOT_DIR`, `TWITCH_VIDEO_DIR` | `reports/screenshots`, `reports/videos` | artifact folders |
| `TWITCH_ENV_FILE` | `.env` | alternate env file |

## Screenshots, recordings and reports

- `--screenshot` / `--video` (`off|on-failure|always`) are pytest options whose defaults come from the variables above.
- The scenario's own screenshot (step 6) is always taken and saved under `reports/screenshots/`.
- Video is a step-based GIF: one frame is captured after every `WebObject` action (open / click / type / scroll),
  saved under `reports/videos/`.

| Report | For | Default location |
|---|---|---|
| **pytest-html** (one self-contained file) | people, live viewing | `reports/report-unit.html`, `reports/report-e2e.html` (`report-all.html` when both run together) |
| **JUnit XML** | CI, trend tools | set `TWITCH_JUNIT_XML`, for example `reports/junit-{stage}.xml` |

- `{stage}` in a configured path becomes `unit` / `e2e` / `all`, so a unit run never overwrites the e2e report.
- The HTML report embeds the end-of-test screenshot (click to enlarge) and an Environment table (device, headless,
  tags, target). GIFs are not embedded. Open one with `open reports/report-e2e.html`; the file can be emailed as is.
- The gate's internal unit-test subprocess never overwrites these reports.

## Docker

    docker build -t twitch-wap-tests .
    docker run --rm --shm-size=1g -v "$PWD/reports:/app/reports" twitch-wap-tests            # unit, then e2e
    docker run --rm twitch-wap-tests tests/unit                                              # unit only
    docker run --rm --shm-size=1g --env-file .env twitch-wap-tests                           # reuse .env (no quotes around values)
    docker compose run --rm tests

The image uses Debian's `chromium` + `chromium-driver` (versions match, amd64 and arm64) and sets
`TWITCH_HEADLESS=true`, `TWITCH_NO_SANDBOX=true`, `CHROME_BIN`, `CHROMEDRIVER_PATH`. `.env` is not copied into the
image (see `.dockerignore`); pass it with `--env-file`. The first build downloads ~250 MB of apt packages and can be
slow on a poor network; later builds reuse the cached layers.

## CI (GitHub Actions)

`.github/workflows/e2e-tests.yml`:

1. **unit** job: installs requirements, runs `pytest tests/unit --cov` (fails below 85% coverage), writes a results
   table to the job summary and uploads the JUnit / coverage / HTML files.
2. **e2e** job (`needs: unit`): builds the Docker image and runs `src/specs` inside it with
   `TWITCH_SKIP_UNIT_GATE=true` (the unit job already did the gate), then writes a summary and uploads `reports/`.

Triggers: push to `main`, pull requests, nightly schedule, and manual dispatch with inputs for search term, device,
tags (a `-m` expression) and video policy.

## Test conventions

- `--strict-markers --strict-config`: unregistered markers / config keys fail fast.
- `filterwarnings = error`: any new warning fails the run.
- `timeout = 60` per test (pytest-timeout); slow scenarios opt in with `@pytest.mark.timeout(900)`.
- Shared setup lives in fixtures; parametrized cases carry readable `ids`.
- Tests are auto-marked by location (`tests/unit` -> `unit`, `src/specs` -> `e2e`); use `smoke` / `regression` for
  selection.

## Known limitations

- **Selectors depend on Twitch's current mobile-web DOM** (for example, the player lives in an iframe and result
  cards are buttons). Each locator has fallbacks, but a redesign may still need locator updates.
- **Running locally can be much slower than in Docker.** On a heavily loaded machine Twitch's JavaScript keeps the
  browser busy for 20+ seconds after load, which blocks WebDriver commands. If scenarios time out locally, raise
  `TWITCH_TIMEOUT` (for example `60`) or run through Docker.
- **Pop-ups depend on the visitor's region.** CI runners (data-centre IPs) can see consent banners that a local run
  does not (for example the purple "Cookies and Advertising Choices" bottom banner with a **Proceed** button, which
  covers the bottom navigation and is handled by `ModalHandler`). `ModalHandler` handles known pop-ups; when a click is intercepted by an unknown overlay it also looks for
  an accept-like button ("Accept all", "I agree", "OK", ...) inside the overlay and clicks it. If nothing matches, the
  overlay's HTML is written to the log (look for `covered by an unrecognised overlay`), and on failure the page HTML is
  saved next to the screenshot (`reports/screenshots/<test>.html`) so a new pop-up can be added to `DISMISS_LOCATORS`.
- The step recording is a GIF built from per-action frames, not a continuous video.
