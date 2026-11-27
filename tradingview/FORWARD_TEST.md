# 3-month TradingView paper test: Nasdaq noise-area momentum

**Runs:** Monday 30 Nov 2026 → Friday 26 Feb 2027 (about 63 sessions, about 50–60 trades expected).
**Script:** [nasdaq_noise_momentum.pine](nasdaq_noise_momentum.pine), the strategy that passed the real-data test.

## Start it (5 minutes)
1. In TradingView, open a chart of **MNQ1!** (Micro Nasdaq, continuous) on the **5-minute** timeframe.
   * CME data is delayed 10 minutes on free plans. That's fine for this test, since decisions are every 30 minutes.
2. **Pine Editor** → *Open → New blank strategy* → delete everything → paste the whole `.pine` file →
   **Save** → **Add to chart**.
3. Strategy settings (gear icon) → *Inputs*:
   * forward-test start date `2026-11-30`;
   * risk per trade **$500**;
   * daily loss stop **$1,000**;
   * leave the rest as is.
4. Optional: right-click the strategy → *Add alert on strategy* → "Order fills", to get notified of every trade.
5. Keep the chart (and the strategy on it) saved in your layout. TradingView recalculates it on every new bar, so
   it keeps paper-trading the whole period. You don't need to keep the browser open.
   * If you also want the trades in TradingView's *Paper Trading* account, place each alerted order there by hand.
     It is optional; the Strategy Tester already records everything.

**Before the start date:** set the start date to e.g. 2026-06-01 to see recent behaviour (a backtest only), then set
it back to 2026-11-30.

## Every month (end of Dec, Jan, Feb)
1. Strategy Tester → **List of trades** → **Export** (CSV).
2. Upload the CSV in the Claude session (or run `python engine/scripts/analyze_tradingview.py <file>`).
3. Compare against the real-data expectations:

| | expected | stop the test if |
|---|---|---|
| trades per session | ≈ 0.84 | far fewer: the script isn't running correctly |
| win rate | ≈ 33 % | — (a low win rate is normal for this strategy) |
| expectancy | ≈ +0.10R per trade ($50 at $500 risk) | drift z-score < −2 after 40+ trades |
| worst drawdown | 30R+ has happened in the backtest | — |

## What 3 months can and cannot tell you
* **Can:** that the script runs, fills and costs match the backtest, and that nothing is broken.
* **Cannot:** prove the edge. Its annual Sharpe of ~0.6 means 3 months of paper results are mostly noise. A losing
  quarter is entirely possible even if the edge is real; 2019 and 2025 were negative years in the backtest.
* **Decision rule after 3 months:**
  * If the drift z-score is above −1 and execution matches → keep going, optionally with one Topstep 50K at 10–15 %
    risk ($200–300).
  * If it is below −2 → stop.
