from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pptx import Presentation

import generate_deck


def test_cli_version_exits_zero(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["generate_deck.py", "--version"])
    with pytest.raises(SystemExit) as exc:
        generate_deck.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert re.match(r"fund-deck \d+\.\d+\.\d+\s*$", out.strip())


def test_cli_smoke_generates_pptx(monkeypatch, tmp_path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    holdings_path = project_root / "data" / "sample_holdings.csv"
    config_path = project_root / "config" / "fund_config.yaml"
    output_path = tmp_path / "smoke_report.pptx"

    def _mock_download(tickers, *args, **kwargs) -> pd.DataFrame:
        tickers_list = list(tickers)
        index = pd.date_range("2025-01-01", periods=260, freq="B")
        values = np.tile(np.linspace(100.0, 120.0, len(index)).reshape(-1, 1), (1, len(tickers_list)))
        columns = pd.MultiIndex.from_product([["Close"], tickers_list], names=["Price", "Ticker"])
        return pd.DataFrame(values, index=index, columns=columns)

    monkeypatch.setattr("src.data_loader.yf.download", _mock_download)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_deck.py",
            "--holdings",
            str(holdings_path),
            "--config",
            str(config_path),
            "--date",
            "2026-03-31",
            "--output",
            str(output_path),
            "--aum",
            "EUR 125.4M",
        ],
    )

    generate_deck.main()

    assert output_path.exists()
    assert output_path.stat().st_size > 0

    prs = Presentation(str(output_path))
    assert len(prs.slides) >= 1
