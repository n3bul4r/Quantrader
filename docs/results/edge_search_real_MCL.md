# Edge search — real_MCL

Data: real data: ../data/real/MCL.parquet. Instrument MCL (all-in cost $4.70/RT). **12,144 configurations** across 4 families, searched in 18 s. In-sample = first 70 % of days, out-of-sample = last 30 %.

## Verdict on the search itself

| metric | value | meaning |
|---|---|---|
| best in-sample Sharpe | 0.44 | what a naive optimiser would show you |
| same config, out-of-sample Sharpe | 0.55 | what it actually did next |
| deflated Sharpe (P that the winner is real, 12,144 trials) | 0.00 | ≥ 0.95 required |
| deflated Sharpe with effective trials (≈ 44 independent bets) | 0.00 | configs are highly correlated; this is the fairer test |
| PBO (CSCV, 2000 splits) | 0.07 | ≥ 0.5 = the 'best' config is noise |
| walk-forward OOS Sharpe of the re-selection process | -1.21 | the honest number |
| walk-forward OOS mean daily R | -0.048 | |

## By family

| family | configs | median IS Sharpe | best IS Sharpe | its OOS Sharpe | share OOS > 0 | configs with win rate ≥ 60 % | their median OOS E[R] |
|---|---|---|---|---|---|---|---|
| LDM | 144 | -1.87 | -0.34 | -0.90 | 7% | 0 | +nan |
| NAM | 8,000 | -2.02 | 0.44 | 0.55 | 7% | 162 | -0.099 |
| ORB | 2,000 | -3.18 | -0.10 | -0.64 | 11% | 130 | -0.109 |
| VWR | 2,000 | -4.93 | -1.08 | -1.73 | 3% | 65 | -0.080 |

## In-sample leaderboard (top 15) — and what happened out of sample

| # | family | key params | trades/day | win % | IS Sharpe | OOS Sharpe | IS E[R] | OOS E[R] |
|---|---|---|---|---|---|---|---|---|
| 1 | NAM | {'band_mult': 1.0, 'trail_mode': 2, 'target_r': 0.0, 'regime_filter': 1, 'direction': 0} | 0.30 | 28% | 0.44 | 0.55 | +0.109 | +0.150 |
| 2 | NAM | {'band_mult': 1.5, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.23 | 34% | 0.39 | 0.63 | +0.144 | +0.174 |
| 3 | NAM | {'band_mult': 1.2, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.20 | 21% | 0.37 | 0.42 | +0.279 | +0.228 |
| 4 | NAM | {'band_mult': 1.2, 'trail_mode': 2, 'target_r': 0.0, 'regime_filter': 1, 'direction': 0} | 0.45 | 31% | 0.34 | -0.66 | +0.044 | -0.047 |
| 5 | NAM | {'band_mult': 1.5, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 0.50 | 25% | 0.33 | 0.04 | +0.075 | +0.010 |
| 6 | NAM | {'band_mult': 0.8, 'trail_mode': 2, 'target_r': 0.0, 'regime_filter': 1, 'direction': 0} | 0.33 | 26% | 0.33 | -0.56 | +0.061 | -0.078 |
| 7 | NAM | {'band_mult': 1.5, 'trail_mode': 1, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.19 | 42% | 0.32 | 0.57 | +0.079 | +0.099 |
| 8 | NAM | {'band_mult': 0.8, 'trail_mode': 2, 'target_r': 0.0, 'regime_filter': 1, 'direction': 0} | 0.32 | 27% | 0.31 | 0.27 | +0.137 | +0.094 |
| 9 | NAM | {'band_mult': 1.5, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': 1, 'direction': 0} | 0.20 | 22% | 0.31 | -0.72 | +0.148 | -0.236 |
| 10 | NAM | {'band_mult': 1.5, 'trail_mode': 1, 'target_r': 0.0, 'regime_filter': 1, 'direction': 0} | 0.19 | 31% | 0.30 | -0.91 | +0.239 | -0.240 |
| 11 | NAM | {'band_mult': 1.5, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.26 | 24% | 0.27 | 0.70 | +0.159 | +0.340 |
| 12 | NAM | {'band_mult': 1.5, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.16 | 38% | 0.27 | 0.43 | +0.114 | +0.136 |
| 13 | NAM | {'band_mult': 1.5, 'trail_mode': 2, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 0.43 | 37% | 0.25 | -0.56 | +0.016 | -0.085 |
| 14 | NAM | {'band_mult': 0.6, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': 1, 'direction': 0} | 0.38 | 21% | 0.25 | -0.31 | +0.105 | -0.092 |
| 15 | NAM | {'band_mult': 1.5, 'trail_mode': 2, 'target_r': 3.0, 'regime_filter': 1, 'direction': 0} | 0.19 | 38% | 0.25 | 0.01 | +0.049 | +0.003 |

## Topstep objective: walk-forward OOS trades through the 50K lifecycle simulator (1 year)

Empirical model: 129 OOS trades, 0.17 trades/day, net E[R] -0.284.

| risk $/trade | net mean $ | net median $ | P(net>0) | pass rate/attempt |
|---|---|---|---|---|
| 200 | -624 | -637 | 0% | 1% |
| 400 | -667 | -686 | 0% | 1% |
| 600 | -706 | -735 | 0% | 2% |
