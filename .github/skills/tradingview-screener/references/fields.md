# TradingView Screener — Field Reference Catalogue

> **Source:** https://shner-elmo.github.io/TradingView-Screener/fields/stocks.html
> **Last verified:** 2026-04-19
>
> Use this file to look up exact column name strings before writing any
> `.select()` or `.where()` call. Column names are **case-sensitive**.
>
> Fields that represent price or indicator data support a timeframe suffix:
> `close|1` (1 min), `close|5` (5 min), `close|60` (1h), `close` (1 day, default),
> `close|1W` (1 week). See the **Timeframe Suffix Convention** section at the bottom.
>
> The `ticker` column is always returned by `.get_scanner_data()` regardless of
> whether it appears in `.select()`.

---

## Core Identity & Market Info

| Column name | Display name | Type |
|-------------|--------------|------|
| ticker | Symbol (always returned implicitly) | text |
| name | Symbol name / ticker code | text |
| exchange | Exchange (e.g. `BIST`, `NASDAQ`, `NYSE`) | text |
| market | Market identifier (e.g. `turkey`, `america`) | text |
| type | Symbol type (`stock`, `fund`, `dr`, `structured`) | text |
| is_primary | Primary listing flag | bool |
| active_symbol | Active in current trading day | bool |
| country | Region / country code | text |
| currency | Quote currency (e.g. `TRY`, `USD`) | text |
| sector | Sector classification | text |
| industry | Industry classification | text |
| submarket | Submarket identifier | text |
| description | Full company name / description | text |
| logoid | TradingView logo identifier | text |
| update_mode | Data update mode (`streaming`, `delayed_streaming_900`) | text |
| asset_class | Asset class descriptor | text |
| typespecs | Type specification set | set |
| kind | Symbol kind | text |

---

## Price & OHLCV

| Column name | Display name | Type |
|-------------|--------------|------|
| open | Open | price |
| high | High | price |
| low | Low | price |
| close | Close / Current Price (daily) | price |
| volume | Volume | number |
| VWAP | Volume Weighted Average Price | number |
| change | Change % | percent |
| change_abs | Change (absolute) | price |
| change_from_open | Change from Open % | percent |
| change_from_open_abs | Change from Open (absolute) | price |
| gap | Gap % | percent |
| gap_up | Gap Up % | percent |
| gap_up_abs | Gap Up (absolute) | price |
| gap_down | Gap Down % | percent |
| gap_down_abs | Gap Down (absolute) | price |
| Value.Traded | Volume × Price | number |
| relative_volume_10d_calc | Relative Volume (10-day avg) | number |
| relative_volume | Relative Volume | number |
| average_volume_10d_calc | Average Volume (10-day) | number |
| average_volume_30d_calc | Average Volume (30-day) | number |
| average_volume_60d_calc | Average Volume (60-day) | number |
| average_volume_90d_calc | Average Volume (90-day) | number |
| average_volume | Average Volume | number |
| volume_change | Volume Change % | percent |
| volume_change_abs | Volume Change (absolute) | number |
| premarket_open | Pre-market Open | price |
| premarket_high | Pre-market High | price |
| premarket_low | Pre-market Low | price |
| premarket_close | Pre-market Close | price |
| premarket_volume | Pre-market Volume | number |
| premarket_change | Pre-market Change % | percent |
| premarket_change_abs | Pre-market Change (absolute) | price |
| premarket_gap | Pre-market Gap % | percent |
| premarket_change_from_open | Pre-market Change from Open % | percent |
| postmarket_open | Post-market Open | price |
| postmarket_high | Post-market High | price |
| postmarket_low | Post-market Low | price |
| postmarket_close | Post-market Close | price |
| postmarket_volume | Post-market Volume | number |
| postmarket_change | Post-market Change % | percent |
| postmarket_change_abs | Post-market Change (absolute) | price |
| rtc | Real-time close | price |

---

## Price Range & Performance

