#!/usr/bin/env python3
"""
generate_deck.py
================
CLI entry point. Feed it a holdings CSV, get a polished investor deck.

Uses the same pipeline as the local Deck Builder UI (see README).

Usage:
    python generate_deck.py --holdings data/sample_holdings.csv --date 2026-03-31
    python generate_deck.py --holdings data/sample_holdings.csv --template minimal_investor --pdf
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml
from pptx import Presentation

from src.deck_pipeline import generate_deck
from src.slide_variants import default_enabled_slides

LOG = logging.getLogger("fund_deck")


def _resolve_template_arg(project_root: Path, template: str | None) -> Path | None:
    if not template:
        return None
    raw = Path(template)
    if raw.is_file():
        return raw.resolve()
    stem = template.replace(".yaml", "").replace(".yml", "")
    for name in (f"{stem}.yaml", f"{stem}.yml", template):
        candidate = project_root / "config" / "templates" / name
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        f"Template not found: {template!r} (expected file path or name under config/templates/)."
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
        stream=sys.stderr,
    )

    project_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Generate an investor reporting deck from a holdings CSV.")
    parser.add_argument("--holdings", required=True, help="Path to holdings CSV file")
    parser.add_argument("--config", default="config/fund_config.yaml", help="Path to fund config YAML")
    parser.add_argument(
        "--template",
        default=None,
        help="Optional YAML merged onto config (file path or name under config/templates/, e.g. minimal_investor).",
    )
    parser.add_argument("--date", default=datetime.today().strftime("%Y-%m-%d"), help="Report date (YYYY-MM-DD)")
    parser.add_argument("--output", default=None, help="Output PPTX path")
    parser.add_argument("--aum", default="€125.4M", help="AUM display string")
    parser.add_argument(
        "--price-snapshot",
        default=None,
        help="Load prices from CSV/Parquet instead of Yahoo Finance (see README).",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="After PPTX, export PDF (LibreOffice headless, or PowerPoint on Windows with comtypes).",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_file():
        config_path = project_root / args.config
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    Path("charts").mkdir(exist_ok=True)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    template_path = _resolve_template_arg(project_root, args.template)
    snap_path = Path(args.price_snapshot) if args.price_snapshot else None
    if snap_path and not snap_path.is_file():
        alt = project_root / args.price_snapshot
        snap_path = alt if alt.is_file() else snap_path

    LOG.info("Generating deck: %s | %s", config["fund"]["name"], args.date)

    enabled = default_enabled_slides(config)
    out = generate_deck(
        holdings_path=args.holdings,
        config_path=config_path,
        report_date=args.date,
        aum=args.aum,
        output_path=args.output,
        chart_dir="charts",
        enabled_slides=enabled,
        slide_variants=None,
        price_snapshot_path=snap_path,
        template_path=template_path,
        pipeline_warnings=None,
    )

    LOG.info("Done. Deck: %s", out)
    LOG.info("Slides: %s", len(Presentation(str(out)).slides))

    if args.pdf:
        from src.pdf_export import pptx_to_pdf

        pdf_out = pptx_to_pdf(out)
        LOG.info("PDF: %s", pdf_out)


if __name__ == "__main__":
    main()
