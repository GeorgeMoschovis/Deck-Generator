from __future__ import annotations

import re
from pathlib import Path


def test_package_version_matches_declared_version() -> None:
    from src.package_version import package_version

    project_root = Path(__file__).resolve().parents[1]
    text = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m is not None
    expected = m.group(1)
    assert package_version() == expected
