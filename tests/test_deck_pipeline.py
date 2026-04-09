from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pptx import Presentation

from src.deck_pipeline import generate_deck


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def mock_yf_download(monkeypatch: pytest.MonkeyPatch) -> None:
    def _mock_download(tickers, *args, **kwargs) -> pd.DataFrame:
        tickers_list = list(tickers) if not isinstance(tickers, str) else [tickers]
        index = pd.date_range("2025-01-01", periods=260, freq="B")
        values = np.tile(np.linspace(100.0, 120.0, len(index)).reshape(-1, 1), (1, len(tickers_list)))
        columns = pd.MultiIndex.from_product([["Close"], tickers_list], names=["Price", "Ticker"])
        return pd.DataFrame(values, index=index, columns=columns)

    monkeypatch.setattr("src.data_loader.yf.download", _mock_download)


def test_generate_deck_sector_split_variant(
    mock_yf_download: None,
    tmp_path: Path,
    project_root: Path,
) -> None:
    holdings_path = project_root / "data" / "sample_holdings.csv"
    config_path = project_root / "config" / "fund_config.yaml"
    output_path = tmp_path / "pipeline_split.pptx"
    chart_dir = tmp_path / "charts"

    out = generate_deck(
        holdings_path=holdings_path,
        config_path=config_path,
        report_date="2026-03-31",
        aum="EUR 100M",
        output_path=output_path,
        chart_dir=chart_dir,
        enabled_slides=None,
        slide_variants={"exposure_sector": "split", "exposure_geography": "net_bars"},
        price_snapshot_path=None,
        template_path=None,
        pipeline_warnings=None,
    )

    assert out == output_path
    assert output_path.is_file()
    prs = Presentation(str(output_path))
    assert len(prs.slides) >= 1


def test_generate_deck_pipeline_warnings_list_mutable(
    mock_yf_download: None,
    tmp_path: Path,
    project_root: Path,
) -> None:
    warnings_list: list[str] = []
    holdings_path = project_root / "data" / "sample_holdings.csv"
    config_path = project_root / "config" / "fund_config.yaml"
    generate_deck(
        holdings_path=holdings_path,
        config_path=config_path,
        report_date="2026-03-31",
        aum="EUR 1",
        output_path=tmp_path / "out.pptx",
        chart_dir=tmp_path / "c",
        pipeline_warnings=warnings_list,
    )
    assert isinstance(warnings_list, list)
