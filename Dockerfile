# Debian's chromium + chromium-driver are versioned together and ship for amd64 and arm64,
# so the same image works on CI runners, Intel and Apple Silicon machines.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    TWITCH_HEADLESS=true \
    TWITCH_NO_SANDBOX=true

RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium chromium-driver fonts-liberation fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: unit tests first, e2e only if they pass (enforced by the gate in conftest.py)
ENTRYPOINT ["pytest"]
