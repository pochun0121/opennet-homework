"""Render a JUnit XML file as a Markdown table for the GitHub Actions job summary.

Usage:  python3 -m src.utils.junit_summary reports/unit-junit.xml "Unit tests" >> "$GITHUB_STEP_SUMMARY"
Standard library only, so it runs on a bare CI runner.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def summarize(path: Path | str, title: str = "Test results") -> str:
    path = Path(path)
    if not path.is_file():
        return f"### {title}\n\n_No JUnit report found at `{path}`._\n"
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    totals = {k: sum(int(s.get(k, 0)) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
    seconds = sum(float(s.get("time", 0)) for s in suites)
    passed = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    lines = [
        f"### {title}",
        "",
        "| Total | Passed | Failed | Errors | Skipped | Time |",
        "|---:|---:|---:|---:|---:|---:|",
        f"| {totals['tests']} | {passed} | {totals['failures']} | {totals['errors']} | {totals['skipped']} | {seconds:.1f}s |",
        "",
    ]
    failed = [
        f"- `{case.get('classname')}::{case.get('name')}`"
        for case in root.iter("testcase")
        if case.find("failure") is not None or case.find("error") is not None
    ]
    if failed:
        lines += ["**Failed tests**", "", *failed, ""]
    return "\n".join(lines)


if __name__ == "__main__":
    print(summarize(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Test results"))
