# Fund Deck Generator

Automated investor-reporting deck generator for hedge funds and AIFMs.

Input: holdings CSV.  
Output: investor-ready PPTX.

## Deterministic Runbook

### 1) Install

PowerShell (Windows):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Expected output (tail):

```text
Successfully installed ... pytest-... python-pptx-... yfinance-...
```

### 2) Run the CLI manually

```powershell
python generate_deck.py --holdings data/sample_holdings.csv --date 2026-03-31 --output output/manual_smoke.pptx --aum "EUR 125.4M"
```

Expected output (example):

```text
📊 Generating deck for Aquila Capital Partners — 2026-03-31
  → Loading holdings...
  → Fetching prices for 16 securities...
  → Computing analytics...
  → Rendering charts...
  → Assembling slides...
✅ Done! Deck: output/manual_smoke.pptx
   Slides: 7
```

Expected artifact:
- `output/manual_smoke.pptx` exists and opens in PowerPoint.

### 3) Run reproducible verification

All tests:

```powershell
pytest -q
```

Expected output pattern:

```text
................                                                         [100%]
16 passed, 1 warning in <time>s
```

Smoke test only (CLI path, deterministic, offline-safe):

```powershell
pytest -q tests/test_smoke_cli.py
```

Expected output:

```text
.                                                                      [100%]
1 passed in <time>s
```

Analytics + loader unit tests:

```powershell
pytest -q tests/test_analytics.py tests/test_data_loader.py
```

Expected output:

```text
...............                                                          [100%]
15 passed, 1 warning in <time>s
```

## What the tests verify

- `tests/test_smoke_cli.py`: runs `generate_deck.py` end-to-end on `data/sample_holdings.csv` and verifies a PPTX is generated.
- `tests/test_analytics.py`: unit tests for portfolio returns, period performance, risk metrics, exposures, top positions, and attribution.
- `tests/test_data_loader.py`: loader and enrichment edge cases (missing columns, invalid tickers, empty ticker input, deduped ticker fetch, unresolved prices).

The smoke test mocks Yahoo Finance calls so CI and local checks stay deterministic.

## Project Structure

```text
fund-deck-generator/
├── generate_deck.py
├── config/fund_config.yaml
├── data/sample_holdings.csv
├── src/
├── tests/
├── .github/workflows/tests.yml
└── requirements.txt
```
