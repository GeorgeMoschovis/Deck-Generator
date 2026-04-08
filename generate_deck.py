#!/usr/bin/env python3
"""
generate_deck.py
================
CLI entry point. Feed it a holdings CSV, get a polished investor deck.

Uses the same pipeline as the local Deck Builder UI (see README).

Usage:
    python generate_deck.py --holdings data/sample_holdings.csv --date 2026-03-31
    python generate_deck.py --holdings data/sample_holdings.csv --date 2026-03-31 --output output/report.pptx
"""

import argparse
from datetime import datetime
from pathlib import Path

import yaml
from pptx import Presentation

from src.deck_pipeline import generate_deck
from src.slide_variants import default_enabled_slides


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an investor reporting deck from a holdings CSV.")
    parser.add_argument("--holdings", required=True, help="Path to holdings CSV file")
    parser.add_argument("--config", default="config/fund_config.yaml", help="Path to fund config YAML")
    parser.add_argument("--date", default=datetime.today().strftime("%Y-%m-%d"), help="Report date (YYYY-MM-DD)")
    parser.add_argument("--output", default=None, help="Output PPTX path")
    parser.add_argument("--aum", default="€125.4M", help="AUM display string")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    Path("charts").mkdir(exist_ok=True)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    print(f"📊 Generating deck for {config['fund']['name']} — {args.date}")

    enabled = default_enabled_slides(config)
    out = generate_deck(
        holdings_path=args.holdings,
        config_path=args.config,
        report_date=args.date,
        aum=args.aum,
        output_path=args.output,
        chart_dir="charts",
        enabled_slides=enabled,
        slide_variants=None,
    )

    print(f"\n✅ Done! Deck: {out}")
    print(f"   Slides: {len(Presentation(str(out)).slides)}")


if __name__ == "__main__":
    main()