| Column name | Display name | Type |
|-------------|--------------|------|
| price_52_week_high | 52-Week High | number |
| price_52_week_low | 52-Week Low | number |
| price_52_week_high_date | 52-Week High Date | time |
| price_52_week_low_date | 52-Week Low Date | time |
| High.1M | 1-Month High | number |
| Low.1M | 1-Month Low | number |
| High.3M | 3-Month High | number |
| Low.3M | 3-Month Low | number |
| High.6M | 6-Month High | number |
| Low.6M | 6-Month Low | number |
| High.All | All-Time High | number |
| Low.All | All-Time Low | number |
| High.5D | 5-Day High | number |
| Low.5D | 5-Day Low | number |
| Perf.5D | 5-Day Performance | number |
| Perf.W | Weekly Performance | number |
| Perf.1M | Monthly Performance | number |
| Perf.3M | 3-Month Performance | number |
| Perf.6M | 6-Month Performance | number |
| Perf.Y | Yearly Performance | number |
| Perf.YTD | Year-to-Date Performance | number |
| Perf.5Y | 5-Year Performance | number |
| Perf.3Y | 3-Year Performance | number |
| Perf.10Y | 10-Year Performance | number |
| Perf.All | All-Time Performance | number |
| beta_1_year | 1-Year Beta | number |
| beta_3_year | 3-Year Beta | number |
| beta_5_year | 5-Year Beta | number |
| Volatility.D | Daily Volatility | number |
| Volatility.W | Weekly Volatility | number |
| Volatility.M | Monthly Volatility | number |
| ADR | Average Day Range (14) | number |
| ADRP | Average Day Range % | number |
| all_time_high | All-Time High (absolute) | price |
| all_time_low | All-Time Low (absolute) | price |
| low_after_high_all_change | Low After All-Time High Change % | percent |
| low_after_high_all_change_abs | Low After All-Time High Change | price |

---

## Moving Averages

