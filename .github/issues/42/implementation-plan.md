# Implementation Plan: Issue #42 — `tradingview-screener` Agent Skill

## Branch
`feature/issue-42-tradingview-screener-skill`

---

## 1. Open Question Resolutions

The following table records Lead Developer answers to the open questions that
were raised in `plan.md`. All downstream agents MUST treat these as binding
decisions.

| OQ | Decision | Impact on Plan |
|----|----------|----------------|
| Q1 | **Yes — add `scripts/` directory.** It must contain a `smoke_test.py` and at least two working example scripts. These scripts perform live HTTP queries and serve as executable learning material for agents. | Adds Story 6 (Create `scripts/` directory). Constraint C8 is revised — scripts may be network-dependent; `SKILL.md` body itself must remain code-free documentation. |
| Q2 | **Network access is available and required.** The agent must run the smoke test to validate that examples produce valid `DataFrame` output before marking any story complete. | Smoke test in Story 6 is mandatory. `gotchas.md` will note offline fallback is not documented (out of scope). |
| Q3 | **Do NOT add a `compatibility` field to SKILL.md frontmatter.** The skill must always be version-agnostic. No pinning, no minimum version annotation in any skill file. | Constraint C2 updated. |
| Q4 | **Delete `docs/tradingview_screener/TRADINGVIEW_SCREENER_GUIDE.md`.** It covers only the obsolete `get_all_symbols()` API and must not co-exist with the new skill which documents the `Query()` API. Adds Story 7. Constraint C5 is revised accordingly. | The old guide is the ONLY existing file that may be touched. No other existing file in the repo may be modified. |
| Q5 | **Create `references/fields.md` once, manually, from the live fields page.** The catalogue must be comprehensive — no fields may be omitted. The canonical source is: `https://shner-elmo.github.io/TradingView-Screener/fields/stocks.html`. The developer agent must fetch this page live and transcribe all fields into the reference file, grouped by category. | Story 3 is the most labour-intensive story. The developer must fetch the page and transcribe all fields, not guess. |

---

## 2. Updated Constraints & Conventions

All constraints from `plan.md` remain in force. The following are changes or
additions resulting from the OQ resolutions above.

| # | Rule | Change from plan.md |
|---|------|---------------------|
| C2 | `SKILL.md` frontmatter must contain `name` and `description` only. No `compatibility`, no `version`, no other keys. | **Updated**: removed version constraint guidance. |
| C5 | `docs/tradingview_screener/TRADINGVIEW_SCREENER_GUIDE.md` MUST be deleted. It is the only existing file that may be touched. All other existing files remain untouched. | **Revised**: one file is deleted, not modified. |
| C8 | `SKILL.md` body must not contain executable code or network-dependent instructions. `scripts/` files are exempt and must perform live queries. | **Clarified**: restriction applies to `SKILL.md` body only. |
| C9 | *(new)* All scripts in `.github/skills/tradingview-screener/scripts/` must be runnable Python files that exit cleanly. They must import from `tradingview_screener` and perform a live `get_scanner_data()` call. | New. |
| C10 | *(new)* `scripts/smoke_test.py` must be the canonical validation tool. Running `python scripts/smoke_test.py` from within the skill directory must exit with code 0 and print a confirmation line to stdout. This is the agent's own acceptance gate. | New. |

### Library version note

`tradingview-screener` is currently pinned at `2.5.0` in
`tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt`. The latest release
is **v3.1.0** (Feb 2026). The skill must document the `Query()` API as it
exists in v3.x. The `requirements.txt` pin is a separate concern; upgrading
it is **not** part of Issue 42 and must be tracked as follow-up technical
debt.

Both `Column` (capital C, used in production code) and `col` (lowercase,
used in upstream docs) are valid aliases in v3.x. The skill should show
`Column` as primary (matching production code) and note the `col` alias.

---

## 3. Delivery Stories

Stories must be executed in the order listed. Each story is a single commit.

---

### Story 1 — Scaffold skill directory and `SKILL.md` stub

**Files created:**
- `.github/skills/tradingview-screener/SKILL.md`

**Exact `SKILL.md` frontmatter required:**
```yaml
---
name: tradingview-screener
description: >
  Skill for querying financial market data using the tradingview-screener
  Python library. Covers the Query() API, field names, filter syntax,
  multi-market queries, index constituent retrieval, and fundamental
  screening. Load this skill whenever you need to write or debug a
  tradingview_screener Query: selecting columns, applying .where() filters,
  using .set_markets(), .set_index(), .order_by(), .limit(), or calling
  .get_scanner_data(). Includes a comprehensive field catalogue
  (references/fields.md), known gotchas (references/gotchas.md), and
  annotated usage examples (references/examples.md).
---
```

**Body at this stage:** Single line — `<!-- body placeholder — replaced in Story 2 -->`.

**Acceptance criteria:**
- [ ] `name` value is exactly `tradingview-screener` (no quotes, no spaces).
- [ ] `description` is ≤ 1 024 characters (count with `wc -c`).
- [ ] File is valid YAML — runnable `python -c "import yaml; yaml.safe_load(open('.github/skills/tradingview-screener/SKILL.md').read().split('---')[1])"` raises no exception.
- [ ] No `compatibility`, `version`, or other frontmatter keys are present.

**Commit:** `feat(issue-42): scaffold tradingview-screener skill directory and SKILL.md stub`

---

### Story 2 — Write core `SKILL.md` body

