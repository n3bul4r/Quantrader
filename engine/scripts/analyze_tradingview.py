"""Compare a TradingView forward test with the real-data backtest expectations.

    python scripts/analyze_tradingview.py <List-of-trades export .csv> [--risk 500] [--strategy momentum|vwap]

Export in TradingView: Strategy Tester → List of trades → Export (CSV). Works with old and new column layouts.
Expectations come from the real-data test (docs/REAL_DATA_RESULTS.md):
  momentum (S1, nasdaq_noise_momentum.pine): ≈ 0.84 trades/session, ≈ 33 % winners, ≈ +0.10 R net per trade.
  vwap (S3, nasdaq_vwap_reversion.pine, control): ≈ 0.62 trades/session, ≈ 43 % winners, ≈ −0.04 R net per trade
  (out-of-sample of its best in-sample variant; the search as a whole was −0.08 R).
"""
from __future__ import annotations

import argparse
import math
import sys

import pandas as pd

EXPECTS = {
    "momentum": {"trades_per_day": 0.84, "win_rate": 0.33, "exp_r": 0.10, "sd_r": 1.9},
    "vwap": {"trades_per_day": 0.62, "win_rate": 0.43, "exp_r": -0.04, "sd_r": 1.13},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--risk", type=float, default=500.0, help="risk per trade in $ (the script input)")
    ap.add_argument("--strategy", choices=sorted(EXPECTS), default="momentum")
    a = ap.parse_args()
    EXPECT = EXPECTS[a.strategy]
    df = pd.read_csv(a.csv)
    cols = {c.lower(): c for c in df.columns}
    type_col = next((cols[c] for c in cols if c == "type"), None)
    pnl_col = next((cols[c] for c in cols if ("p&l" in c or "profit" in c) and "cum" not in c and "%" not in c
                    and "run-up" not in c and "drawdown" not in c), None)
    dt_col = next((cols[c] for c in cols if "date" in c), None)
    if not (type_col and pnl_col and dt_col):
        sys.exit(f"unrecognised columns: {list(df.columns)}")
    ex = df[df[type_col].astype(str).str.contains("Exit", case=False)].copy()
    ex["pnl"] = pd.to_numeric(ex[pnl_col].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
    ex["dt"] = pd.to_datetime(ex[dt_col], errors="coerce")
    ex = ex.dropna(subset=["pnl", "dt"])
    n = len(ex)
    if n == 0:
        sys.exit("no closed trades yet")
    days = ex["dt"].dt.normalize().nunique()
    sessions = max(int(pd.bdate_range(ex["dt"].min(), ex["dt"].max()).size), 1)
    r = ex["pnl"] / a.risk
    exp_r, wr = r.mean(), (r > 0).mean()
    z = (exp_r - EXPECT["exp_r"]) / (EXPECT["sd_r"] / math.sqrt(n))
    print(f"period            {ex['dt'].min().date()} → {ex['dt'].max().date()}  ({sessions} sessions, {days} with trades)")
    print(f"trades            {n}  ({n / sessions:.2f}/session; expected ≈ {EXPECT['trades_per_day']})")
    print(f"net P&L           ${ex['pnl'].sum():,.0f}   best ${ex['pnl'].max():,.0f}   worst ${ex['pnl'].min():,.0f}")
    print(f"win rate          {wr:.0%}  (expected ≈ {EXPECT['win_rate']:.0%})")
    print(f"expectancy        {exp_r:+.3f} R per trade  (expected ≈ {EXPECT['exp_r']:+.2f} R)")
    cum = ex.sort_values("dt")["pnl"].cumsum()
    dd = (cum - cum.cummax().clip(lower=0)).min()
    print(f"max drawdown      ${dd:,.0f}  ({dd / a.risk:.1f} R)")
    z0 = exp_r / (EXPECT["sd_r"] / math.sqrt(n))
    print(f"strategy          {a.strategy}")
    print(f"drift z-score     {z:+.2f}   (below −2 = live edge significantly worse than tested → stop)")
    print(f"z vs zero         {z0:+.2f}   (above +2 = profitable beyond luck; this needs far more trades than 3 months)")
    if n < 60:
        print(f"note: only {n} trades — too few to judge; ~60+ trades (≈ 3 months) needed")


if __name__ == "__main__":
    main()
