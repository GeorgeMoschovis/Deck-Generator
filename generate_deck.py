#!/usr/bin/env python3
"""
generate_deck.py
================
CLI entry point. Feed it a holdings CSV, get a polished investor deck.

Usage:
    python generate_deck.py --holdings data/sample_holdings.csv --date 2026-03-31
    python generate_deck.py --holdings data/sample_holdings.csv --date 2026-03-31 --output output/report.pptx
"""

import argparse
import yaml
from pathlib import Path
from datetime import datetime

from src.data_loader import load_holdings, fetch_prices, enrich_holdings
from src.analytics import (
    compute_portfolio_returns, performance_table, risk_metrics,
    exposure_by_field, top_positions, pnl_attribution,
)
from src.chart_generator import (
    cumulative_return_chart, drawdown_chart, bar_chart, pie_chart,
)
from src.slide_builder import DeckBuilder


def main():
    parser = argparse.ArgumentParser(description="Generate an investor reporting deck from a holdings CSV.")
    parser.add_argument("--holdings", required=True, help="Path to holdings CSV file")
    parser.add_argument("--config", default="config/fund_config.yaml", help="Path to fund config YAML")
    parser.add_argument("--date", default=datetime.today().strftime("%Y-%m-%d"), help="Report date (YYYY-MM-DD)")
    parser.add_argument("--output", default=None, help="Output PPTX path")
    parser.add_argument("--aum", default="€125.4M", help="AUM display string")
    args = parser.parse_args()

    # Load config
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    # Prepare output path
    if args.output is None:
        args.output = f"output/{config['fund']['name'].replace(' ', '_')}_Report_{args.date}.pptx"
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path("charts").mkdir(exist_ok=True)

    print(f"📊 Generating deck for {config['fund']['name']} — {args.date}")

    # 1. Load & enrich data
    print("  → Loading holdings...")
    holdings = load_holdings(args.holdings)
    tickers = holdings["ticker"].tolist()

    print(f"  → Fetching prices for {len(tickers)} securities...")
    prices = fetch_prices(tickers, lookback_days=config["risk"]["var_lookback_days"])
    holdings = enrich_holdings(holdings, prices)

    # 2. Compute analytics
    print("  → Computing analytics...")
    port_returns = compute_portfolio_returns(holdings, prices)
    perf = performance_table(port_returns)
    risk = risk_metrics(port_returns, config["risk"]["var_confidence"], config["risk"]["risk_free_rate"])
    sector_exp = exposure_by_field(holdings, "sector")
    geo_exp = exposure_by_field(holdings, "country")
    top_longs, top_shorts = top_positions(holdings, n=5)
    attribution = pnl_attribution(holdings, "sector")

    # 3. Generate charts
    print("  → Rendering charts...")
    branding = config.get("branding", {})
    cumulative_return_chart(port_returns, "charts/cumulative.png", branding=branding)
    drawdown_chart(port_returns, "charts/drawdown.png", branding=branding)
    bar_chart(
        sector_exp["net_weight"],
        "charts/sector_net.png",
        title="Net Exposure by Sector",
        horizontal=True,
        branding=branding,
    )
    bar_chart(
        geo_exp["net_weight"],
        "charts/geo_net.png",
        title="Net Exposure by Geography",
        horizontal=True,
        branding=branding,
    )
    pie_chart(
        sector_exp["gross_weight"],
        "charts/sector_pie.png",
        title="Gross Exposure by Sector",
        branding=branding,
    )
    if config["slides"].get("attribution", False):
        bar_chart(
            attribution["pnl_contribution_pct"],
            "charts/attribution.png",
            title="P&L Contribution by Sector",
            horizontal=True,
            branding=branding,
        )

    # 4. Build deck
    print("  → Assembling slides...")
    deck = DeckBuilder(config)

    report_date_fmt = datetime.strptime(args.date, "%Y-%m-%d").strftime("%B %Y")

    if config["slides"]["title"]:
        deck.add_title_slide(report_date_fmt, aum=args.aum)

    if config["slides"]["performance_summary"]:
        deck.add_performance_slide(perf, "charts/cumulative.png", "charts/drawdown.png")

    if config["slides"]["exposure_sector"]:
        deck.add_exposure_slide("Sector Exposure", "charts/sector_net.png", sector_exp)

    if config["slides"]["exposure_geography"]:
        deck.add_exposure_slide("Geographic Exposure", "charts/geo_net.png", geo_exp)

    if config["slides"]["top_positions"]:
        deck.add_top_positions_slide(top_longs, top_shorts)

    if config["slides"]["risk_metrics"]:
        deck.add_risk_slide(risk)

    if config["slides"].get("attribution", False):
        deck.add_attribution_slide(attribution, "charts/attribution.png")

    if config["slides"]["disclaimer"]:
        deck.add_disclaimer_slide()

    deck.save(args.output)
    print(f"\n✅ Done! Deck: {args.output}")
    print(f"   Slides: {len(deck.prs.slides)}")


if __name__ == "__main__":
    main()
