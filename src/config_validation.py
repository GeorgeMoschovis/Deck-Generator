"""
config_validation.py
--------------------
Validate fund YAML before network calls or heavy work.
"""

from __future__ import annotations

import re
from typing import Any

from src.slide_variants import SLIDE_ORDER

_HEX6 = re.compile(r"^[0-9A-Fa-f]{6}$")

REQUIRED_FUND_KEYS: tuple[str, ...] = (
    "name",
    "legal_name",
    "strategy",
    "base_currency",
    "inception_date",
)

REQUIRED_RISK_KEYS: tuple[str, ...] = (
    "var_confidence",
    "var_lookback_days",
    "risk_free_rate",
)

BRANDING_HEX_KEYS: tuple[str, ...] = (
    "primary_color",
    "secondary_color",
    "accent_color",
    "positive_color",
    "negative_color",
    "surface_color",
    "border_color",
    "text_light",
    "bg_dark",
    "bg_light",
    "text_dark",
    "text_muted",
)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base (override wins)."""
    out: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def validate_config(config: dict[str, Any]) -> None:
    """
    Raise ValueError with a clear message if config is invalid or incomplete.
    """
    if not isinstance(config, dict):
        raise ValueError("Config must be a mapping (YAML object).")

    fund = config.get("fund")
    if not isinstance(fund, dict):
        raise ValueError("Config missing required section: fund (object).")

    missing_fund = [k for k in REQUIRED_FUND_KEYS if not fund.get(k)]
    if missing_fund:
        raise ValueError(
            "Config fund section missing or empty keys: " + ", ".join(missing_fund)
        )

    slides = config.get("slides")
    if not isinstance(slides, dict):
        raise ValueError("Config missing required section: slides (object).")

    for key in SLIDE_ORDER:
        if key not in slides:
            raise ValueError(
                f"Config slides section missing key: {key!r} (expected boolean for each slide)."
            )
        if not isinstance(slides[key], bool):
            raise ValueError(f"Config slides.{key} must be a boolean, got {type(slides[key]).__name__}.")

    risk = config.get("risk")
    if not isinstance(risk, dict):
        raise ValueError("Config missing required section: risk (object).")

    missing_risk = [k for k in REQUIRED_RISK_KEYS if k not in risk]
    if missing_risk:
        raise ValueError("Config risk section missing keys: " + ", ".join(missing_risk))

    branding = config.get("branding")
    if not isinstance(branding, dict):
        raise ValueError("Config missing required section: branding (object).")

    for key in BRANDING_HEX_KEYS:
        val = branding.get(key)
        if not isinstance(val, str) or not _HEX6.match(val.strip()):
            raise ValueError(
                f"Config branding.{key} must be a 6-character hex string (e.g. 1E2761), got {val!r}."
            )

    for key in ("font_heading", "font_body"):
        if not isinstance(branding.get(key), str) or not str(branding[key]).strip():
            raise ValueError(f"Config branding.{key} must be a non-empty string.")

    if not isinstance(config.get("disclaimer_text"), str):
        raise ValueError("Config disclaimer_text must be a string.")
