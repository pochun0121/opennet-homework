"""Single place that resolves configuration values.

Precedence (highest first):
  1. real environment variables (shell, CI, `docker run -e / --env-file`)
  2. the `.env` file at the project root (or the file named by TWITCH_ENV_FILE)
  3. defaults declared in settings.py
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE_VAR = "TWITCH_ENV_FILE"
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def parse_env_file(path: Path | str) -> dict[str, str]:
    """Parse KEY=VALUE lines. Supports comments, blank lines, `export KEY=...` and quoted values."""
    values: dict[str, str] = {}
    path = Path(path)
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:  # inline comment (only for unquoted values)
            value = value.split(" #", 1)[0].rstrip()
        values[key.strip()] = value
    return values


def _env_file_path() -> Path:
    return Path(os.environ.get(ENV_FILE_VAR) or ROOT_DIR / ".env")


def get_env(name: str, default: str = "") -> str:
    if name in os.environ:
        return os.environ[name]
    return parse_env_file(_env_file_path()).get(name, default)


def get_bool(name: str, default: bool) -> bool:
    return get_env(name, str(default)).strip().lower() in TRUE_VALUES
