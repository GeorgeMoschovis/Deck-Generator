"""
data_loader.py
--------------
Loads holdings CSV and enriches with live market data.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import warnings

import numpy as np
import pandas as pd
import yfinance as yf


REQUIRED_HOLDINGS_COLUMNS: tuple[str, ...] = (
    "ticker",
    "quantity",
    "avg_cost",
    "currency",
    "sector",
    "country",
    "strategy_sleeve",
    "side",
)

ENRICHED_HOLDINGS_COLUMNS: tuple[str, ...] = REQUIRED_HOLDINGS_COLUMNS + (
    "current_price",
    "market_value",
    "cost_basis",
    "weight_gross",
    "pnl",
    "pnl_pct",
)


def _build_invalid_ticker_mask(values: pd.Series) -> pd.Series:
    """Return a boolean mask for missing/blank ticker values."""
    as_text = values.astype("string")
    return as_text.isna() | (as_text.str.strip() == "")


def _normalize_ticker_list(tickers: Sequence[str]) -> list[str]:
    """Normalize, validate, and de-duplicate tickers while preserving order."""
    normalized: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        value = str(ticker).strip()
        if not value:
            continue
        if value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


def load_holdings(filepath: str | Path) -> pd.DataFrame:
    """Load holdings CSV, normalize schema, and drop rows with invalid tickers."""
    df = pd.read_csv(filepath)
    required_cols = set(REQUIRED_HOLDINGS_COLUMNS)
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Holdings CSV missing columns: {missing}")

    holdings = df.copy()
    holdings["side"] = holdings["side"].astype("string").str.strip().str.upper()
    holdings["ticker"] = holdings["ticker"].astype("string").str.strip()

    invalid_ticker_mask = _build_invalid_ticker_mask(holdings["ticker"])
    dropped_invalid = int(invalid_ticker_mask.sum())
    if dropped_invalid:
        warnings.warn(
            f"Dropping {dropped_invalid} holdings rows with missing/invalid tickers before price fetch.",
            RuntimeWarning,
            stacklevel=2,
        )
        holdings = holdings.loc[~invalid_ticker_mask].copy()

    holdings.attrs["ingestion_report"] = {
        "loaded_rows": int(len(df)),
        "dropped_invalid_ticker_rows": dropped_invalid,
        "remaining_rows": int(len(holdings)),
    }
    return holdings.reset_index(drop=True)


def fetch_prices(tickers: Sequence[str], lookback_days: int = 252) -> pd.DataFrame:
    """Fetch historical close prices from Yahoo Finance with resilient parsing."""
    valid_tickers = _normalize_ticker_list(tickers)
    if not valid_tickers:
        warnings.warn(
            "No valid tickers provided to fetch_prices; returning empty price frame.",
            RuntimeWarning,
            stacklevel=2,
        )
        return pd.DataFrame()

    end = datetime.today()
    start = end - timedelta(days=int(lookback_days * 1.5))  # buffer for weekends
    data = yf.download(valid_tickers, start=start, end=end, auto_adjust=True, progress=False)

    prices: pd.DataFrame
    if data.empty:
        prices = pd.DataFrame(columns=valid_tickers)
    elif isinstance(data.columns, pd.MultiIndex):
        level_0 = data.columns.get_level_values(0)
        if "Close" in level_0:
            prices = data["Close"].copy()
        elif "Adj Close" in level_0:
            prices = data["Adj Close"].copy()
        else:
            prices = pd.DataFrame(index=data.index, columns=valid_tickers)
    elif "Close" in data.columns:
        # Single ticker responses are often a flat frame with only one close column.
        prices = data[["Close"]].rename(columns={"Close": valid_tickers[0]})
    else:
        prices = pd.DataFrame(index=data.index, columns=valid_tickers)

    if isinstance(prices, pd.Series):
        prices = prices.to_frame(name=valid_tickers[0])

    for ticker in valid_tickers:
        if ticker not in prices.columns:
            prices[ticker] = np.nan

    prices = prices[valid_tickers].apply(pd.to_numeric, errors="coerce")

    unresolved_from_history = [ticker for ticker in valid_tickers if prices[ticker].dropna().empty]
    if unresolved_from_history:
        warnings.warn(
            "No usable close-price history for tickers: " + ", ".join(unresolved_from_history),
            RuntimeWarning,
            stacklevel=2,
        )

    prices = prices.dropna(how="all")
    if prices.empty:
        warnings.warn(
            "Price history contains no usable close prices after cleaning.",
            RuntimeWarning,
            stacklevel=2,
        )

    prices.attrs["price_report"] = {
        "requested_tickers": list(tickers),
        "valid_tickers": valid_tickers,
        "unresolved_price_history": unresolved_from_history,
        "price_rows": int(len(prices)),
    }
    return prices


def enrich_holdings(holdings: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Add current price, market value, weight, and P&L to holdings."""
    missing = set(REQUIRED_HOLDINGS_COLUMNS) - set(holdings.columns)
    if missing:
        raise ValueError(f"Holdings DataFrame missing required columns: {missing}")

    latest_prices = pd.Series(dtype="float64")
    if not prices.empty:
        latest_prices = prices.ffill().iloc[-1]

    enriched = holdings.copy()
    enriched["current_price"] = enriched["ticker"].map(latest_prices)

    unresolved_mask = enriched["current_price"].isna()
    unresolved_tickers = enriched.loc[unresolved_mask, "ticker"].astype(str).tolist()
    if unresolved_tickers:
        warnings.warn(
            f"Dropping {len(unresolved_tickers)} holdings with unresolved prices: {', '.join(unresolved_tickers)}",
            RuntimeWarning,
            stacklevel=2,
        )
        enriched = enriched.loc[~unresolved_mask].copy()

    for column in ENRICHED_HOLDINGS_COLUMNS:
        if column not in enriched.columns:
            enriched[column] = np.nan

    if enriched.empty:
        enriched.attrs["enrichment_report"] = {
            "input_rows": int(len(holdings)),
            "resolved_rows": 0,
            "dropped_unresolved_rows": int(len(unresolved_tickers)),
            "unresolved_tickers": unresolved_tickers,
        }
        return enriched

    enriched["market_value"] = enriched["quantity"] * enriched["current_price"]
    enriched["cost_basis"] = enriched["quantity"] * enriched["avg_cost"]

    # Adjust sign for shorts
    enriched.loc[enriched["side"] == "SHORT", "market_value"] *= -1
    enriched.loc[enriched["side"] == "SHORT", "cost_basis"] *= -1

    gross_exposure = enriched["market_value"].abs().sum()
    if gross_exposure == 0:
        enriched["weight_gross"] = 0.0
    else:
        enriched["weight_gross"] = enriched["market_value"].abs() / gross_exposure

    enriched["pnl"] = enriched["market_value"] - enriched["cost_basis"]
    cost_abs = enriched["cost_basis"].abs()
    enriched["pnl_pct"] = np.where(cost_abs > 0, enriched["pnl"] / cost_abs, np.nan)

    enriched.attrs["enrichment_report"] = {
        "input_rows": int(len(holdings)),
        "resolved_rows": int(len(enriched)),
        "dropped_unresolved_rows": int(len(unresolved_tickers)),
        "unresolved_tickers": unresolved_tickers,
    }
    return enriched