| Column name | Display name | Type |
|-------------|--------------|------|
| SMA5 | Simple Moving Average (5) | number |
| SMA10 | Simple Moving Average (10) | number |
| SMA20 | Simple Moving Average (20) | number |
| SMA30 | Simple Moving Average (30) | number |
| SMA50 | Simple Moving Average (50) | number |
| SMA100 | Simple Moving Average (100) | number |
| SMA200 | Simple Moving Average (200) | number |
| EMA5 | Exponential Moving Average (5) | number |
| EMA10 | Exponential Moving Average (10) | number |
| EMA20 | Exponential Moving Average (20) | number |
| EMA30 | Exponential Moving Average (30) | number |
| EMA50 | Exponential Moving Average (50) | number |
| EMA100 | Exponential Moving Average (100) | number |
| EMA200 | Exponential Moving Average (200) | number |
| HullMA9 | Hull Moving Average (9) | number |
| HullMA20 | Hull Moving Average (20) | number |
| HullMA200 | Hull Moving Average (200) | number |
| VWMA | Volume Weighted Moving Average (20) | number |
| Recommend.MA | Moving Averages Technical Rating | number |

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
| Stoch.RSI.K | Stochastic RSI Fast (3, 3, 14, 14) | number |
| Stoch.RSI.D | Stochastic RSI Slow (3, 3, 14, 14) | number |
| ADX | Average Directional Index (14) | number |
| ADX+DI | Positive Directional Indicator (14) | number |
| ADX-DI | Negative Directional Indicator (14) | number |
| ATR | Average True Range (14) | number |
| ATRP | Average True Range % | number |
| CCI20 | Commodity Channel Index (20) | number |
| AO | Awesome Oscillator | number |
| Mom | Momentum (10) | number |
| ROC | Rate of Change (9) | number |
| BB.upper | Bollinger Upper Band (20) | number |
| BB.lower | Bollinger Lower Band (20) | number |
| BB.basis | Bollinger Basis (20) | number |
| BB.basis_50 | Bollinger Basis (50) | number |
| BB.upper_50 | Bollinger Upper Band (50) | number |
| BB.lower_50 | Bollinger Lower Band (50) | number |
| KltChnl.upper | Keltner Channel Upper (20) | number |
| KltChnl.lower | Keltner Channel Lower (20) | number |
| KltChnl.basis | Keltner Channel Basis | number |
| DonchCh20.Upper | Donchian Channel Upper (20) | number |
| DonchCh20.Lower | Donchian Channel Lower (20) | number |
| DonchCh20.Middle | Donchian Channel Middle (20) | number |
| Ichimoku.CLine | Ichimoku Conversion Line (9, 26, 52, 26) | number |
| Ichimoku.BLine | Ichimoku Base Line (9, 26, 52, 26) | number |
| Ichimoku.Lead1 | Ichimoku Leading Span A (9, 26, 52, 26) | number |
| Ichimoku.Lead2 | Ichimoku Leading Span B (9, 26, 52, 26) | number |
| P.SAR | Parabolic SAR | number |
| ChaikinMoneyFlow | Chaikin Money Flow (20) | number |
| MoneyFlow | Money Flow (14) | number |
| UO | Ultimate Oscillator (7, 14, 28) | number |
| BBPower | Bull Bear Power | number |
| W.R | Williams Percent Range (14) | number |
| Aroon.Up | Aroon Up (14) | number |
| Aroon.Down | Aroon Down (14) | number |
| Recommend.All | Technical Rating (composite) | number |
| Recommend.Other | Oscillators Rating | number |
| Rec.BBPower | BB Power Rating | number |
| Rec.HullMA9 | Hull MA (9) Rating | number |
| Rec.Ichimoku | Ichimoku Rating | number |
| Rec.Stoch.RSI | Stochastic RSI Rating | number |
| Rec.UO | Ultimate Oscillator Rating | number |
| Rec.VWMA | VWMA Rating | number |
| Rec.WR | Williams %R Rating | number |

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
| Pivot.M.Classic.R1 | Classic Pivot R1 | number |
| Pivot.M.Classic.R2 | Classic Pivot R2 | number |
| Pivot.M.Classic.R3 | Classic Pivot R3 | number |
| Pivot.M.Classic.S1 | Classic Pivot S1 | number |
| Pivot.M.Classic.S2 | Classic Pivot S2 | number |
| Pivot.M.Classic.S3 | Classic Pivot S3 | number |
| Pivot.M.Fibonacci.Middle | Fibonacci Pivot P | number |
| Pivot.M.Fibonacci.R1 | Fibonacci Pivot R1 | number |
| Pivot.M.Fibonacci.R2 | Fibonacci Pivot R2 | number |
| Pivot.M.Fibonacci.R3 | Fibonacci Pivot R3 | number |
| Pivot.M.Fibonacci.S1 | Fibonacci Pivot S1 | number |
| Pivot.M.Fibonacci.S2 | Fibonacci Pivot S2 | number |
| Pivot.M.Fibonacci.S3 | Fibonacci Pivot S3 | number |
| Pivot.M.Camarilla.Middle | Camarilla Pivot P | number |
| Pivot.M.Camarilla.R1 | Camarilla Pivot R1 | number |
| Pivot.M.Camarilla.R2 | Camarilla Pivot R2 | number |
| Pivot.M.Camarilla.R3 | Camarilla Pivot R3 | number |
| Pivot.M.Camarilla.S1 | Camarilla Pivot S1 | number |
| Pivot.M.Camarilla.S2 | Camarilla Pivot S2 | number |
| Pivot.M.Camarilla.S3 | Camarilla Pivot S3 | number |
| Pivot.M.Woodie.Middle | Woodie Pivot P | number |
| Pivot.M.Woodie.R1 | Woodie Pivot R1 | number |
| Pivot.M.Woodie.R2 | Woodie Pivot R2 | number |
| Pivot.M.Woodie.R3 | Woodie Pivot R3 | number |
| Pivot.M.Woodie.S1 | Woodie Pivot S1 | number |
| Pivot.M.Woodie.S2 | Woodie Pivot S2 | number |
| Pivot.M.Woodie.S3 | Woodie Pivot S3 | number |
| Pivot.M.Demark.Middle | DeMark Pivot P | number |
| Pivot.M.Demark.R1 | DeMark Pivot R1 | number |
| Pivot.M.Demark.S1 | DeMark Pivot S1 | number |

---

## Fundamental — Income Statement

