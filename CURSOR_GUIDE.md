# CURSOR GUIDE — How to Build This Project Effectively

## 1. Model Configuration

Open **Cursor Settings → Models** and set up:

| Context           | Model             | Why                                              |
|-------------------|-------------------|--------------------------------------------------|
| **Chat / Agent**  | Claude Sonnet 4   | Best for multi-file refactors, architecture Q&A  |
| **Inline edits**  | Claude Sonnet 4   | Fast, accurate single-file changes               |
| **Autocomplete**  | Cursor default    | Leave as-is; it's optimised for tab completions  |

**Enable these settings:**
- ✅ "Agent" mode (not just "Ask") — this lets the model create/edit multiple files
- ✅ "Codebase indexing" — index the whole project so Cursor understands cross-file refs
- ✅ "Apply all" — so you can batch-apply multi-file suggestions

---

## 2. Project Setup Prompts

Open a terminal in Cursor and run:
```bash
pip install -r requirements.txt
python generate_deck.py --holdings data/sample_holdings.csv --date 2026-03-31
```

Verify the output PPTX opens correctly. Now you have a working baseline.

---

## 3. Recommended Build Sequence & Cursor Prompts

Work through these in order. Each prompt goes into Cursor's **Agent** chat (Cmd+L / Ctrl+L). Tag relevant files with @filename.

### Phase 1 — Get it working end-to-end (already done)
The skeleton above already runs. Your first job is to open the generated PPTX, identify what looks rough, and iterate.

### Phase 2 — Visual polish
```
@slide_builder.py @fund_config.yaml
The title slide looks flat. Add a subtle gradient-like effect using
two overlapping rectangles (dark navy on bottom, slightly lighter on top).
Add the fund logo from config/logo.png in the top-right corner if the
file exists. Keep the gold accent line.
```

```
@chart_generator.py
Refactor all charts to use the colour palette from fund_config.yaml
instead of hardcoded hex values. Add a load_brand_colours() function
that reads the YAML and returns a dict. All chart functions should
accept this dict as a parameter.
```

```
@slide_builder.py
The exposure slides have a table but it's hard to read. Add alternating
row colours (white and very light grey). Make the header row use the
primary brand colour with white text. Add thin borders.
```

### Phase 3 — New slide types
```
@slide_builder.py @analytics.py
Add a new slide: "Monthly P&L Attribution by Sector". Show a horizontal
bar chart where each bar is the P&L contribution of that sector.
Green for positive, red for negative. Add a table below showing the
exact figures. Wire it into generate_deck.py with a config toggle.
```

```
@slide_builder.py @analytics.py @chart_generator.py
Add a "Strategy Sleeve Breakdown" slide that shows gross/net exposure
per strategy_sleeve (e.g. Long/Short Equity vs Market Neutral).
Include both a stacked bar chart and a summary table.
```

```
@slide_builder.py
Add an "Executive Summary" slide after the title. It should have 4 large
KPI cards in a 2x2 grid: AUM, Net Return YTD, Gross Exposure, Net Exposure.
Each card has the number in large bold font and a label below in muted grey.
```

### Phase 4 — Data source flexibility
```
@data_loader.py
Add support for loading from Excel (.xlsx) files in addition to CSV.
Auto-detect format from the file extension. Also add a JSON loader for
holdings served from an API endpoint.
```

```
@data_loader.py
Add FX conversion: the current code ignores currency. Add a function that
fetches EUR exchange rates for all currencies in the portfolio (using
yfinance pairs like USDEUR=X) and converts all market values to the
fund's base currency from config.
```

### Phase 5 — Stretch features
```
Create a new module src/commentary.py. It should call the Anthropic API
(claude-sonnet-4-20250514) with the performance data, top movers, and risk
metrics as context, and ask it to generate a 150-word market commentary
paragraph. Add a new slide in slide_builder.py that displays this text.
Add ANTHROPIC_API_KEY to the config.
```

```
@generate_deck.py
Add a --pdf flag that, after generating the PPTX, converts it to PDF
using LibreOffice headless mode (soffice --headless --convert-to pdf).
```

```
Add a --schedule mode using Python's schedule library that generates
the deck every Friday at 18:00 and saves it to output/ with a
timestamped filename.
```

---

## 4. Cursor Power Features to Use

### @-mentions (critical)
Always tag the files you want Cursor to read/edit:
- `@slide_builder.py` when working on slides
- `@analytics.py @chart_generator.py` when changing calculations
- `@fund_config.yaml` when changing branding
- `@generate_deck.py` when wiring new features

### Agent mode vs Ask mode
- **Agent** (Cmd+L → toggle to Agent): Use for anything that creates or edits files. It can modify multiple files in one go.
- **Ask**: Use for understanding code, debugging, or "explain this function".

### Inline editing (Cmd+K)
Select code → Cmd+K → type instruction. Best for:
- "Add type hints to this function"
- "Refactor this loop into a list comprehension"
- "Add error handling for missing tickers"

### Terminal integration (Cmd+`)
Run `python generate_deck.py ...` directly in Cursor's terminal. When you get an error, paste it into Agent chat — it will read the traceback and fix the code.

### .cursorrules file
Create this in the project root to give Cursor persistent context:

```
# .cursorrules
This is a Python project that generates investor-ready PPTX slide decks
for a hedge fund. The architecture is modular:
- src/data_loader.py: CSV/Excel ingestion + Yahoo Finance enrichment
- src/analytics.py: Portfolio analytics (returns, risk, exposure)
- src/chart_generator.py: Matplotlib charts rendered as PNG
- src/slide_builder.py: python-pptx deck assembly
- generate_deck.py: CLI entry point
- config/fund_config.yaml: All branding and configuration

Key conventions:
- All colours come from fund_config.yaml, never hardcode hex values
- Charts are saved as PNG to charts/ and embedded into slides as images
- Every new slide type needs a config toggle in fund_config.yaml
- Use type hints everywhere
- Holdings DataFrame has columns: ticker, quantity, avg_cost, currency,
  sector, country, strategy_sleeve, side, current_price, market_value,
  cost_basis, weight_gross, pnl, pnl_pct
```

---

## 5. Debugging Workflow in Cursor

When something breaks:
1. Run the script in Cursor's terminal
2. Copy the full traceback
3. Open Agent chat → paste the error → tag the relevant file
4. Let it fix → Apply → rerun

Example prompt:
```
I'm getting this error when running generate_deck.py:
[paste traceback]

@data_loader.py @analytics.py
Fix this. The issue seems to be with missing tickers in the price data.
```

---

## 6. Git Workflow

Commit after each working phase:
```bash
git init
git add .
git commit -m "feat: initial working deck generator with 7 slide types"
# After Phase 2:
git commit -m "style: visual polish — branded charts, styled tables, logo"
# After Phase 3:
git commit -m "feat: attribution, strategy sleeve, and exec summary slides"
# etc.
```

This gives you a clean commit history that tells a story on GitHub.
