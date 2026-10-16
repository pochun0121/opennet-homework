import pytest

from src.constants.env import get_bool, get_env, parse_env_file
from src.constants.settings import Settings


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    path = tmp_path / "test.env"
    monkeypatch.setenv("TWITCH_ENV_FILE", str(path))
    return path


class TestParseEnvFile:
    def test_missing_file_gives_empty_dict(self, tmp_path):
        assert parse_env_file(tmp_path / "nope.env") == {}

    def test_parses_comments_quotes_export_and_inline_comments(self, tmp_path):
        f = tmp_path / "a.env"
        f.write_text(
            "# comment\n\nA=1\nexport B=two\nC=\"with space\"\nD='single'\nE=value # trailing\nF=\"keep # hash\"\nnot a pair\n"
        )
        assert parse_env_file(f) == {"A": "1", "B": "two", "C": "with space", "D": "single", "E": "value", "F": "keep # hash"}


class TestPrecedence:
    def test_default_when_nothing_set(self, env_file, monkeypatch):
        monkeypatch.delenv("TWITCH_X", raising=False)
        assert get_env("TWITCH_X", "dflt") == "dflt"

    def test_file_beats_default(self, env_file, monkeypatch):
        monkeypatch.delenv("TWITCH_X", raising=False)
        env_file.write_text("TWITCH_X=from_file\n")
        assert get_env("TWITCH_X", "dflt") == "from_file"

    def test_real_env_beats_file(self, env_file, monkeypatch):
        env_file.write_text("TWITCH_X=from_file\n")
        monkeypatch.setenv("TWITCH_X", "from_env")
        assert get_env("TWITCH_X", "dflt") == "from_env"

    @pytest.mark.parametrize("raw,expected", [("true", True), ("1", True), ("YES", True), ("false", False), ("0", False), ("", False)],
        ids=["true", "one", "yes_upper", "false", "zero", "empty"],
    )
    def test_get_bool(self, monkeypatch, raw, expected):
        monkeypatch.setenv("TWITCH_B", raw)
        assert get_bool("TWITCH_B", True) is expected


class TestSettingsFromFile:
    def test_all_run_options_come_from_env_file(self, env_file, monkeypatch):
        for key in ("TWITCH_HEADLESS", "TWITCH_NO_SANDBOX", "TWITCH_TAGS", "TWITCH_VIDEO_POLICY", "TWITCH_TIMEOUT"):
            monkeypatch.delenv(key, raising=False)
        env_file.write_text(
            "TWITCH_HEADLESS=true\nTWITCH_NO_SANDBOX=true\nTWITCH_TAGS=smoke and not slow\n"
            "TWITCH_VIDEO_POLICY=always\nTWITCH_TIMEOUT=30\n"
        )
        s = Settings()
        assert s.headless and s.no_sandbox
        assert s.tags == "smoke and not slow" and s.video_policy == "always" and s.timeout == 30.0

    def test_defaults(self, monkeypatch):
        for key in ("TWITCH_HEADLESS", "TWITCH_TAGS", "TWITCH_SCREENSHOT_POLICY", "TWITCH_VIDEO_POLICY", "TWITCH_SKIP_UNIT_GATE"):
            monkeypatch.delenv(key, raising=False)
        s = Settings()
        assert not s.headless and s.tags == "" and not s.skip_unit_gate
        assert (s.screenshot_policy, s.video_policy) == ("on-failure", "on-failure")