| Column name | Display name | Type |
|-------------|--------------|------|
| total_revenue | Total Revenue (FY) | fundamental_price |
| total_revenue_fq | Total Revenue (MRQ) | fundamental_price |
| total_revenue_ttm | Total Revenue (TTM) | fundamental_price |
| total_revenue_fh | Total Revenue (FH) | fundamental_price |
| total_revenue_yoy_growth_fy | Revenue YoY Growth (FY) | percent |
| total_revenue_qoq_growth_fq | Revenue QoQ Growth (MRQ) | percent |
| total_revenue_yoy_growth_fq | Revenue YoY Growth (MRQ) | percent |
| total_revenue_yoy_growth_ttm | Revenue YoY Growth (TTM) | percent |
| total_revenue_cagr_5y | Revenue 5Y CAGR | percent |
| total_revenue_5y_growth_fy | Revenue 5Y Growth (FY) | percent |
| last_annual_revenue | Last Year Revenue (FY) | fundamental_price |
| gross_profit | Gross Profit (FY) | fundamental_price |
| gross_profit_fq | Gross Profit (MRQ) | fundamental_price |
| gross_profit_fh | Gross Profit (FH) | fundamental_price |
| gross_profit_ttm | Gross Profit (TTM) | fundamental_price |
| gross_margin | Gross Margin (TTM) | percent |
| gross_profit_margin_fy | Gross Margin (FY) | percent |
| gross_margin_fy | Gross Margin (FY) alt | percent |
| gross_margin_ttm | Gross Margin (TTM) alt | percent |
| ebitda | EBITDA (TTM) | fundamental_price |
| ebitda_fy | EBITDA (FY) | fundamental_price |
| ebitda_fq | EBITDA (MRQ) | fundamental_price |
| ebitda_fh | EBITDA (FH) | fundamental_price |
| ebitda_ttm | EBITDA (TTM) alt | fundamental_price |
| ebitda_margin_fy | EBITDA Margin (FY) | percent |
| ebitda_margin_ttm | EBITDA Margin (TTM) | percent |
| ebitda_yoy_growth_fy | EBITDA YoY Growth (FY) | percent |
| ebitda_qoq_growth_fq | EBITDA QoQ Growth (MRQ) | percent |
| ebitda_yoy_growth_fq | EBITDA YoY Growth (MRQ) | percent |
| ebitda_yoy_growth_ttm | EBITDA YoY Growth (TTM) | percent |
| oper_income_fy | Operating Income (FY) | fundamental_price |
| oper_income_fq | Operating Income (MRQ) | fundamental_price |
| oper_income_fh | Operating Income (FH) | fundamental_price |
| oper_income_ttm | Operating Income (TTM) | fundamental_price |
| operating_margin | Operating Margin (TTM) | percent |
| oper_income_margin_fy | Operating Margin (FY) | percent |
| operating_margin_fy | Operating Margin (FY) alt | percent |
| operating_margin_ttm | Operating Margin (TTM) alt | percent |
| net_income | Net Income (FY) | fundamental_price |
| net_income_fq | Net Income (MRQ) | fundamental_price |
| net_income_fh | Net Income (FH) | fundamental_price |
| net_income_ttm | Net Income (TTM) | fundamental_price |
| after_tax_margin | Net Margin (TTM) | percent |
| net_margin | Net Margin | percent |
| net_margin_fy | Net Margin (FY) | percent |
| net_margin_ttm | Net Margin (TTM) alt | percent |
| net_income_bef_disc_oper_margin_fy | Net Margin (FY) alt | percent |
| pre_tax_margin | Pretax Margin (TTM) | percent |
| pre_tax_margin_ttm | Pretax Margin (TTM) alt | percent |
| net_income_yoy_growth_fy | Net Income YoY Growth (FY) | percent |
| net_income_qoq_growth_fq | Net Income QoQ Growth (MRQ) | percent |
| net_income_yoy_growth_fq | Net Income YoY Growth (MRQ) | percent |
| net_income_yoy_growth_ttm | Net Income YoY Growth (TTM) | percent |
| net_income_cagr_5y | Net Income 5Y CAGR | percent |
| earnings_per_share_basic_ttm | Basic EPS (TTM) | fundamental_price |
| basic_eps_net_income | Basic EPS (FY) | fundamental_price |
| earnings_per_share_basic_fq | Basic EPS (MRQ) | fundamental_price |
| earnings_per_share_basic_fy | Basic EPS (FY) alt | fundamental_price |
| earnings_per_share_basic_fh | Basic EPS (FH) | fundamental_price |
| earnings_per_share_basic_cagr_5y | Basic EPS 5Y CAGR | percent |
| earnings_per_share_diluted_ttm | Diluted EPS (TTM) | fundamental_price |
| last_annual_eps | Diluted EPS (FY) | fundamental_price |
| earnings_per_share_fq | Diluted EPS (MRQ) | fundamental_price |
| earnings_per_share_diluted_fq | Diluted EPS (MRQ) alt | fundamental_price |
| earnings_per_share_diluted_fy | Diluted EPS (FY) alt | fundamental_price |
| earnings_per_share_diluted_fh | Diluted EPS (FH) | fundamental_price |
| earnings_per_share_forecast_next_fq | EPS Forecast (next MRQ) | fundamental_price |
| earnings_per_share_forecast_fq | EPS Forecast (MRQ) | fundamental_price |
| earnings_per_share_forecast_next_fh | EPS Forecast (next FH) | fundamental_price |
| earnings_per_share_forecast_next_fy | EPS Forecast (next FY) | fundamental_price |
| earnings_release_date | Recent Earnings Date | time |
| earnings_release_next_date | Upcoming Earnings Date | time |
| earnings_release_calendar_date | Earnings Calendar Date | time |
| eps_surprise_fq | EPS Surprise (MRQ) | fundamental_price |
| eps_surprise_percent_fq | EPS Surprise % (MRQ) | percent |
| revenue_surprise_fq | Revenue Surprise (MRQ) | fundamental_price |
| revenue_surprise_percent_fq | Revenue Surprise % (MRQ) | percent |
| sell_gen_admin_exp_other_fy | SG&A Expenses (FY) | fundamental_price |
| sell_gen_admin_exp_other_ttm | SG&A Expenses (TTM) | fundamental_price |
| sell_gen_admin_exp_other_ratio_fy | SG&A Ratio (FY) | percent |
| sell_gen_admin_exp_other_ratio_ttm | SG&A Ratio (TTM) | percent |
| research_and_dev_fy | R&D Expenses (FY) | fundamental_price |
| research_and_dev_fq | R&D Expenses (MRQ) | fundamental_price |
| research_and_dev_fh | R&D Expenses (FH) | fundamental_price |
| research_and_dev_ttm | R&D Expenses (TTM) | fundamental_price |
| research_and_dev_ratio_fy | R&D Ratio (FY) | percent |
| research_and_dev_ratio_ttm | R&D Ratio (TTM) | percent |
| ebit_ttm | EBIT (TTM) | fundamental_price |

