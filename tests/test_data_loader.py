from __future__ import annotations

import pandas as pd
import pytest

from src.data_loader import ENRICHED_HOLDINGS_COLUMNS, enrich_holdings, fetch_prices, load_holdings


def _write_holdings_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False)


def test_load_holdings_raises_on_missing_required_columns(tmp_path) -> None:
    csv_path = tmp_path / "missing_cols.csv"
    _write_holdings_csv(
        csv_path,
        [
            {
                "ticker": "AAPL",
                "quantity": 10,
                "avg_cost": 100.0,
                "currency": "USD",
                "sector": "Tech",
                "country": "US",
                "side": "LONG",
            }
        ],
    )

    with pytest.raises(ValueError, match="strategy_sleeve"):
        load_holdings(csv_path)


def test_load_holdings_drops_invalid_tickers_and_warns(tmp_path) -> None:
    csv_path = tmp_path / "invalid_tickers.csv"
    _write_holdings_csv(
        csv_path,
        [
            {
                "ticker": "AAPL",
                "quantity": 10,
                "avg_cost": 100.0,
                "currency": "USD",
                "sector": "Tech",
                "country": "US",
                "strategy_sleeve": "Core",
                "side": "long",
            },
            {
                "ticker": "   ",
                "quantity": 5,
                "avg_cost": 80.0,
                "currency": "USD",
                "sector": "Tech",
                "country": "US",
                "strategy_sleeve": "Core",
                "side": "short",
            },
        ],
    )

    with pytest.warns(RuntimeWarning, match="missing/invalid tickers"):
        loaded = load_holdings(csv_path)

    assert loaded["ticker"].tolist() == ["AAPL"]
    assert loaded["side"].tolist() == ["LONG"]
    assert loaded.attrs["ingestion_report"]["dropped_invalid_ticker_rows"] == 1


def test_fetch_prices_warns_and_returns_empty_on_all_nan_close(monkeypatch) -> None:
    def _mock_download(*args, **kwargs) -> pd.DataFrame:
        index = pd.date_range("2026-01-01", periods=3, freq="D")
        return pd.DataFrame({"Close": [float("nan"), float("nan"), float("nan")]}, index=index)

    monkeypatch.setattr("src.data_loader.yf.download", _mock_download)

    with pytest.warns(RuntimeWarning, match="Price history contains no usable close prices"):
        prices = fetch_prices(["AAPL"])

    assert prices.empty
    assert prices.attrs["price_report"]["valid_tickers"] == ["AAPL"]
    assert prices.attrs["price_report"]["unresolved_price_history"] == ["AAPL"]


def test_fetch_prices_returns_empty_for_no_valid_tickers() -> None:
    with pytest.warns(RuntimeWarning, match="No valid tickers provided"):
        prices = fetch_prices([" ", "", "\t"])

    assert prices.empty


def test_fetch_prices_deduplicates_tickers_in_download_call(monkeypatch) -> None:
    captured: dict[str, list[str]] = {}

    def _mock_download(tickers, *args, **kwargs) -> pd.DataFrame:
        captured["tickers"] = list(tickers)
        index = pd.date_range("2026-01-01", periods=2, freq="D")
        columns = pd.MultiIndex.from_tuples(
            [("Close", "AAPL"), ("Close", "MSFT")],
            names=["Price", "Ticker"],
        )
        return pd.DataFrame([[100.0, 200.0], [101.0, 201.0]], index=index, columns=columns)

    monkeypatch.setattr("src.data_loader.yf.download", _mock_download)

    prices = fetch_prices([" AAPL ", "MSFT", "AAPL"])
    assert captured["tickers"] == ["AAPL", "MSFT"]
    assert prices.columns.tolist() == ["AAPL", "MSFT"]


def test_enrich_holdings_drops_unresolved_and_preserves_enriched_schema() -> None:
    holdings = pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "quantity": 10,
                "avg_cost": 100.0,
                "currency": "USD",
                "sector": "Tech",
                "country": "US",
                "strategy_sleeve": "Core",
                "side": "LONG",
            },
            {
                "ticker": "BAD",
                "quantity": 3,
                "avg_cost": 50.0,
                "currency": "USD",
                "sector": "Tech",
                "country": "US",
                "strategy_sleeve": "Core",
                "side": "LONG",
            },
        ]
    )
    prices = pd.DataFrame({"AAPL": [105.0]})

    with pytest.warns(RuntimeWarning, match="unresolved prices"):
        enriched = enrich_holdings(holdings, prices)

    assert enriched["ticker"].tolist() == ["AAPL"]
    assert set(ENRICHED_HOLDINGS_COLUMNS).issubset(enriched.columns)
    assert enriched.attrs["enrichment_report"]["unresolved_tickers"] == ["BAD"]


def test_enrich_holdings_returns_empty_with_required_columns_when_all_unresolved() -> None:
    holdings = pd.DataFrame(
        [
            {
                "ticker": "BAD1",
                "quantity": 10,
                "avg_cost": 100.0,
                "currency": "USD",
                "sector": "Tech",
                "country": "US",
                "strategy_sleeve": "Core",
                "side": "LONG",
            }
        ]
    )
    prices = pd.DataFrame()

    with pytest.warns(RuntimeWarning, match="unresolved prices"):
        enriched = enrich_holdings(holdings, prices)

    assert enriched.empty
    assert set(ENRICHED_HOLDINGS_COLUMNS).issubset(enriched.columns)
