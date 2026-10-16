"""Reporting helpers: pytest-html (live viewing) and JUnit XML (CI).

Kept free of pytest hooks so they can be unit tested; conftest.py wires them in.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

IMAGE_HTML = (
    '<div style="margin:6px 0"><div style="font-size:12px;color:#666">{label} (click to enlarge)</div>'
    '<img alt="{label}" src="data:{mime};base64,{content}" '
    'style="width:320px;max-width:100%;height:auto;border:1px solid #ccc;cursor:zoom-in" '
    "onclick=\"this.style.width = this.style.width === '100%' ? '320px' : '100%'\"></div>"
)
IMAGE_TYPES = {".png": ("image/png", "png"), ".gif": ("image/gif", "gif"), ".jpg": ("image/jpeg", "jpg")}


def register_artifact(node: Any, path: Path | str, label: str) -> None:
    """Remember a file produced during a test so the HTML report can embed it."""
    if not hasattr(node, "e2e_artifacts"):
        node.e2e_artifacts = []
    node.e2e_artifacts.append((label, Path(path)))


def attach_artifacts(report: Any, node: Any, html_extras: Any) -> int:
    """Append the registered images to `report.extras` (pytest-html format). Returns how many were embedded."""
    embedded = 0
    extras = list(getattr(report, "extras", []))
    for label, path in getattr(node, "e2e_artifacts", []):
        mime, ext = IMAGE_TYPES.get(path.suffix.lower(), (None, None))
        if mime is None or not path.is_file():
            continue
        # base64 content keeps the report self-contained (one file, shareable as is).
        # The default pytest-html thumbnail is a 320x200 center crop, which shows only the blank middle of a tall
        # phone screenshot, so render the whole image instead (click to toggle full width).
        content = base64.b64encode(path.read_bytes()).decode("ascii")
        extras.append(html_extras.html(IMAGE_HTML.format(label=label, mime=mime, content=content)))
        embedded += 1
    report.extras = extras
    return embedded


def detect_stage(args: list[str], root: Path) -> str:
    """Name the run by what was selected: 'unit' (tests/unit), 'e2e' (src/specs) or 'all' (anything else / mixed)."""
    kinds = set()
    for arg in args:
        path = Path(arg.split("::", 1)[0])
        parts = (path if path.is_absolute() else root / path).parts
        kinds.add("unit" if "unit" in parts else "e2e" if "specs" in parts else "other")
    return kinds.pop() if len(kinds) == 1 and kinds != {"other"} else "all"


def apply_report_options(option: Any, settings: Any, root: Path, stage: str = "all") -> None:
    """Fill in --html / --junitxml from settings unless they were given on the command line.

    A `{stage}` placeholder in the configured path is replaced by unit / e2e / all, so reports never overwrite each other.
    """

    def _resolve(value: str) -> str:
        path = Path(value.replace("{stage}", stage)).expanduser()
        return str(path if path.is_absolute() else root / path)

    if settings.html_report and hasattr(option, "htmlpath") and not option.htmlpath:
        option.htmlpath = _resolve(settings.html_report)
        option.self_contained_html = True
    if settings.junit_xml and hasattr(option, "xmlpath") and not option.xmlpath:
        option.xmlpath = _resolve(settings.junit_xml)