**Files modified:**
- `.github/skills/tradingview-screener/SKILL.md` — replace placeholder body

**Required sections in order:**

1. **When to load this skill** — one short paragraph: load whenever writing or reviewing any Python code that imports from `tradingview_screener`.

2. **Package identity** — table:

   | Attribute | Value |
   |-----------|-------|
   | PyPI name | `tradingview-screener` |
   | Import path | `from tradingview_screener import Query, Column` |
   | Distinct from | `tradingview-scraper` (different package, already in `tayfin-ingestor-jobs/requirements.txt`) |
   | Upstream docs | https://shner-elmo.github.io/TradingView-Screener/ |
   | Fields reference | https://shner-elmo.github.io/TradingView-Screener/fields/stocks.html |

3. **`Query()` method chain** — one sub-section per method with signature, description, and key notes:
   - `.set_markets(*markets)` — sets the market universe; string values from the screener markets list (e.g. `'turkey'`, `'america'`); can be called with multiple markets.
   - `.set_index(index_id)` — restricts to a specific index; use `'SYML:BIST;XU100'` for BIST XU100; `'SYML:SP;SPX'` for S&P 500.
   - `.select(*columns)` — specifies which fields to fetch; column names must match the canonical list in `references/fields.md` exactly (case-sensitive); `ticker` is always returned implicitly.
   - `.where(*conditions)` — SQL-like filters; conditions use `Column('field_name') <operator> value`; multiple conditions are ANDed; wrap in `.or_()` for OR logic.
   - `.order_by(column, ascending=True)` — sorts results; returns top N after ordering when used with `.limit()`.
   - `.offset(n)` — skips first N rows (for pagination).
   - `.limit(n)` — caps result rows; server default is 50; use up to 200 without risk; above 200 increases ban risk.
   - `.get_scanner_data()` — executes the HTTP request; returns `(int, pd.DataFrame)` where `int` is the total server-side match count (always ≥ `len(df)`) and `df` contains the results; `ticker` column is always present and in `EXCHANGE:SYMBOL` format.

4. **Return value shape** — short section explaining the `(raw_count, df)` tuple; note that `raw_count > len(df)` is normal when `.limit()` is applied; `df.columns` always includes `ticker`.

5. **Ticker format rule** — critical note: every value in `df['ticker']` is `EXCHANGE:SYMBOL` (e.g. `BIST:THYAO`, `NASDAQ:AAPL`). Never bare symbol. Strip the prefix with `t.replace('BIST:', '', 1)` only after retrieval.

6. **End-to-end example** — BIST XU100 index constituents (matching the current production query in `tayfin-ingestor-jobs`):
   ```python
   from tradingview_screener import Query, Column

   raw_count, df = (
       Query()
       .set_markets('turkey')
       .set_index('SYML:BIST;XU100')
       .select('name', 'exchange', 'market', 'is_primary', 'indexes')
       .where(Column('is_primary') == True)
       .limit(5000)
       .get_scanner_data()
   )
   # raw_count: total matching symbols on server
   # df: DataFrame with columns [ticker, name, exchange, market, is_primary, indexes]
   # df['ticker'] values: 'BIST:THYAO', 'BIST:AKBNK', ...
   ```

7. **Reference files** — load-on-demand table:

   | File | When to load |
   |------|-------------|
   | `references/fields.md` | Before writing any `.select()` or `.where()` call — look up exact column names |
   | `references/gotchas.md` | When results are unexpected, columns are missing, or duplicates appear |
   | `references/examples.md` | When building a new query type not covered in this file |

8. **Scripts** — note that `.github/skills/tradingview-screener/scripts/smoke_test.py` can be run to validate the library is installed and queries work.

