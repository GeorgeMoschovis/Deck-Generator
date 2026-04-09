"""
Shared fixtures: avoid live FX calls during tests (portfolio uses multiple currencies).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _patch_fx_rates_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.data_loader.fetch_fx_to_base_rate",
        lambda _from_ccy, _base_ccy: 1.0,
    )