---

## Fundamental — Balance Sheet

| Column name | Display name | Type |
|-------------|--------------|------|
| total_assets | Total Assets (MRQ) | fundamental_price |
| total_assets_fq | Total Assets (MRQ) alt | fundamental_price |
| total_assets_fy | Total Assets (FY) | fundamental_price |
| total_current_assets | Total Current Assets (MRQ) | fundamental_price |
| total_current_assets_fq | Total Current Assets (MRQ) alt | fundamental_price |
| total_current_assets_fy | Total Current Assets (FY) | fundamental_price |
| cash_n_short_term_invest_fq | Cash & Short-term Investments (MRQ) | fundamental_price |
| cash_n_short_term_invest_fy | Cash & Short-term Investments (FY) | fundamental_price |
| cash_n_equivalents_fq | Cash & Equivalents (MRQ) | fundamental_price |
| cash_n_equivalents_fy | Cash & Equivalents (FY) | fundamental_price |
| total_debt | Total Debt (MRQ) | fundamental_price |
| total_debt_fq | Total Debt (MRQ) alt | fundamental_price |
| total_debt_fy | Total Debt (FY) | fundamental_price |
| short_term_debt_fq | Short-term Debt (MRQ) | fundamental_price |
| short_term_debt_fy | Short-term Debt (FY) | fundamental_price |
| long_term_debt_fq | Long-term Debt (MRQ) | fundamental_price |
| long_term_debt_fy | Long-term Debt (FY) | fundamental_price |
| total_liabilities_fq | Total Liabilities (MRQ) | fundamental_price |
| total_liabilities_fy | Total Liabilities (FY) | fundamental_price |
| total_current_liabilities_fq | Total Current Liabilities (MRQ) | fundamental_price |
| total_current_liabilities_fy | Total Current Liabilities (FY) | fundamental_price |
| shrhldrs_equity_fq | Shareholders' Equity (MRQ) | fundamental_price |
| shrhldrs_equity_fy | Shareholders' Equity (FY) | fundamental_price |
| total_equity_fq | Total Equity (MRQ) | fundamental_price |
| total_equity_fy | Total Equity (FY) | fundamental_price |
| net_debt | Net Debt (MRQ) | fundamental_price |
| net_debt_fq | Net Debt (MRQ) alt | fundamental_price |
| net_debt_fy | Net Debt (FY) | fundamental_price |
| goodwill | Goodwill | fundamental_price |
| goodwill_fq | Goodwill (MRQ) | fundamental_price |
| goodwill_fy | Goodwill (FY) | fundamental_price |
| current_ratio | Current Ratio (MRQ) | number |
| current_ratio_fq | Current Ratio (MRQ) alt | number |
| current_ratio_fy | Current Ratio (FY) | number |
| quick_ratio | Quick Ratio (MRQ) | number |
| quick_ratio_fq | Quick Ratio (MRQ) alt | number |
| quick_ratio_fy | Quick Ratio (FY) | number |
| cash_ratio | Cash Ratio | number |
| debt_to_equity | Debt to Equity (MRQ) | number |
| debt_to_equity_fq | Debt to Equity (MRQ) alt | number |
| debt_to_equity_fy | Debt to Equity (FY) | number |
| debt_to_asset_fq | Debt to Assets (MRQ) | number |
| debt_to_asset_fy | Debt to Assets (FY) | number |
| debt_to_assets | Debt to Assets | number |
| long_term_debt_to_equity_fq | LT Debt to Equity (MRQ) | number |
| long_term_debt_to_assets_fq | LT Debt to Assets (MRQ) | number |
| long_term_debt_to_assets_fy | LT Debt to Assets (FY) | number |
| enterprise_value_fq | Enterprise Value (MRQ) | fundamental_price |
| net_debt_to_ebitda_fq | Net Debt to EBITDA (MRQ) | number |
| net_debt_to_ebitda_fy | Net Debt to EBITDA (FY) | number |
| total_debt_to_ebitda_fq | Total Debt to EBITDA (MRQ) | number |
| total_debt_to_ebitda_fy | Total Debt to EBITDA (FY) | number |
| working_capital_fq | Working Capital (MRQ) | fundamental_price |
| total_shares_outstanding | Total Shares Outstanding | number |
| total_shares_outstanding_fundamental | Total Shares Outstanding (fundamental) | number |
| float_shares_outstanding | Shares Float | number |
| shares_outstanding | Shares Outstanding | number |
| book_value_per_share_fq | Book Value per Share (MRQ) | fundamental_price |
| book_value_per_share_fy | Book Value per Share (FY) | fundamental_price |
| altman_z_score_fy | Altman Z-Score (FY) | number |
| altman_z_score_ttm | Altman Z-Score (TTM) | number |
| piotroski_f_score_fy | Piotroski F-Score (FY) | number |

