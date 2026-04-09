"""
slide_variants.py
-----------------
Human-readable labels and defaults for per-slide layout choices (CLI + UI).
"""

from __future__ import annotations

from typing import Any, TypedDict


class VariantOption(TypedDict):
    id: str
    label: str
    description: str


# Slides that support 2–3 layout alternatives in the UI / pipeline.
SLIDE_VARIANT_GROUPS: dict[str, list[VariantOption]] = {
    "performance_summary": [
        {
            "id": "simple",
            "label": "Simple",
            "description": "KPI boxes only — fastest to scan; no performance charts.",
        },
        {
            "id": "standard",
            "label": "Standard",
            "description": "KPIs plus cumulative return and drawdown charts (default).",
        },
        {
            "id": "detailed",
            "label": "Detailed",
            "description": "Same charts as standard with larger chart area for readability.",
        },
    ],
    "exposure_sector": [
        {
            "id": "net_bars",
            "label": "Net bars",
            "description": "Horizontal bar chart of net exposure + summary table.",
        },
        {
            "id": "pie_gross",
            "label": "Gross pie",
            "description": "Pie chart of gross weights + summary table.",
        },
        {
            "id": "split",
            "label": "Split view",
            "description": "Net bars and gross pie side by side + table.",
        },
    ],
    "exposure_geography": [
        {
            "id": "table_only",
            "label": "Table only",
            "description": "Gross and net % by geography — no chart (avoids overlap with the summary table).",
        },
        {
            "id": "net_bars",
            "label": "Net bars + table",
            "description": "Horizontal bar chart of net exposure plus the summary table on the right.",
        },
        {
            "id": "pie_gross",
            "label": "Gross pie",
            "description": "Pie chart of gross weights by geography plus the summary table.",
        },
        {
            "id": "split",
            "label": "Split view",
            "description": "Net bars and gross pie side by side plus the summary table.",
        },
    ],
    "top_positions": [
        {
            "id": "simple",
            "label": "Simple",
            "description": "Top 3 longs and shorts.",
        },
        {
            "id": "standard",
            "label": "Standard",
            "description": "Top 5 longs and shorts (default).",
        },
        {
            "id": "detailed",
            "label": "Detailed",
            "description": "Top 8 longs and shorts.",
        },
    ],
}

DEFAULT_VARIANTS: dict[str, str] = {
    "performance_summary": "standard",
    "exposure_sector": "net_bars",
    "exposure_geography": "table_only",
    "top_positions": "standard",
}

# Fixed order when assembling the deck (only slides that are enabled are added).
SLIDE_ORDER: tuple[str, ...] = (
    "title",
    "performance_summary",
    "exposure_sector",
    "exposure_geography",
    "top_positions",
    "risk_metrics",
    "attribution",
    "disclaimer",
)


def normalize_variants(user: dict[str, str] | None) -> dict[str, str]:
    """Merge user choices with defaults; ignore unknown keys."""
    out = dict(DEFAULT_VARIANTS)
    if user:
        for key, value in user.items():
            if key in DEFAULT_VARIANTS and value:
                allowed = {o["id"] for o in SLIDE_VARIANT_GROUPS.get(key, [])}
                if value in allowed:
                    out[key] = value
    return out


def default_enabled_slides(config: dict[str, Any]) -> dict[str, bool]:
    """Start from config['slides'] booleans; safe for missing keys."""
    slides = config.get("slides") or {}
    return {key: bool(slides.get(key, False)) for key in SLIDE_ORDER}
