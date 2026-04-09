# Fund Deck Generator

Generate investor-style PowerPoint reports from a holdings CSV: load positions, pull market data (Yahoo Finance), convert to the fund’s base currency, compute analytics, render charts (including an optional benchmark line), and assemble a branded PPTX.

## Requirements

- Python 3.10+
- Optional: [LibreOffice](https://www.libreoffice.org/) on PATH for `--pdf` (`soffice` / `libreoffice`)

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Editable install with CLI entry point `fund-deck`:

```powershell
pip install -e ".[dev]"
fund-deck --help
fund-deck --version
```

From a repo checkout without an editable install, `python generate_deck.py --version` prints the same version (from `pyproject.toml`).

## Run (CLI)

```powershell
$env:PYTHONUTF8 = "1"
python generate_deck.py --holdings data/sample_holdings.csv --date 2026-03-31 --output output/report.pptx --aum "EUR 125.4M"
```

Use a **template** (YAML merged on top of `config/fund_config.yaml`):

```powershell
python generate_deck.py --holdings data/sample_holdings.csv --template minimal_investor --output output/minimal.pptx
```

**Deterministic prices** (no live Yahoo call): save a CSV with a date index and one column per ticker (plus optional benchmark), then either:

```powershell
$env:DECK_PRICE_SNAPSHOT = "path\to\prices.csv"
python generate_deck.py --holdings data/sample_holdings.csv --output output/report.pptx
```

Or require snapshot mode explicitly (path via `DECK_PRICE_SNAPSHOT` or `DECK_SNAPSHOT_PATH`):

```powershell
$env:DECK_USE_SNAPSHOT = "1"
$env:DECK_SNAPSHOT_PATH = "path\to\prices.csv"
python generate_deck.py --holdings data/sample_holdings.csv --output output/report.pptx
```

Or pass `--price-snapshot path\to\prices.csv` (overrides env for that run).

**PDF export**: tries LibreOffice (`soffice` / `libreoffice`) first. On **Windows**, if LibreOffice is not installed, you can use **Microsoft PowerPoint** via COM after `pip install comtypes`.

```powershell
python generate_deck.py --holdings data/sample_holdings.csv --output output/report.pptx --pdf
```

Store reproducible price CSVs under `fixtures/` or `cache/` (see `cache/.gitkeep`) and point `DECK_PRICE_SNAPSHOT` or `--price-snapshot` at them.

On Windows, `PYTHONUTF8=1` avoids console encoding issues when logging non-ASCII text.

## Deck Builder (local UI)

Pick slides, layout variants, and optional templates; warnings from the loader (e.g. dropped tickers) appear in the app. After a successful build, `.deck_builder_state.json` in the project root (gitignored) stores holdings path, AUM, template choice, slide on/off toggles, and layout variant picks for the next session.

```powershell
$env:PYTHONPATH = "."
streamlit run app_deck_builder.py
```

## Configuration

- `config/fund_config.yaml` — fund identity, `benchmark_ticker`, branding (6-digit hex colours), slide toggles, risk parameters, disclaimer.
- `config/templates/` — optional presets (`minimal_investor.yaml`, `full_gp_report.yaml`) merged over the base config.

## Methodology (summary)

- **Weights:** Duplicate tickers are aggregated; each line’s contribution uses signed gross weight (long +1, short −1) times daily simple returns, then summed.
- **Period returns:** MTD / QTD / YTD / ITD are compounded simple daily returns over the relevant calendar windows. **ITD** is further trimmed to dates on or after `fund.inception_date` when that field is set.
- **Risk:** Daily parametric and historical VaR at the configured confidence, Sharpe/Sortino vs the configured annual risk-free rate de-annualised to a daily rate, max drawdown and annualised volatility from the same return series.
- **FX:** Positions are converted to `fund.base_currency` using latest Yahoo FX spot pairs (`{CCY}{BASE}=X` with an inverted fallback). If a pair is missing, a warning is issued and a 1.0 rate is used for that currency.
- **Missing prices:** Rows without a usable close are dropped before exposure and P&L; warnings describe what was removed.

## Tests and quality

From the repository root (no `PYTHONPATH` needed for tests — `pyproject.toml` sets `pythonpath` for pytest):

```powershell
$env:PYTHONUTF8 = "1"
pytest -q
python -m ruff check .
python -m mypy src
```

CI (`.github/workflows/tests.yml`) runs the same checks; it also sets `PYTHONPATH` for compatibility.

## Docker

```bash
docker build -t fund-deck .
docker run --rm -v "$PWD:/app" fund-deck --holdings data/sample_holdings.csv --output output/report.pptx
```

Mount your `config/`, `data/`, and `output/` as needed.

## Layout

```text
├── generate_deck.py          # CLI
├── app_deck_builder.py       # Streamlit UI
├── config/
│   ├── fund_config.yaml
│   └── templates/
├── data/
├── fixtures/                 # optional: committed price CSV samples
├── cache/                    # optional: local price snapshots (ignored except .gitkeep)
├── src/                      # pipeline, loader, analytics, charts, slides
├── tests/
├── Dockerfile
├── pyproject.toml
└── requirements.txt
```

## Licence

MIT