---

## Fundamental — Cash Flow

| Column name | Display name | Type |
|-------------|--------------|------|
| free_cash_flow | Free Cash Flow (FY) | fundamental_price |
| free_cash_flow_fq | Free Cash Flow (MRQ) | fundamental_price |
| free_cash_flow_fh | Free Cash Flow (FH) | fundamental_price |
| free_cash_flow_ttm | Free Cash Flow (TTM) | fundamental_price |
| free_cash_flow_margin_fy | FCF Margin (FY) | percent |
| free_cash_flow_margin_ttm | FCF Margin (TTM) | percent |
| free_cash_flow_yoy_growth_fy | FCF YoY Growth (FY) | percent |
| free_cash_flow_qoq_growth_fq | FCF QoQ Growth (MRQ) | percent |
| free_cash_flow_yoy_growth_fq | FCF YoY Growth (MRQ) | percent |
| free_cash_flow_yoy_growth_ttm | FCF YoY Growth (TTM) | percent |
| free_cash_flow_cagr_5y | FCF 5Y CAGR | percent |
| cash_f_operating_activities_fy | Cash from Operations (FY) | fundamental_price |
| cash_f_operating_activities_fq | Cash from Operations (MRQ) | fundamental_price |
| cash_f_operating_activities_fh | Cash from Operations (FH) | fundamental_price |
| cash_f_operating_activities_ttm | Cash from Operations (TTM) | fundamental_price |
| cash_f_investing_activities_fy | Cash from Investing (FY) | fundamental_price |
| cash_f_investing_activities_fq | Cash from Investing (MRQ) | fundamental_price |
| cash_f_investing_activities_fh | Cash from Investing (FH) | fundamental_price |
| cash_f_investing_activities_ttm | Cash from Investing (TTM) | fundamental_price |
| cash_f_financing_activities_fy | Cash from Financing (FY) | fundamental_price |
| cash_f_financing_activities_fq | Cash from Financing (MRQ) | fundamental_price |
| cash_f_financing_activities_fh | Cash from Financing (FH) | fundamental_price |
| cash_f_financing_activities_ttm | Cash from Financing (TTM) | fundamental_price |
| capital_expenditures_fy | CapEx (FY) | fundamental_price |
| capital_expenditures_fq | CapEx (MRQ) | fundamental_price |
| capital_expenditures_fh | CapEx (FH) | fundamental_price |
| capital_expenditures_ttm | CapEx (TTM) | fundamental_price |
| dividends_paid | Dividends Paid (FY) | fundamental_price |
| total_cash_dividends_paid_fy | Total Cash Dividends Paid (FY) | fundamental_price |
| total_cash_dividends_paid_fq | Total Cash Dividends Paid (MRQ) | fundamental_price |
| total_cash_dividends_paid_ttm | Total Cash Dividends Paid (TTM) | fundamental_price |

