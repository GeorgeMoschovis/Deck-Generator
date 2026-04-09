"""Package version for CLI, Streamlit, and other entry points."""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, version as pkg_version
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def package_version() -> str:
    """Version from installed metadata, else ``pyproject.toml`` at repo root."""
    try:
        return pkg_version("fund-deck-generator")
    except PackageNotFoundError:
        pass
    pyproject = _REPO_ROOT / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if m:
            return m.group(1)
    return "0.0.0"
