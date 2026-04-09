from __future__ import annotations

from src.slide_variants import DEFAULT_VARIANTS, normalize_variants


def test_normalize_variants_merges_and_ignores_unknown() -> None:
    out = normalize_variants(
        {
            "performance_summary": "simple",
            "bogus": "x",
            "exposure_sector": "not_a_real_variant",
        }
    )
    assert out["performance_summary"] == "simple"
    assert out["exposure_sector"] == DEFAULT_VARIANTS["exposure_sector"]
    assert out["top_positions"] == DEFAULT_VARIANTS["top_positions"]


def test_normalize_variants_accepts_geography_split() -> None:
    out = normalize_variants({"exposure_geography": "split"})
    assert out["exposure_geography"] == "split"