---

## Fundamental — Valuation Ratios

| Column name | Display name | Type |
|-------------|--------------|------|
| market_cap_basic | Market Capitalization | fundamental_price |
| price_earnings_ttm | P/E Ratio (TTM) | number |
| price_earnings_current | P/E Ratio (current) | number |
| price_earnings_forward_fy | Forward P/E (FY) | number |
| price_book_ratio | Price to Book (FY) | number |
| price_book_fq | Price to Book (MRQ) | number |
| price_book_current | Price to Book (current) | number |
| price_revenue_ttm | Price to Revenue (TTM) | number |
| price_sales_ratio | Price to Sales (FY) | number |
| price_sales_current | Price to Sales (current) | number |
| price_annual_sales | Price to Annual Sales | number |
| price_free_cash_flow_ttm | Price to FCF (TTM) | number |
| price_free_cash_flow_current | Price to FCF (current) | number |
| enterprise_value_ebitda_ttm | EV/EBITDA (TTM) | number |
| enterprise_value_ebitda_current | EV/EBITDA (current) | number |
| enterprise_value_to_revenue_ttm | EV/Revenue (TTM) | number |
| enterprise_value_to_free_cash_flow_ttm | EV/FCF (TTM) | number |
| enterprise_value_to_ebit_ttm | EV/EBIT (TTM) | number |
| enterprise_value_to_gross_profit_ttm | EV/Gross Profit (TTM) | number |
| return_on_equity | Return on Equity (TTM) | percent |
| return_on_equity_fq | ROE (MRQ) | percent |
| return_on_equity_fy | ROE (FY) | percent |
| return_on_common_equity_ttm | Return on Common Equity (TTM) | percent |
| return_on_assets | Return on Assets (TTM) | percent |
| return_on_assets_fq | ROA (MRQ) | percent |
| return_on_assets_fy | ROA (FY) | percent |
| return_on_invested_capital | Return on Invested Capital (TTM) | percent |
| return_on_invested_capital_fq | ROIC (MRQ) | percent |
| return_on_invested_capital_fy | ROIC (FY) | percent |
| price_earnings_growth_ttm | PEG Ratio (TTM) | number |
| price_annual_book | Price to Annual Book | number |
| price_to_cash_ratio | Price to Cash | number |
| graham_numbers_fy | Graham Number (FY) | number |
| graham_numbers_ttm | Graham Number (TTM) | number |
| piotroski_f_score_ttm | Piotroski F-Score (TTM) | number |
| earnings_yield | Earnings Yield | percent |

---

## Fundamental — Dividends