**Acceptance criteria:**
- [ ] `SKILL.md` total line count ≤ 500 (`wc -l`).
- [ ] All seven sections are present and non-empty.
- [ ] The end-to-end example is syntactically valid Python (run `python -m py_compile` against the code block extracted to a temp file).
- [ ] Relative paths `references/fields.md`, `references/gotchas.md`, `references/examples.md` appear in the body (they are forward references — files don't exist yet at this story).

**Commit:** `feat(issue-42): write core SKILL.md instructions and query API reference`

---

### Story 3 — Add comprehensive field reference catalogue

**Files created:**
- `.github/skills/tradingview-screener/references/fields.md`

**Source of truth:** Fetch live from `https://shner-elmo.github.io/TradingView-Screener/fields/stocks.html`.
The developer agent MUST fetch this page during execution — do not guess or rely on memory.

**File structure:**

```
# TradingView Screener — Field Reference Catalogue

> Source: https://shner-elmo.github.io/TradingView-Screener/fields/stocks.html
> Last verified: <date of fetch>
>
> Use this file to look up exact column name strings before writing any
> `.select()` or `.where()` call. Column names are case-sensitive.
> Field names with `|` suffix support timeframes: `close|1` (1 min),
> `close|5` (5 min), `close|60` (1h), `close` (1 day), `close|1W` (1 week).

---

## Core Identity & Market Info

| Column name | Display name | Type |
|-------------|--------------|------|
| ticker | Symbol (always returned) | text |
| name | Symbol name | text |
| exchange | Exchange | text |
| market | Market | text |
| type | Symbol type | text |
| is_primary | Primary listing | bool |
| active_symbol | Active in current session | bool |
| country | Region/Country | text |
| currency | Quote currency | text |
| sector | Sector | text |
| industry | Industry | text |
| submarket | Submarket | text |
| description | Full name/description | text |
| logoid | Logo identifier | text |
| update_mode | Data update mode (streaming/delayed) | text |

---

## Price & OHLCV

| Column name | Display name | Type |
|-------------|--------------|------|
| open | Open | price |
| high | High | price |
| low | Low | price |
| close | Close / Price (daily) | price |
| volume | Volume | number |
| VWAP | Volume Weighted Average Price | number |
| change | Change % | percent |
| change_abs | Change (absolute) | price |
| change_from_open | Change from Open % | percent |
| change_from_open_abs | Change from Open | price |
| gap | Gap % | percent |
| Value.Traded | Volume × Price | number |
| relative_volume_10d_calc | Relative Volume (10d avg) | number |
| average_volume_10d_calc | Average Volume (10d) | number |
| average_volume_30d_calc | Average Volume (30d) | number |
| average_volume_60d_calc | Average Volume (60d) | number |
| average_volume_90d_calc | Average Volume (90d) | number |
| volume_change | Volume Change % | percent |
| premarket_open | Pre-market Open | price |
| premarket_high | Pre-market High | price |
| premarket_low | Pre-market Low | price |
| premarket_close | Pre-market Close | price |
| premarket_volume | Pre-market Volume | number |
| premarket_change | Pre-market Change % | percent |
| premarket_change_abs | Pre-market Change | price |
| premarket_gap | Pre-market Gap % | percent |
| postmarket_open | Post-market Open | price |
| postmarket_high | Post-market High | price |
| postmarket_low | Post-market Low | price |
| postmarket_close | Post-market Close | price |
| postmarket_volume | Post-market Volume | number |
| postmarket_change | Post-market Change % | percent |

---

## Price Range & Performance

| Column name | Display name | Type |
|-------------|--------------|------|
| price_52_week_high | 52-Week High | number |
| price_52_week_low | 52-Week Low | number |
| High.1M | 1-Month High | number |
| Low.1M | 1-Month Low | number |
| High.3M | 3-Month High | number |
| Low.3M | 3-Month Low | number |
| High.6M | 6-Month High | number |
| Low.6M | 6-Month Low | number |
| High.All | All Time High | number |
| Low.All | All Time Low | number |
| Perf.5D | 5-Day Performance | number |
| Perf.1M | Monthly Performance | number |
| Perf.3M | 3-Month Performance | number |
| Perf.6M | 6-Month Performance | number |
| Perf.Y | Yearly Performance | number |
| Perf.YTD | YTD Performance | number |
| Perf.5Y | 5-Year Performance | number |
| Perf.All | All Time Performance | number |
| Perf.W | Weekly Performance | number |
| beta_1_year | 1-Year Beta | number |
| Volatility.D | Daily Volatility | number |
| Volatility.W | Weekly Volatility | number |
| Volatility.M | Monthly Volatility | number |
| ADR | Average Day Range (14) | number |

---

## Moving Averages

| Column name | Display name | Type |
|-------------|--------------|------|
| SMA5 | SMA (5) | number |
| SMA10 | SMA (10) | number |
| SMA20 | SMA (20) | number |
| SMA30 | SMA (30) | number |
| SMA50 | SMA (50) | number |
| SMA100 | SMA (100) | number |
| SMA200 | SMA (200) | number |
| EMA5 | EMA (5) | number |
| EMA10 | EMA (10) | number |
| EMA20 | EMA (20) | number |
| EMA30 | EMA (30) | number |
| EMA50 | EMA (50) | number |
| EMA100 | EMA (100) | number |
| EMA200 | EMA (200) | number |
| HullMA9 | Hull Moving Average (9) | number |
| VWMA | Volume Weighted Moving Average (20) | number |
| Recommend.MA | Moving Averages Rating | number |

---

## Technical Indicators & Oscillators

| Column name | Display name | Type |
|-------------|--------------|------|
| RSI | Relative Strength Index (14) | number |
| RSI7 | RSI (7) | number |
| MACD.macd | MACD Level (12, 26) | number |
| MACD.signal | MACD Signal (12, 26) | number |
| MACD.hist | MACD Histogram | number |
| Stoch.K | Stochastic %K (14, 3, 3) | number |
| Stoch.D | Stochastic %D (14, 3, 3) | number |
| Stoch.RSI.K | Stochastic RSI Fast | number |
| Stoch.RSI.D | Stochastic RSI Slow | number |
| ADX | Average Directional Index (14) | number |
| ADX+DI | Positive DI (14) | number |
| ADX-DI | Negative DI (14) | number |
| ATR | Average True Range (14) | number |
| CCI20 | Commodity Channel Index (20) | number |
| AO | Awesome Oscillator | number |
| Mom | Momentum (10) | number |
| ROC | Rate of Change (9) | number |
| BB.upper | Bollinger Upper Band (20) | number |
| BB.lower | Bollinger Lower Band (20) | number |
| BB.basis | Bollinger Basis | number |
| KltChnl.upper | Keltner Channel Upper (20) | number |
| KltChnl.lower | Keltner Channel Lower (20) | number |
| DonchCh20.Upper | Donchian Upper (20) | number |
| DonchCh20.Lower | Donchian Lower (20) | number |
| Ichimoku.CLine | Ichimoku Conversion Line | number |
| Ichimoku.BLine | Ichimoku Base Line | number |
| Ichimoku.Lead1 | Ichimoku Leading Span A | number |
| Ichimoku.Lead2 | Ichimoku Leading Span B | number |
| P.SAR | Parabolic SAR | number |
| ChaikinMoneyFlow | Chaikin Money Flow (20) | number |
| MoneyFlow | Money Flow (14) | number |
| UO | Ultimate Oscillator (7, 14, 28) | number |
| BBPower | Bull Bear Power | number |
| W.R | Williams %R (14) | number |
| Aroon.Up | Aroon Up (14) | number |
| Aroon.Down | Aroon Down (14) | number |
| Recommend.All | Technical Rating (composite) | number |
| Recommend.Other | Oscillators Rating | number |

---

## Candlestick Patterns

| Column name | Display name | Type |
|-------------|--------------|------|
| Candle.Doji | Doji | number |
| Candle.Doji.Dragonfly | Dragonfly Doji | number |
| Candle.Doji.Gravestone | Gravestone Doji | number |
| Candle.Hammer | Hammer | number |
| Candle.InvertedHammer | Inverted Hammer | number |
| Candle.HangingMan | Hanging Man | number |
| Candle.Engulfing.Bullish | Bullish Engulfing | number |
| Candle.Engulfing.Bearish | Bearish Engulfing | number |
| Candle.Harami.Bullish | Bullish Harami | number |
| Candle.Harami.Bearish | Bearish Harami | number |
| Candle.MorningStar | Morning Star | number |
| Candle.EveningStar | Evening Star | number |
| Candle.3WhiteSoldiers | Three White Soldiers | number |
| Candle.3BlackCrows | Three Black Crows | number |
| Candle.AbandonedBaby.Bullish | Abandoned Baby Bullish | number |
| Candle.AbandonedBaby.Bearish | Abandoned Baby Bearish | number |
| Candle.ShootingStar | Shooting Star | number |
| Candle.Kicking.Bullish | Kicking Bullish | number |
| Candle.Kicking.Bearish | Kicking Bearish | number |
| Candle.Marubozu.White | Marubozu White | number |
| Candle.Marubozu.Black | Marubozu Black | number |
| Candle.SpinningTop.White | Spinning Top White | number |
| Candle.SpinningTop.Black | Spinning Top Black | number |
| Candle.LongShadow.Upper | Long Upper Shadow | number |
| Candle.LongShadow.Lower | Long Lower Shadow | number |
| Candle.TriStar.Bullish | Tri-Star Bullish | number |
| Candle.TriStar.Bearish | Tri-Star Bearish | number |

---

## Pivot Points

| Column name | Display name | Type |
|-------------|--------------|------|
| Pivot.M.Classic.Middle | Classic Pivot P | number |
| Pivot.M.Classic.R1 | Classic R1 | number |
| Pivot.M.Classic.R2 | Classic R2 | number |
| Pivot.M.Classic.R3 | Classic R3 | number |
| Pivot.M.Classic.S1 | Classic S1 | number |
| Pivot.M.Classic.S2 | Classic S2 | number |
| Pivot.M.Classic.S3 | Classic S3 | number |
| Pivot.M.Fibonacci.Middle | Fibonacci Pivot P | number |
| Pivot.M.Fibonacci.R1 | Fibonacci R1 | number |
| Pivot.M.Fibonacci.R2 | Fibonacci R2 | number |
| Pivot.M.Fibonacci.R3 | Fibonacci R3 | number |
| Pivot.M.Fibonacci.S1 | Fibonacci S1 | number |
| Pivot.M.Fibonacci.S2 | Fibonacci S2 | number |
| Pivot.M.Fibonacci.S3 | Fibonacci S3 | number |
| Pivot.M.Camarilla.Middle | Camarilla Pivot P | number |
| Pivot.M.Camarilla.R1 | Camarilla R1 | number |
| Pivot.M.Camarilla.R2 | Camarilla R2 | number |
| Pivot.M.Camarilla.R3 | Camarilla R3 | number |
| Pivot.M.Camarilla.S1 | Camarilla S1 | number |
| Pivot.M.Camarilla.S2 | Camarilla S2 | number |
| Pivot.M.Camarilla.S3 | Camarilla S3 | number |
| Pivot.M.Woodie.Middle | Woodie Pivot P | number |
| Pivot.M.Woodie.R1 | Woodie R1 | number |
| Pivot.M.Woodie.R2 | Woodie R2 | number |
| Pivot.M.Woodie.R3 | Woodie R3 | number |
| Pivot.M.Woodie.S1 | Woodie S1 | number |
| Pivot.M.Woodie.S2 | Woodie S2 | number |
| Pivot.M.Woodie.S3 | Woodie S3 | number |
| Pivot.M.Demark.Middle | DeMark Pivot P | number |
| Pivot.M.Demark.R1 | DeMark R1 | number |
| Pivot.M.Demark.S1 | DeMark S1 | number |

---

## Fundamental — Income Statement

| Column name | Display name | Type |
|-------------|--------------|------|
| total_revenue | Total Revenue (FY) | fundamental_price |
| total_revenue_fq | Total Revenue (MRQ) | fundamental_price |
| total_revenue_ttm | Total Revenue (TTM) | fundamental_price |
| gross_profit | Gross Profit (FY) | fundamental_price |
| gross_profit_fq | Gross Profit (MRQ) | fundamental_price |
| gross_margin | Gross Margin (TTM) | percent |
| gross_profit_margin_fy | Gross Margin (FY) | percent |
| ebitda | EBITDA (TTM) | fundamental_price |
| ebitda_fy | EBITDA (FY) | fundamental_price |
| ebitda_fq | EBITDA (MRQ) | fundamental_price |
| ebitda_margin_ttm | EBITDA Margin (TTM) | percent |
| oper_income_fy | Operating Income (FY) | fundamental_price |
| operating_margin | Operating Margin (TTM) | percent |
| oper_income_margin_fy | Operating Margin (FY) | percent |
| net_income | Net Income (FY) | fundamental_price |
| net_income_fq | Net Income (MRQ) | fundamental_price |
| after_tax_margin | Net Margin (TTM) | percent |
| net_income_bef_disc_oper_margin_fy | Net Margin (FY) | percent |
| pre_tax_margin | Pretax Margin (TTM) | percent |
| earnings_per_share_basic_ttm | Basic EPS (TTM) | fundamental_price |
| basic_eps_net_income | Basic EPS (FY) | fundamental_price |
| earnings_per_share_diluted_ttm | Diluted EPS (TTM) | fundamental_price |
| last_annual_eps | Diluted EPS (FY) | fundamental_price |
| earnings_per_share_fq | Diluted EPS (MRQ) | fundamental_price |
| earnings_per_share_forecast_next_fq | EPS Forecast (next MRQ) | fundamental_price |
| earnings_release_date | Recent Earnings Date | time |
| earnings_release_next_date | Upcoming Earnings Date | time |

---

## Fundamental — Balance Sheet

| Column name | Display name | Type |
|-------------|--------------|------|
| total_assets | Total Assets (MRQ) | fundamental_price |
| total_current_assets | Total Current Assets (MRQ) | fundamental_price |
| cash_n_short_term_invest_fq | Cash & Short-term Investments (MRQ) | fundamental_price |
| cash_n_equivalents_fq | Cash & Equivalents (MRQ) | fundamental_price |
| total_debt | Total Debt (MRQ) | fundamental_price |
| total_liabilities_fq | Total Liabilities (MRQ) | fundamental_price |
| shrhldrs_equity_fq | Shareholders' Equity (MRQ) | fundamental_price |
| net_debt | Net Debt (MRQ) | fundamental_price |
| goodwill | Goodwill | fundamental_price |
| current_ratio | Current Ratio (MRQ) | number |
| quick_ratio | Quick Ratio (MRQ) | number |
| debt_to_equity | Debt to Equity (MRQ) | number |
| enterprise_value_fq | Enterprise Value (MRQ) | fundamental_price |

---

## Fundamental — Cash Flow

| Column name | Display name | Type |
|-------------|--------------|------|
| free_cash_flow | Free Cash Flow (FY) | fundamental_price |
| free_cash_flow_margin_ttm | Free Cash Flow Margin (TTM) | percent |
| cash_f_operating_activities_fy | Cash from Operations (FY) | fundamental_price |
| cash_f_investing_activities_fy | Cash from Investing (FY) | fundamental_price |
| cash_f_financing_activities_fy | Cash from Financing (FY) | fundamental_price |
| capital_expenditures_fy | CapEx (FY) | fundamental_price |
| dividends_paid | Dividends Paid (FY) | fundamental_price |

---

## Fundamental — Valuation Ratios

| Column name | Display name | Type |
|-------------|--------------|------|
| market_cap_basic | Market Capitalization | fundamental_price |
| price_earnings_ttm | P/E Ratio (TTM) | number |
| price_book_ratio | Price to Book (FY) | number |
| price_book_fq | Price to Book (MRQ) | number |
| price_revenue_ttm | Price to Revenue (TTM) | number |
| price_sales_ratio | Price to Sales (FY) | number |
| price_free_cash_flow_ttm | Price to Free Cash Flow (TTM) | number |
| enterprise_value_ebitda_ttm | EV/EBITDA (TTM) | number |
| return_on_equity | Return on Equity (TTM) | percent |
| return_on_assets | Return on Assets (TTM) | percent |
| return_on_invested_capital | Return on Invested Capital (TTM) | percent |
| total_revenue_yoy_growth_fy | Revenue YoY Growth (FY) | percent |
| net_income_yoy_growth_fy | Net Income YoY Growth (FY) | percent |
| ebitda_yoy_growth_fy | EBITDA YoY Growth (FY) | percent |
| piotroski_f_score_ttm | Piotroski F-Score (TTM) | number |

---

## Fundamental — Dividends

| Column name | Display name | Type |
|-------------|--------------|------|
| dividends_yield | Dividend Yield | number |
| dividend_yield_recent | Dividend Yield (Forward) | number |
| dps_common_stock_prim_issue_fy | Dividends per Share (FY) | fundamental_price |
| dividends_per_share_fq | Dividends per Share (MRQ) | fundamental_price |
| dividend_payout_ratio_ttm | Dividend Payout Ratio (TTM) | percent |
| ex_dividend_date_recent | Ex-Dividend Date (recent) | time |
| ex_dividend_date_upcoming | Ex-Dividend Date (upcoming) | time |

---

## Fundamental — Company Info

| Column name | Display name | Type |
|-------------|--------------|------|
| number_of_employees | Number of Employees | number |
| number_of_shareholders | Number of Shareholders | number |
| total_shares_outstanding_fundamental | Total Shares Outstanding | number |
| float_shares_outstanding | Shares Float | number |
| last_annual_revenue | Last Year Revenue (FY) | fundamental_price |

---

## Index Membership

| Column name | Display name | Type |
|-------------|--------------|------|
| indexes | Index membership list | interface |
| index | Index (text) | text |
| index_id | Internal index identifier | text |
| index_priority | Index sort priority | number |
| index_provider | Index provider name | text |

---

## Timeframe Suffix Convention

Fields that represent price, indicator, or volume data can be suffixed with
`|<timeframe>` to request a specific resolution:

| Suffix | Timeframe |
|--------|-----------|
| *(none)* | 1 Day (default) |
| `\|1` | 1 Minute |
| `\|5` | 5 Minutes |
| `\|15` | 15 Minutes |
| `\|30` | 30 Minutes |
| `\|60` | 1 Hour |
| `\|120` | 2 Hours |
| `\|240` | 4 Hours |
| `\|1W` | 1 Week |
| `\|1M` | 1 Month |

**Example:** `close|60` is the 1-hour close. `MACD.macd|1` is the 1-minute MACD.

> **Note:** This catalogue covers the primary named fields. The full page at
> `https://shner-elmo.github.io/TradingView-Screener/fields/stocks.html` lists
> 300+ additional fields (variant timeframes, extended metrics, fund/ETF
> specific fields) that are less commonly used. Consult that URL for the
> complete list if a field is not found here.
```

**Acceptance criteria:**
- [ ] File exists at `.github/skills/tradingview-screener/references/fields.md`.
- [ ] All category headings are present: Core Identity & Market Info, Price & OHLCV, Price Range & Performance, Moving Averages, Technical Indicators & Oscillators, Candlestick Patterns, Pivot Points, Fundamental — Income Statement, Fundamental — Balance Sheet, Fundamental — Cash Flow, Fundamental — Valuation Ratios, Fundamental — Dividends, Fundamental — Company Info, Index Membership, Timeframe Suffix Convention.
- [ ] `ticker`, `name`, `exchange`, `market`, `close`, `volume`, `market_cap_basic`, `price_earnings_ttm`, `is_primary`, `indexes`, `RSI`, `MACD.macd` are all present in the file.
- [ ] All production field names used in `tradingview_bist.py` (`name`, `exchange`, `market`, `is_primary`, `indexes`) appear in the catalogue.

**Commit:** `feat(issue-42): add comprehensive field reference catalogue to references/fields.md`

---

### Story 4 — Add gotchas & edge-case reference

**Files created:**
- `.github/skills/tradingview-screener/references/gotchas.md`

**Required content** (all six items are mandatory):

1. **Ticker prefix is always `EXCHANGE:SYMBOL`**
   - All values in `df['ticker']` are prefixed. There is no bare `AAPL` — only `NASDAQ:AAPL`. Never pass a bare symbol to `.where()` filters that compare against `ticker`.
   - To strip: `symbol.replace('BIST:', '', 1)` or use `.split(':')[-1]`.

2. **`is_primary == True` filter is required for BIST**
   - BIST stocks can appear multiple times (e.g. `BIST:THYAO` and `BIST:THYAOM` as a participation certificate). Without the filter, `len(df)` may be 2–3× the expected constituent count.
   - Always add `.where(Column('is_primary') == True)` when querying BIST.

3. **`market_cap_basic` is `NaN` for ETFs and certificates**
   - Non-equity instruments (ETFs, participation certificates, warrants) return `NaN` for `market_cap_basic` even when the field is in `.select()`.
   - Filter these out with `.where(Column('type') == 'stock')` if hard values are needed.

4. **`raw_count` always exceeds `len(df)` when `.limit()` is applied**
   - `raw_count` is the total number of server-side matches before limiting.
   - `len(df)` is the number of rows returned (capped by `.limit()`).
   - Do not treat `raw_count == len(df)` as a postcondition; it is virtually never true.

5. **No authentication required for screener queries**
   - `Query().get_scanner_data()` works without a TradingView account, cookies, or any environment variables.
   - Data will be `delayed_streaming_900` (15-minute delay) for most exchanges without authentication.
   - Real-time data requires passing browser cookies via `rookiepy` — this is out of scope for Tayfin.

6. **`.get_scanner_data()` is a live HTTP call — non-deterministic**
   - Results change between runs as market data updates.
   - Never rely on exact row count or specific values in tests. Use column set and type assertions instead.
   - There is no local cache or offline mode. An active internet connection is required.

**Acceptance criteria:**
- [ ] All 6 gotchas are present, titled, and contain at least one concrete actionable statement.
- [ ] Gotcha 2 (`is_primary`) references the production code pattern.
- [ ] Gotcha 3 mentions `NaN` and the `type` filter workaround.

**Commit:** `feat(issue-42): add gotchas and edge-case reference to references/gotchas.md`

---

### Story 5 — Add annotated usage examples

**Files created:**
- `.github/skills/tradingview-screener/references/examples.md`

**Required examples (4 total):**

**Example A — BIST XU100 index constituents** (production pattern)
```python
from tradingview_screener import Query, Column

raw_count, df = (
    Query()
    .set_markets('turkey')
    .set_index('SYML:BIST;XU100')
    .select('name', 'exchange', 'market', 'is_primary', 'indexes')
    .where(Column('is_primary') == True)
    .limit(5000)
    .get_scanner_data()
)
# Expected columns: ticker, name, exchange, market, is_primary, indexes
# Example row: {"ticker": "BIST:AKBNK", "name": "AKBNK", "exchange": "BIST",
#               "market": "turkey", "is_primary": True, "indexes": [...]}
```
Annotation: explain what `SYML:BIST;XU100` means, why `limit(5000)` is used.

**Example B — Top 20 BIST stocks by market cap**
```python
raw_count, df = (
    Query()
    .set_markets('turkey')
    .select('name', 'close', 'volume', 'market_cap_basic', 'sector')
    .where(
        Column('is_primary') == True,
        Column('type') == 'stock',
    )
    .order_by('market_cap_basic', ascending=False)
    .limit(20)
    .get_scanner_data()
)
# Expected columns: ticker, name, close, volume, market_cap_basic, sector
```
Annotation: explain `.order_by()` combined with `.limit()` gives true top-N.

**Example C — BIST stocks with P/E < 10 and positive net income**
```python
raw_count, df = (
    Query()
    .set_markets('turkey')
    .select('name', 'close', 'price_earnings_ttm', 'net_income', 'return_on_equity')
    .where(
        Column('is_primary') == True,
        Column('type') == 'stock',
        Column('price_earnings_ttm') < 10,
        Column('price_earnings_ttm') > 0,
        Column('net_income') > 0,
    )
    .order_by('market_cap_basic', ascending=False)
    .limit(50)
    .get_scanner_data()
)
```
Annotation: note that `price_earnings_ttm > 0` is required to exclude negative-earnings stocks.

**Example D — Multi-market query (USA + Turkey)**
```python
raw_count, df = (
    Query()
    .set_markets('america', 'turkey')
    .select('name', 'close', 'market_cap_basic', 'country', 'exchange')
    .where(
        Column('is_primary') == True,
        Column('market_cap_basic') > 1_000_000_000,
    )
    .order_by('market_cap_basic', ascending=False)
    .limit(100)
    .get_scanner_data()
)
# df['exchange'] will contain both NASDAQ/NYSE and BIST values
```
Annotation: multi-market queries use multiple string args to `.set_markets()`.

**Acceptance criteria:**
- [ ] All 4 examples are present with Python code blocks and annotations.
- [ ] Each example states its expected `df.columns` set.
- [ ] Each example has at least one annotation sentence explaining a non-obvious choice.

**Commit:** `feat(issue-42): add annotated usage examples to references/examples.md`

---

### Story 6 — Create `scripts/` directory with smoke test and examples

**Files created:**
- `.github/skills/tradingview-screener/scripts/smoke_test.py`
- `.github/skills/tradingview-screener/scripts/example_bist_xu100.py`
- `.github/skills/tradingview-screener/scripts/example_top_by_market_cap.py`

**`smoke_test.py` requirements:**
- Imports `Query` and `Column` from `tradingview_screener`.
- Executes a minimal live query (e.g. `Query().select('name', 'close').limit(5).get_scanner_data()`).
- Asserts that the return value is a `(int, pd.DataFrame)` tuple.
- Asserts `len(df) > 0`.
- Asserts `'ticker'` is in `df.columns`.
- Prints a confirmation line: `"smoke_test OK — {len(df)} rows returned"`.
- Exits with code 0 on success, raises on failure.
- Running `python smoke_test.py` from the `scripts/` directory must complete without error.

**`example_bist_xu100.py` requirements:**
- Reproduces the production BIST XU100 query from `tradingview_bist.py` (Example A from Story 5).
- Prints the first 5 rows of the resulting DataFrame.
- Prints the `raw_count`.

**`example_top_by_market_cap.py` requirements:**
- Reproduces Example B from Story 5 (top 20 BIST by market cap).
- Prints the resulting DataFrame.

**Acceptance criteria:**
- [ ] `python scripts/smoke_test.py` passes (exits 0) when run from the skill root.
- [ ] All three scripts import cleanly (`python -c "import ast; ast.parse(open('scripts/smoke_test.py').read())`).
- [ ] Scripts contain no hardcoded credentials, cookies, or API keys.

**Commit:** `feat(issue-42): add scripts directory with smoke test and working examples`

---

### Story 7 — Delete obsolete knowledge guide

**Files deleted:**
- `docs/tradingview_screener/TRADINGVIEW_SCREENER_GUIDE.md`

**Rationale:** This file documents only `get_all_symbols()` (Issue #41 spike notes) and is now superseded by the new skill, which documents the `Query()` API. Retaining it risks confusing downstream agents with outdated patterns.

**Acceptance criteria:**
- [ ] `docs/tradingview_screener/TRADINGVIEW_SCREENER_GUIDE.md` does not exist.
- [ ] No other file in `docs/tradingview_screener/` is modified or deleted (if the directory becomes empty after deletion, it may be left empty or removed — developer's discretion).
- [ ] `git rm` is used (not `rm`) so the deletion is tracked in the commit.

**Commit:** `feat(issue-42): delete obsolete get_all_symbols knowledge guide`

---

### Story 8 — Final review, self-validation, and `development_notes.md`

**Files created:**
- `.github/issues/42/development_notes.md`

**Self-validation checklist the developer must run before writing `development_notes.md`:**

```
[ ] git branch shows feature/issue-42-tradingview-screener-skill
[ ] wc -l .github/skills/tradingview-screener/SKILL.md          → ≤ 500
[ ] wc -c on SKILL.md description field                          → ≤ 1024
[ ] python -c "import yaml; ..." on SKILL.md frontmatter         → no exception
[ ] SKILL.md contains references to fields.md, gotchas.md, examples.md
[ ] references/fields.md exists and contains all 15 category headings
[ ] references/gotchas.md exists and contains all 6 gotchas
[ ] references/examples.md exists and contains all 4 examples
[ ] scripts/smoke_test.py exits 0
[ ] docs/tradingview_screener/TRADINGVIEW_SCREENER_GUIDE.md does not exist
[ ] git log --oneline shows exactly 8 commits on this branch beyond the plan commit
[ ] No files outside .github/skills/tradingview-screener/ or docs/tradingview_screener/ 
    were modified (verified with git diff main -- . ':(exclude).github/' ':(exclude)docs/tradingview_screener/')
```

**`development_notes.md` must contain:**
1. Branch name confirmation.
2. Stories completed (list with commit SHAs).
3. Any deviations from this implementation plan (if none, state "No deviations").
4. Smoke test output (copy of the `smoke_test OK — N rows returned` line).
5. Open items or follow-up debt (e.g. upgrade `tradingview-screener` from 2.5.0 to latest in `requirements.txt`).

**Acceptance criteria:**
- [ ] All self-validation checks pass.
- [ ] `development_notes.md` contains all 5 required sections.
- [ ] Smoke test output is pasted into `development_notes.md`.

**Commit:** `feat(issue-42): self-validation pass and development_notes.md`

---

## 4. Full Story Summary Table

| # | Story | Files | Commit |
|---|-------|-------|--------|
| 1 | Scaffold `SKILL.md` stub | `SKILL.md` (create) | `feat(issue-42): scaffold tradingview-screener skill directory and SKILL.md stub` |
| 2 | Write core `SKILL.md` body | `SKILL.md` (update) | `feat(issue-42): write core SKILL.md instructions and query API reference` |
| 3 | Add field catalogue | `references/fields.md` (create) | `feat(issue-42): add comprehensive field reference catalogue to references/fields.md` |
| 4 | Add gotchas reference | `references/gotchas.md` (create) | `feat(issue-42): add gotchas and edge-case reference to references/gotchas.md` |
| 5 | Add usage examples | `references/examples.md` (create) | `feat(issue-42): add annotated usage examples to references/examples.md` |
| 6 | Add scripts/ | `scripts/smoke_test.py`, `scripts/example_bist_xu100.py`, `scripts/example_top_by_market_cap.py` (create) | `feat(issue-42): add scripts directory with smoke test and working examples` |
| 7 | Delete obsolete guide | `docs/tradingview_screener/TRADINGVIEW_SCREENER_GUIDE.md` (delete) | `feat(issue-42): delete obsolete get_all_symbols knowledge guide` |
| 8 | Final review | `.github/issues/42/development_notes.md` (create) | `feat(issue-42): self-validation pass and development_notes.md` |

---

## 5. Lead Developer Validation Steps

After the developer agent completes all stories, perform the following checks
before marking the issue as done.

### 5.1 Branch & commit hygiene
```bash
git log --oneline feature/issue-42-tradingview-screener-skill
```
Expected: 9 commits (1 plan + 8 stories). All commit messages match the table
in Section 4.

### 5.2 SKILL.md spec compliance
```bash
# Line count
wc -l .github/skills/tradingview-screener/SKILL.md
# Must be ≤ 500

# Frontmatter validity
python3 -c "
import yaml
text = open('.github/skills/tradingview-screener/SKILL.md').read()
fm = text.split('---')[1]
d = yaml.safe_load(fm)
assert d['name'] == 'tradingview-screener', f'bad name: {d[\"name\"]}'
assert len(d['description']) <= 1024, f'description too long: {len(d[\"description\"])}'
assert set(d.keys()) == {'name','description'}, f'unexpected keys: {d.keys()}'
print('SKILL.md frontmatter OK')
"
```

### 5.3 Field catalogue completeness spot-check
```bash
# All production fields from tradingview_bist.py must be present
for field in name exchange market is_primary indexes; do
  grep -q "| $field " .github/skills/tradingview-screener/references/fields.md \
    && echo "OK: $field" || echo "MISSING: $field"
done
```

### 5.4 Smoke test
```bash
cd .github/skills/tradingview-screener
python scripts/smoke_test.py
# Expected output: smoke_test OK — N rows returned
# Expected exit code: 0
```

### 5.5 Deleted file confirmation
```bash
ls docs/tradingview_screener/TRADINGVIEW_SCREENER_GUIDE.md 2>&1
# Expected: No such file or directory
```

### 5.6 No unintended modifications
```bash
git diff main --name-only | grep -v "^\.github/skills/tradingview-screener" \
  | grep -v "^docs/tradingview_screener" \
  | grep -v "^\.github/issues/42"
# Expected: no output (no files outside the three allowed paths were changed)
```

---

## 6. Follow-up Technical Debt

The following items are out of scope for Issue #42 but must be tracked:

1. **Upgrade `tradingview-screener` from 2.5.0 to latest (≥3.1.0)** in
   `tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt`. The library has
   had breaking changes between 2.x and 3.x; validate that
   `TradingViewBistDiscoveryProvider` still works after upgrade.

2. **Extend the field catalogue** once the library is upgraded — new fields
   may be available in 3.x that are not listed in this version.
