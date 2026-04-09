"""
deck_pipeline.py
----------------
Single entry to load data, render charts, and assemble PPTX from config + user choices.
Used by the CLI and the local Streamlit app.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import yaml

from src.analytics import (
    compute_portfolio_returns,
    exposure_by_field,
    performance_table,
    pnl_attribution,
    risk_metrics,
    top_positions,
)
from src.chart_generator import (
    bar_chart,
    cumulative_return_chart,
    drawdown_chart,
    pie_chart,
)
from src.config_validation import deep_merge, validate_config
from src.data_loader import enrich_holdings, fetch_prices, load_holdings
from src.slide_builder import DeckBuilder
from src.slide_variants import (
    SLIDE_ORDER,
    default_enabled_slides,
    normalize_variants,
)


def _merge_enabled_slides(config: dict[str, Any], user: Mapping[str, bool] | None) -> dict[str, bool]:
    merged = default_enabled_slides(config)
    if user:
        for key, value in user.items():
            if key in merged:
                merged[key] = bool(value)
    return merged


def _top_n_for_variant(variant: str) -> int:
    if variant == "simple":
        return 3
    if variant == "detailed":
        return 8
    return 5


def _deck_metadata(prices: Any, report_date: str) -> dict[str, str]:
    """As-of date, generation timestamp, and price source for deck footers."""
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    pr = getattr(prices, "attrs", {}).get("price_report") or {}
    if isinstance(pr, dict) and pr.get("source") == "snapshot":
        path_str = pr.get("path")
        name = Path(path_str).name if path_str else "snapshot"
        prices_caption = f"Prices: snapshot ({name})"
    else:
        prices_caption = "Prices & FX: Yahoo Finance"
    return {
        "as_of_iso": report_date,
        "generated_at": generated_at,
        "prices_caption": prices_caption,
    }


def _collect_reports_into_warnings(
    pipeline_warnings: list[str] | None,
    holdings_after_load: Any,
    prices: Any,
    holdings_after_enrich: Any,
) -> None:
    if pipeline_warnings is None:
        return

    ing = getattr(holdings_after_load, "attrs", {}).get("ingestion_report")
    if isinstance(ing, dict) and ing.get("dropped_invalid_ticker_rows", 0) > 0:
        pipeline_warnings.append(
            f"Dropped {ing['dropped_invalid_ticker_rows']} holdings row(s) with invalid tickers "
            f"(loaded {ing.get('loaded_rows', '?')}, kept {ing.get('remaining_rows', '?')})."
        )

    pr = getattr(prices, "attrs", {}).get("price_report")
    if isinstance(pr, dict) and pr.get("unresolved_price_history"):
        pipeline_warnings.append(
            "No usable price history for: " + ", ".join(pr["unresolved_price_history"])
        )

    en = getattr(holdings_after_enrich, "attrs", {}).get("enrichment_report")
    if isinstance(en, dict) and en.get("dropped_unresolved_rows", 0) > 0:
        ut = en.get("unresolved_tickers") or []
        pipeline_warnings.append(
            f"Dropped {en['dropped_unresolved_rows']} holding(s) with missing prices: {', '.join(map(str, ut))}."
        )


def generate_deck(
    holdings_path: str | Path,
    config_path: str | Path,
    report_date: str,
    aum: str,
    output_path: str | Path | None = None,
    chart_dir: str | Path = "charts",
    enabled_slides: Mapping[str, bool] | None = None,
    slide_variants: Mapping[str, str] | None = None,
    price_snapshot_path: str | Path | None = None,
    template_path: str | Path | None = None,
    pipeline_warnings: list[str] | None = None,
) -> Path:
    """
    Build a complete deck. ``slide_variants`` keys: performance_summary, exposure_sector,
    exposure_geography, top_positions (see ``src.slide_variants``).

    ``template_path``: optional YAML merged on top of ``config_path`` (override wins).

    ``pipeline_warnings``: if provided, human-readable warning strings are appended (for UIs).
    """
    holdings_path = Path(holdings_path)
    config_path = Path(config_path)
    chart_dir = Path(chart_dir)
    chart_dir.mkdir(parents=True, exist_ok=True)

    with open(config_path, "r", encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f)

    if template_path:
        tp = Path(template_path)
        with open(tp, "r", encoding="utf-8") as f:
            template_doc = yaml.safe_load(f)
        if not isinstance(template_doc, dict):
            raise ValueError("Template YAML must be a mapping at the root.")
        config = deep_merge(config, template_doc)

    validate_config(config)

    enabled = _merge_enabled_slides(config, enabled_slides)
    variants = normalize_variants(dict(slide_variants) if slide_variants else None)
    branding = config.get("branding", {})

    if output_path is None:
        fund_name = config["fund"]["name"].replace(" ", "_")
        output_path = Path("output") / f"{fund_name}_Report_{report_date}.pptx"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    holdings_loaded = load_holdings(holdings_path)
    tickers = holdings_loaded["ticker"].tolist()
    bench_raw = (config.get("fund") or {}).get("benchmark_ticker") or ""
    bench_ticker = str(bench_raw).strip()
    tickers_for_fetch = list(dict.fromkeys(tickers + ([bench_ticker] if bench_ticker else [])))

    lookback = int(config["risk"]["var_lookback_days"])
    prices = fetch_prices(tickers_for_fetch, lookback_days=lookback, snapshot_path=price_snapshot_path)

    base_ccy = str(config["fund"]["base_currency"]).strip()
    holdings = enrich_holdings(holdings_loaded, prices, base_currency=base_ccy)

    _collect_reports_into_warnings(pipeline_warnings, holdings_loaded, prices, holdings)

    port_returns = compute_portfolio_returns(holdings, prices)
    perf = performance_table(
        port_returns,
        inception_date=str(config["fund"].get("inception_date") or "") or None,
    )
    risk = risk_metrics(
        port_returns,
        config["risk"]["var_confidence"],
        config["risk"]["risk_free_rate"],
    )
    sector_exp = exposure_by_field(holdings, "sector")
    geo_exp = exposure_by_field(holdings, "country")
    top_n = _top_n_for_variant(variants["top_positions"])
    top_longs, top_shorts = top_positions(holdings, n=top_n)
    attribution = pnl_attribution(holdings, "sector")

    benchmark_returns = None
    if bench_ticker and bench_ticker in prices.columns and not port_returns.empty:
        bm_pct = prices[bench_ticker].pct_change(fill_method=None)
        benchmark_returns = bm_pct.reindex(port_returns.index).ffill().bfill()
        benchmark_returns = benchmark_returns.fillna(0.0)

    cum_path = chart_dir / "cumulative.png"
    dd_path = chart_dir / "drawdown.png"
    sector_net_path = chart_dir / "sector_net.png"
    sector_pie_path = chart_dir / "sector_pie.png"
    geo_net_path = chart_dir / "geo_net.png"
    geo_pie_path = chart_dir / "geo_pie.png"
    attribution_path = chart_dir / "attribution.png"

    perf_v = variants["performance_summary"]
    if enabled.get("performance_summary") and perf_v != "simple" and not port_returns.empty:
        cumulative_return_chart(
            port_returns,
            str(cum_path),
            branding=branding,
            benchmark_returns=benchmark_returns,
        )
        drawdown_chart(port_returns, str(dd_path), branding=branding)

    sec_v = variants["exposure_sector"]
    if enabled.get("exposure_sector"):
        if sec_v in ("net_bars", "split"):
            bar_chart(
                sector_exp["net_weight"],
                str(sector_net_path),
                title="Net Exposure by Sector",
                horizontal=True,
                branding=branding,
            )
        if sec_v in ("pie_gross", "split"):
            pie_chart(
                sector_exp["gross_weight"],
                str(sector_pie_path),
                title="Gross Exposure by Sector",
                branding=branding,
            )

    geo_v = variants["exposure_geography"]
    if enabled.get("exposure_geography"):
        if geo_v in ("net_bars", "split"):
            bar_chart(
                geo_exp["net_weight"],
                str(geo_net_path),
                title="Net Exposure by Geography",
                horizontal=True,
                branding=branding,
            )
        if geo_v in ("pie_gross", "split"):
            pie_chart(
                geo_exp["gross_weight"],
                str(geo_pie_path),
                title="Gross Exposure by Geography",
                branding=branding,
            )

    if enabled.get("attribution", False):
        bar_chart(
            attribution["pnl_contribution_pct"],
            str(attribution_path),
            title="P&L Contribution by Sector",
            horizontal=True,
            branding=branding,
        )

    deck = DeckBuilder(config, metadata=_deck_metadata(prices, report_date))

    report_date_fmt = datetime.strptime(report_date, "%Y-%m-%d").strftime("%B %Y")

    for slide_key in SLIDE_ORDER:
        if not enabled.get(slide_key, False):
            continue
        if slide_key == "title":
            deck.add_title_slide(report_date_fmt, aum=aum)
        elif slide_key == "performance_summary":
            deck.add_performance_slide(perf, str(cum_path), str(dd_path), variant=perf_v)  # type: ignore[arg-type]
        elif slide_key == "exposure_sector":
            if sec_v == "net_bars":
                deck.add_exposure_slide(
                    "Sector Exposure",
                    str(sector_net_path),
                    sector_exp,
                    variant="net_bars",
                )
            elif sec_v == "pie_gross":
                deck.add_exposure_slide(
                    "Sector Exposure",
                    str(sector_pie_path),
                    sector_exp,
                    variant="pie_gross",
                )
            else:
                deck.add_exposure_slide(
                    "Sector Exposure",
                    str(sector_net_path),
                    sector_exp,
                    variant="split",
                    secondary_chart_path=str(sector_pie_path),
                )
        elif slide_key == "exposure_geography":
            if geo_v == "net_bars":
                deck.add_exposure_slide(
                    "Geographic Exposure",
                    str(geo_net_path),
                    geo_exp,
                    variant="net_bars",
                )
            elif geo_v == "pie_gross":
                deck.add_exposure_slide(
                    "Geographic Exposure",
                    str(geo_pie_path),
                    geo_exp,
                    variant="pie_gross",
                )
            elif geo_v == "split":
                deck.add_exposure_slide(
                    "Geographic Exposure",
                    str(geo_net_path),
                    geo_exp,
                    variant="split",
                    secondary_chart_path=str(geo_pie_path),
                )
            else:
                deck.add_exposure_slide(
                    "Geographic Exposure",
                    "",
                    geo_exp,
                    variant="table_only",
                )
        elif slide_key == "top_positions":
            deck.add_top_positions_slide(top_longs, top_shorts)
        elif slide_key == "risk_metrics":
            deck.add_risk_slide(risk)
        elif slide_key == "attribution":
            deck.add_attribution_slide(attribution, str(attribution_path))
        elif slide_key == "disclaimer":
            deck.add_disclaimer_slide()

    deck.save(str(output_path))
    return output_path