| Column name | Display name | Type |
|-------------|--------------|------|
| dividends_yield | Dividend Yield | number |
| dividend_yield_recent | Dividend Yield (Forward) | number |
| dividend_yield_upcoming | Dividend Yield (Upcoming) | number |
| dividends_yield_current | Dividend Yield (Current) | percent |
| dividends_yield_fq | Dividend Yield (MRQ) | percent |
| dividends_yield_fy | Dividend Yield (FY) | percent |
| dps_common_stock_prim_issue_fy | Dividends per Share (FY) | fundamental_price |
| dps_common_stock_prim_issue_fq | Dividends per Share (MRQ) | fundamental_price |
| dps_common_stock_prim_issue_ttm | Dividends per Share (TTM) | fundamental_price |
| dividends_per_share_fq | Dividends per Share (MRQ) alt | fundamental_price |
| dps_common_stock_prim_issue_yoy_growth_fy | DPS YoY Growth (FY) | percent |
| dividend_payout_ratio_fy | Dividend Payout Ratio (FY) | percent |
| dividend_payout_ratio_ttm | Dividend Payout Ratio (TTM) | percent |
| dividend_payout_ratio_percent_fq | Dividend Payout Ratio % (MRQ) | percent |
| dividend_payout_ratio_percent_fy | Dividend Payout Ratio % (FY) | percent |
| ex_dividend_date_recent | Ex-Dividend Date (recent) | time |
| ex_dividend_date_upcoming | Ex-Dividend Date (upcoming) | time |
| dividend_ex_date_recent | Ex-Dividend Date (recent) alt | time |
| dividend_ex_date_upcoming | Ex-Dividend Date (upcoming) alt | time |
| dividend_payment_date_recent | Dividend Payment Date (recent) | time |
| dividend_payment_date_upcoming | Dividend Payment Date (upcoming) | time |
| dividend_amount_recent | Dividend Amount (recent) | fundamental_price |
| dividend_amount_upcoming | Dividend Amount (upcoming) | fundamental_price |
| continuous_dividend_growth | Consecutive Years of Dividend Growth | number |
| continuous_dividend_payout | Consecutive Years of Dividend Payout | number |
| buyback_yield | Buyback Yield | fundamental_price |

---

## Fundamental — Company Info

| Column name | Display name | Type |
|-------------|--------------|------|
| number_of_employees | Number of Employees | number |
| number_of_employees_fy | Number of Employees (FY) | number |
| number_of_shareholders | Number of Shareholders | number |
| number_of_shareholders_fy | Number of Shareholders (FY) | number |
| total_shares_outstanding_fundamental | Total Shares Outstanding (fundamental) | number |
| float_shares_outstanding | Shares Float | number |
| float_shares_outstanding_current | Shares Float (current) | number |
| float_shares_percent_current | Float % (current) | percent |
| last_annual_revenue | Last Year Revenue (FY) | fundamental_price |
| revenue_per_employee_fy | Revenue per Employee (FY) | fundamental_price |
| net_income_per_employee_fy | Net Income per Employee (FY) | fundamental_price |
| ipo_offer_date | IPO Offer Date | time |
| ipo_announcement_date | IPO Announcement Date | time |
| ipo_deal_amount_usd | IPO Deal Amount (USD) | number |
| ipo_market_cap_usd | IPO Market Cap (USD) | number |
| has_ipo_data | Has IPO Data | bool |
| recommendation_buy | Analyst Buy Recommendations | number |
| recommendation_hold | Analyst Hold Recommendations | number |
| recommendation_sell | Analyst Sell Recommendations | number |
| recommendation_total | Total Analyst Recommendations | number |
| recommendation_mark | Analyst Recommendation Score | number |
| price_target_average | Average Analyst Price Target | number |
| price_target_high | High Analyst Price Target | number |
| price_target_low | Low Analyst Price Target | number |
| price_target_median | Median Analyst Price Target | number |
| price_target_1y | 1-Year Analyst Price Target | price |
| price_target_1y_delta | 1-Year Price Target Delta % | percent |

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
`|<timeframe>` to request a specific resolution. The default (no suffix) is
the **1-day** timeframe.

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

**Example usage:**

```python
.select('close', 'close|60', 'MACD.macd|1', 'RSI|15')
# close       = daily close
# close|60    = 1-hour close
# MACD.macd|1 = 1-minute MACD
# RSI|15      = 15-minute RSI
```

> **Note:** This catalogue covers the primary named fields from the upstream
> documentation page. The full page at
> `https://shner-elmo.github.io/TradingView-Screener/fields/stocks.html`
> includes 300+ additional variant fields (extended indicator periods,
> fund/ETF-specific metrics, bond fields). Consult that URL directly when a
> field is not listed here.
