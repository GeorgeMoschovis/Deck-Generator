from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from src.config_validation import deep_merge, validate_config


def _valid_base() -> dict:
    path = Path(__file__).resolve().parents[1] / "config" / "fund_config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_validate_config_accepts_default_fund_yaml() -> None:
    validate_config(_valid_base())


def test_validate_config_rejects_missing_fund_name() -> None:
    cfg = copy.deepcopy(_valid_base())
    cfg["fund"].pop("name")
    with pytest.raises(ValueError, match="fund section missing"):
        validate_config(cfg)


def test_validate_config_rejects_invalid_branding_hex() -> None:
    cfg = copy.deepcopy(_valid_base())
    cfg["branding"]["primary_color"] = "GGGGGG"
    with pytest.raises(ValueError, match="branding.primary_color"):
        validate_config(cfg)


def test_deep_merge_nested() -> None:
    base = {"a": 1, "slides": {"title": True, "disclaimer": True, "risk_metrics": True}}
    over = {"slides": {"title": False}}
    merged = deep_merge(base, over)
    assert merged["a"] == 1
    assert merged["slides"]["title"] is False
    assert merged["slides"]["disclaimer"] is True
    assert merged["slides"]["risk_metrics"] is True
