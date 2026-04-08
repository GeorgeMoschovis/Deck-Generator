from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.analytics import (
    compute_portfolio_returns,
    exposure_by_field,
    performance_table,
    pnl_attribution,
    risk_metrics,
)


def test_compute_portfolio_returns_handles_long_short_and_duplicate_tickers() -> None:
    holdings = pd.DataFrame(
        [
            {"ticker": "AAPL", "side": "LONG", "weight_gross": 0.40},
            {"ticker": "AAPL", "side": "SHORT", "weight_gross": 0.10},
            {"ticker": "MSFT", "side": "SHORT", "weight_gross": 0.50},
        ]
    )
    prices = pd.DataFrame(
        {
            "AAPL": [100.0, 110.0, 99.0],
            "MSFT": [50.0, 45.0, 54.0],
        },
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )

    returns = compute_portfolio_returns(holdings, prices)
    expected = pd.Series([0.08, -0.13], index=prices.index[1:], name="portfolio_return")
    pd.testing.assert_series_equal(returns, expected)


def test_compute_portfolio_returns_returns_empty_without_overlap() -> None:
    holdings = pd.DataFrame([{"ticker": "NVDA", "side": "LONG", "weight_gross": 1.0}])
    prices = pd.DataFrame({"AAPL": [100.0, 101.0]}, index=pd.date_range("2026-01-01", periods=2, freq="D"))
    returns = compute_portfolio_returns(holdings, prices)
    assert returns.empty


def test_performance_table_returns_zeroes_for_empty_series() -> None:
    perf = performance_table(pd.Series(dtype="float64"))
    assert perf == {"MTD": 0.0, "QTD": 0.0, "YTD": 0.0, "ITD": 0.0}


def test_risk_metrics_handles_empty_and_zero_volatility_inputs() -> None:
    empty_metrics = risk_metrics(pd.Series(dtype="float64"))
    assert empty_metrics == {
        "VaR (Parametric)": 0.0,
        "VaR (Historical)": 0.0,
        "Sharpe Ratio": 0.0,
        "Sortino Ratio": 0.0,
        "Max Drawdown": 0.0,
        "Annualised Volatility": 0.0,
    }

    flat_returns = pd.Series([0.01, 0.01, 0.01, 0.01], dtype="float64")
    flat_metrics = risk_metrics(flat_returns, confidence=0.95, rfr=0.0)
    assert flat_metrics["Sharpe Ratio"] == 0.0
    assert flat_metrics["Sortino Ratio"] == 0.0
    assert flat_metrics["Max Drawdown"] == 0.0
    assert flat_metrics["Annualised Volatility"] == 0.0


def test_risk_metrics_deterministic_values_for_small_series() -> None:
    returns = pd.Series([0.01, -0.02, 0.015, -0.005], dtype="float64")
    metrics = risk_metrics(returns, confidence=0.95, rfr=0.0)

    vol = float(returns.std(ddof=0))
    downside_dev = float(np.sqrt(np.mean(np.square(np.minimum(returns, 0.0)))))
    max_dd = float((((1 + returns).cumprod() - (1 + returns).cumprod().cummax()) / (1 + returns).cumprod().cummax()).min())
    expected = {
        "VaR (Parametric)": round((float(returns.mean()) + stats.norm.ppf(0.05) * vol) * 100, 2),
        "VaR (Historical)": round(float(returns.quantile(0.05)) * 100, 2),
        "Sharpe Ratio": round((float(returns.mean()) / vol) * np.sqrt(252), 2),
        "Sortino Ratio": round((float(returns.mean()) / downside_dev) * np.sqrt(252), 2),
        "Max Drawdown": round(max_dd * 100, 2),
        "Annualised Volatility": round(vol * np.sqrt(252) * 100, 2),
    }
    for key, value in expected.items():
        assert metrics[key] == pytest.approx(value, abs=0.02)


def test_exposure_by_field_uses_gross_baseline_and_handles_missing_groups() -> None:
    holdings = pd.DataFrame(
        [
            {"sector": "Tech", "market_value": 100.0},
            {"sector": "Tech", "market_value": -50.0},
            {"sector": None, "market_value": 50.0},
        ]
    )

    exposure = exposure_by_field(holdings, "sector")
    assert set(exposure.index.tolist()) == {"Tech", "Unspecified"}
    assert exposure["gross_weight"].sum() == 100.0
    assert exposure.loc["Tech", "gross_weight"] == 75.0
    assert exposure.loc["Unspecified", "gross_weight"] == 25.0
    assert exposure.loc["Tech", "net_weight"] == 25.0
    assert exposure.loc["Unspecified", "net_weight"] == 25.0


def test_exposure_and_attribution_handle_zero_baseline() -> None:
    zero_holdings = pd.DataFrame(
        [
            {"sector": "Tech", "market_value": 0.0, "cost_basis": 0.0, "pnl": 2.0},
            {"sector": "Health", "market_value": 0.0, "cost_basis": 0.0, "pnl": -1.0},
        ]
    )

    exposure = exposure_by_field(zero_holdings, "sector")
    attribution = pnl_attribution(zero_holdings, "sector")
    assert (exposure["gross_weight"] == 0.0).all()
    assert (exposure["net_weight"] == 0.0).all()
    assert (attribution["pnl_contribution_pct"] == 0.0).all()


def test_pnl_attribution_contributions_use_portfolio_gross_cost_baseline() -> None:
    holdings = pd.DataFrame(
        [
            {"sector": "Tech", "pnl": 10.0, "cost_basis": 100.0},
            {"sector": "Tech", "pnl": -5.0, "cost_basis": -50.0},
            {"sector": None, "pnl": 5.0, "cost_basis": 50.0},
        ]
    )

    attribution = pnl_attribution(holdings, "sector")
    assert set(attribution.index.tolist()) == {"Tech", "Unspecified"}
    assert attribution["total_pnl"].sum() == 10.0
    assert attribution.loc["Tech", "pnl_contribution_pct"] == 2.5
    assert attribution.loc["Unspecified", "pnl_contribution_pct"] == 2.5
    assert attribution["pnl_contribution_pct"].sum() == 5.0
