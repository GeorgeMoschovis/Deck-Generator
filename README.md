# Fund Deck Generator

Generate investor-style PowerPoint reports from a holdings CSV: load positions, pull market data, compute analytics, render charts, and assemble a branded PPTX.

## Requirements

- Python 3.10+

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```powershell
$env:PYTHONUTF8 = "1"
python generate_deck.py --holdings data/sample_holdings.csv --date 2026-03-31 --output output/report.pptx --aum "EUR 125.4M"
```

On Windows, `PYTHONUTF8=1` avoids console encoding errors if the CLI prints non-ASCII characters.

## Configuration

Edit `config/fund_config.yaml` for fund metadata, branding colours, slide toggles, risk parameters, and disclaimer text.

## Tests

From the repository root:

```powershell
$env:PYTHONPATH = "."
$env:PYTHONUTF8 = "1"
pytest -q
```

CI runs the same suite in `.github/workflows/tests.yml` with `PYTHONPATH` set for imports.

## Layout

```text
├── generate_deck.py       # CLI
├── config/                # YAML branding and fund settings
├── data/                  # Sample holdings
├── src/                   # Loader, analytics, charts, slides
└── tests/
```

## Licence

MIT
