"""
analytics.py
------------
Portfolio analytics: performance, risk metrics, exposures, attribution.
"""

import numpy as np
import pandas as pd
from scipy import stats


def compute_portfolio_returns(holdings: pd.DataFrame, prices: pd.DataFrame) -> pd.Series:
    """Compute daily portfolio returns from signed gross weights and price data."""
    if holdings.empty or prices.empty:
        return pd.Series(dtype="float64", name="portfolio_return")

    required_columns = {"ticker", "side", "weight_gross"}
    missing = required_columns - set(holdings.columns)
    if missing:
        raise ValueError(f"Holdings DataFrame missing required columns: {missing}")

    normalized = holdings.copy()
    normalized["side"] = normalized["side"].astype("string").str.strip().str.upper()
    normalized["weight_gross"] = pd.to_numeric(normalized["weight_gross"], errors="coerce").fillna(0.0)
    normalized["signed_weight"] = np.where(normalized["side"] == "SHORT", -1.0, 1.0) * normalized["weight_gross"]

    # Aggregate duplicate tickers so all sleeves/lines contribute to the same return stream.
    weights = normalized.groupby("ticker", dropna=True)["signed_weight"].sum()
    available = [ticker for ticker in weights.index if ticker in prices.columns]
    if not available:
        return pd.Series(dtype="float64", name="portfolio_return")

    asset_returns = prices[available].pct_change(fill_method=None)
    if asset_returns.empty:
        return pd.Series(dtype="float64", name="portfolio_return")
    asset_returns = asset_returns.dropna(how="all")
    if asset_returns.empty:
        return pd.Series(dtype="float64", name="portfolio_return")

    aligned_weights = weights.loc[available].astype(float)
    portfolio_returns = asset_returns.fillna(0.0).dot(aligned_weights)
    portfolio_returns.name = "portfolio_return"
    return portfolio_returns


def performance_table(returns: pd.Series, inception_date: str | None = None) -> dict:
    """
    Compute MTD, QTD, YTD, ITD performance stats.

    If ``inception_date`` is set (ISO ``YYYY-MM-DD``), ITD uses returns on or after that date only.
    """
    if returns.empty:
        return {"MTD": 0.0, "QTD": 0.0, "YTD": 0.0, "ITD": 0.0}

    returns = returns.dropna().sort_index()
    if returns.empty:
        return {"MTD": 0.0, "QTD": 0.0, "YTD": 0.0, "ITD": 0.0}

    today = returns.index[-1]
    inception_ts: pd.Timestamp | None = None
    if inception_date:
        try:
            inception_ts = pd.Timestamp(inception_date)
        except (ValueError, TypeError):
            inception_ts = None

    itd_series = returns
    if inception_ts is not None:
        itd_series = returns[returns.index >= inception_ts]

    periods = {
        "MTD": returns[returns.index >= today.replace(day=1)],
        "QTD": returns[returns.index >= pd.Timestamp(today.year, ((today.month - 1) // 3) * 3 + 1, 1)],
        "YTD": returns[returns.index >= pd.Timestamp(today.year, 1, 1)],
        "ITD": itd_series,
    }
    result = {}
    for label, r in periods.items():
        cum = (1 + r).prod() - 1
        result[label] = round(cum * 100, 2)
    return result


def risk_metrics(returns: pd.Series, confidence: float = 0.95, rfr: float = 0.035) -> dict:
    """Compute VaR, Sharpe, Sortino, max drawdown."""
    returns = returns.dropna().astype(float)
    if returns.empty:
        return {
            "VaR (Parametric)": 0.0,
            "VaR (Historical)": 0.0,
            "Sharpe Ratio": 0.0,
            "Sortino Ratio": 0.0,
            "Max Drawdown": 0.0,
            "Annualised Volatility": 0.0,
        }

    daily_rfr = (1 + rfr) ** (1 / 252) - 1
    excess = returns - daily_rfr

    mean_return = float(returns.mean())
    volatility = float(returns.std(ddof=0))
    downside_deviation = float(np.sqrt(np.mean(np.square(np.minimum(excess, 0.0)))))

    # VaR
    var_parametric = mean_return + stats.norm.ppf(1 - confidence) * volatility
    var_historical = float(returns.quantile(1 - confidence))

    # Sharpe & Sortino
    excess_mean = float(excess.mean())
    sharpe = excess_mean / volatility * np.sqrt(252) if volatility > 0 else 0.0
    sortino = excess_mean / downside_deviation * np.sqrt(252) if downside_deviation > 0 else 0.0

    # Max drawdown
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_dd = float(drawdown.min()) if not drawdown.empty else 0.0

    return {
        "VaR (Parametric)": round(var_parametric * 100, 2),
        "VaR (Historical)": round(var_historical * 100, 2),
        "Sharpe Ratio": round(sharpe, 2),
        "Sortino Ratio": round(sortino, 2),
        "Max Drawdown": round(max_dd * 100, 2),
        "Annualised Volatility": round(volatility * np.sqrt(252) * 100, 2),
    }


def exposure_by_field(holdings: pd.DataFrame, field: str) -> pd.DataFrame:
    """Compute gross and net exposure by a given field (sector, country, etc.)."""
    grouped = holdings.copy()
    grouped[field] = grouped[field].fillna("Unspecified")
    grouped = grouped.groupby(field).agg(
        long_exposure=("market_value", lambda x: x[x > 0].sum()),
        short_exposure=("market_value", lambda x: x[x < 0].sum()),
    )
    grouped["gross_exposure"] = grouped["long_exposure"] + grouped["short_exposure"].abs()
    grouped["net_exposure"] = grouped["long_exposure"] + grouped["short_exposure"]
    total_gross = grouped["gross_exposure"].sum()
    if total_gross == 0:
        grouped["gross_weight"] = 0.0
        grouped["net_weight"] = 0.0
    else:
        grouped["gross_weight"] = grouped["gross_exposure"] / total_gross * 100
        grouped["net_weight"] = grouped["net_exposure"] / total_gross * 100
    return grouped.sort_values("gross_weight", ascending=False)


def top_positions(holdings: pd.DataFrame, n: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return top N longs and top N shorts by absolute weight."""
    longs = holdings[holdings["side"] == "LONG"].nlargest(n, "weight_gross")
    shorts = holdings[holdings["side"] == "SHORT"].nlargest(n, "weight_gross")
    return longs, shorts


def pnl_attribution(holdings: pd.DataFrame, field: str = "sector") -> pd.DataFrame:
    """P&L attribution by sector or other grouping field."""
    normalized = holdings.copy()
    normalized[field] = normalized[field].fillna("Unspecified")
    attr = normalized.groupby(field).agg(
        total_pnl=("pnl", "sum"),
        total_cost=("cost_basis", lambda x: x.abs().sum()),
    )
    gross_cost_baseline = float(normalized["cost_basis"].abs().sum())
    if gross_cost_baseline == 0:
        attr["pnl_contribution_pct"] = 0.0
    else:
        attr["pnl_contribution_pct"] = attr["total_pnl"] / gross_cost_baseline * 100
    return attr.sort_values("total_pnl", ascending=False)
