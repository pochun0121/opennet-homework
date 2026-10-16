import base64
import types

import pytest

from src.constants.settings import Settings
from src.utils.junit_summary import summarize
from src.utils.report import apply_report_options, attach_artifacts, detect_stage, register_artifact


class FakeExtras:
    @staticmethod
    def html(content):
        return {"html": content}


def node_with(*items):
    node = types.SimpleNamespace()
    for label, path in items:
        register_artifact(node, path, label)
    return node


class TestAttachArtifacts:
    def test_embeds_png_and_gif_as_base64(self, tmp_path):
        png, gif = tmp_path / "a.png", tmp_path / "b.gif"
        png.write_bytes(b"PNGDATA")
        gif.write_bytes(b"GIFDATA")
        report = types.SimpleNamespace()
        count = attach_artifacts(report, node_with(("Screenshot", png), ("Recording", gif)), FakeExtras)
        assert count == 2
        first, second = (e["html"] for e in report.extras)
        assert f"data:image/png;base64,{base64.b64encode(b'PNGDATA').decode()}" in first
        assert f"data:image/gif;base64,{base64.b64encode(b'GIFDATA').decode()}" in second and "Recording" in second

    def test_renders_full_image_not_the_cropped_thumbnail(self, tmp_path):
        png = tmp_path / "a.png"
        png.write_bytes(b"x")
        report = types.SimpleNamespace()
        attach_artifacts(report, node_with(("Screenshot", png)), FakeExtras)
        markup = report.extras[0]["html"]
        assert markup.startswith("<div") and "<img" in markup and "height:auto" in markup and "onclick" in markup

    def test_missing_and_unknown_files_are_skipped(self, tmp_path):
        text = tmp_path / "log.txt"
        text.write_text("x")
        report = types.SimpleNamespace()
        assert attach_artifacts(report, node_with(("gone", tmp_path / "nope.png"), ("txt", text)), FakeExtras) == 0
        assert report.extras == []

    def test_keeps_existing_extras_and_handles_node_without_artifacts(self):
        report = types.SimpleNamespace(extras=["existing"])
        assert attach_artifacts(report, types.SimpleNamespace(), FakeExtras) == 0
        assert report.extras == ["existing"]


class TestDetectStage:
    @pytest.mark.parametrize(
        "args,expected",
        [
            (["tests/unit"], "unit"),
            (["tests/unit/test_env.py::TestPrecedence"], "unit"),
            (["src/specs"], "e2e"),
            (["src/specs/search/test_search_starcraft.py"], "e2e"),
            (["tests", "src/specs"], "all"),
            (["tests/unit", "src/specs"], "all"),
            ([], "all"),
            (["somewhere/else"], "all"),
        ],
        ids=["unit-dir", "unit-node", "specs-dir", "specs-file", "tests+specs", "unit+specs", "no-args", "unknown"],
    )
    def test_stage_from_selected_paths(self, tmp_path, args, expected):
        assert detect_stage(args, tmp_path) == expected


class TestApplyReportOptions:
    def _option(self, **kw):
        return types.SimpleNamespace(htmlpath=kw.get("htmlpath"), xmlpath=kw.get("xmlpath"), self_contained_html=False)

    def test_defaults_from_settings_resolved_against_root(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TWITCH_HTML_REPORT", raising=False)
        monkeypatch.setenv("TWITCH_JUNIT_XML", "reports/junit.xml")
        option = self._option()
        apply_report_options(option, Settings(), tmp_path)
        assert option.htmlpath == str(tmp_path / "reports" / "report-all.html") and option.self_contained_html
        assert option.xmlpath == str(tmp_path / "reports" / "junit.xml")

    def test_stage_placeholder_keeps_reports_apart(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TWITCH_HTML_REPORT", raising=False)
        unit, e2e = self._option(), self._option()
        apply_report_options(unit, Settings(), tmp_path, "unit")
        apply_report_options(e2e, Settings(), tmp_path, "e2e")
        assert unit.htmlpath == str(tmp_path / "reports" / "report-unit.html")
        assert e2e.htmlpath == str(tmp_path / "reports" / "report-e2e.html")

    def test_cli_values_win(self, tmp_path):
        option = self._option(htmlpath="mine.html", xmlpath="mine.xml")
        apply_report_options(option, Settings(), tmp_path)
        assert (option.htmlpath, option.xmlpath) == ("mine.html", "mine.xml")

    def test_empty_values_turn_reports_off(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TWITCH_HTML_REPORT", "")
        monkeypatch.setenv("TWITCH_JUNIT_XML", "")
        option = self._option()
        apply_report_options(option, Settings(), tmp_path)
        assert option.htmlpath is None and option.xmlpath is None

    def test_plugin_missing_is_tolerated(self, tmp_path):
        option = types.SimpleNamespace()  # neither pytest-html nor junitxml options present
        apply_report_options(option, Settings(), tmp_path)


class TestJunitSummary:
    XML = (
        '<testsuites><testsuite tests="3" failures="1" errors="0" skipped="1" time="2.5">'
        '<testcase classname="a.b" name="ok"/>'
        '<testcase classname="a.b" name="bad"><failure message="x"/></testcase>'
        '<testcase classname="a.b" name="skipped"><skipped/></testcase>'
        "</testsuite></testsuites>"
    )

    def test_table_and_failed_list(self, tmp_path):
        f = tmp_path / "r.xml"
        f.write_text(self.XML)
        md = summarize(f, "Unit")
        assert "### Unit" in md and "| 3 | 1 | 1 | 0 | 1 | 2.5s |" in md and "`a.b::bad`" in md

    def test_missing_file(self, tmp_path):
        assert "No JUnit report" in summarize(tmp_path / "none.xml")
