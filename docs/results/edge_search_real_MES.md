# Edge search — real_MES

Data: real data: ../data/real/MES.parquet. Instrument MES (all-in cost $3.90/RT). **12,144 configurations** across 4 families, searched in 26 s. In-sample = first 70 % of days, out-of-sample = last 30 %.

## Verdict on the search itself

| metric | value | meaning |
|---|---|---|
| best in-sample Sharpe | 1.33 | what a naive optimiser would show you |
| same config, out-of-sample Sharpe | -0.70 | what it actually did next |
| deflated Sharpe (P that the winner is real, 12,144 trials) | 0.00 | ≥ 0.95 required |
| deflated Sharpe with effective trials (≈ 36 independent bets) | 0.00 | configs are highly correlated; this is the fairer test |
| PBO (CSCV, 2000 splits) | 0.10 | ≥ 0.5 = the 'best' config is noise |
| walk-forward OOS Sharpe of the re-selection process | -0.18 | the honest number |
| walk-forward OOS mean daily R | -0.006 | |

## By family

| family | configs | median IS Sharpe | best IS Sharpe | its OOS Sharpe | share OOS > 0 | configs with win rate ≥ 60 % | their median OOS E[R] |
|---|---|---|---|---|---|---|---|
| LDM | 144 | -0.58 | 0.75 | 0.55 | 38% | 0 | +nan |
| NAM | 8,000 | -0.44 | 1.33 | -0.70 | 8% | 1,038 | -0.101 |
| ORB | 2,000 | -1.80 | 0.64 | 0.46 | 5% | 211 | -0.111 |
| VWR | 2,000 | -3.40 | -0.91 | -2.35 | 1% | 108 | -0.126 |

## In-sample leaderboard (top 15) — and what happened out of sample

| # | family | key params | trades/day | win % | IS Sharpe | OOS Sharpe | IS E[R] | OOS E[R] |
|---|---|---|---|---|---|---|---|---|
| 1 | NAM | {'band_mult': 1.2, 'trail_mode': 3, 'target_r': 2.0, 'regime_filter': 1, 'direction': 1} | 0.15 | 46% | 1.33 | -0.70 | +0.296 | -0.137 |
| 2 | NAM | {'band_mult': 1.5, 'trail_mode': 0, 'target_r': 2.0, 'regime_filter': 0, 'direction': 1} | 0.19 | 44% | 1.18 | -0.89 | +0.159 | -0.137 |
| 3 | NAM | {'band_mult': 1.5, 'trail_mode': 3, 'target_r': 2.0, 'regime_filter': 1, 'direction': 1} | 0.11 | 48% | 1.14 | -0.40 | +0.276 | -0.085 |
| 4 | NAM | {'band_mult': 1.2, 'trail_mode': 0, 'target_r': 2.0, 'regime_filter': 0, 'direction': 1} | 0.39 | 44% | 1.13 | -1.29 | +0.111 | -0.117 |
| 5 | NAM | {'band_mult': 1.0, 'trail_mode': 3, 'target_r': 1.0, 'regime_filter': 0, 'direction': 1} | 0.26 | 57% | 1.11 | -0.99 | +0.119 | -0.111 |
| 6 | NAM | {'band_mult': 1.5, 'trail_mode': 1, 'target_r': 1.0, 'regime_filter': 0, 'direction': 1} | 0.18 | 52% | 1.03 | -1.44 | +0.117 | -0.164 |
| 7 | NAM | {'band_mult': 1.0, 'trail_mode': 0, 'target_r': 3.0, 'regime_filter': 0, 'direction': 1} | 0.26 | 41% | 1.00 | -0.75 | +0.148 | -0.104 |
| 8 | NAM | {'band_mult': 1.2, 'trail_mode': 0, 'target_r': 2.0, 'regime_filter': 1, 'direction': 1} | 0.33 | 37% | 0.96 | -1.06 | +0.076 | -0.086 |
| 9 | NAM | {'band_mult': 1.2, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': 0, 'direction': 1} | 0.25 | 42% | 0.96 | 0.09 | +0.221 | +0.022 |
| 10 | NAM | {'band_mult': 1.0, 'trail_mode': 1, 'target_r': 2.0, 'regime_filter': 1, 'direction': 1} | 0.18 | 41% | 0.92 | -1.31 | +0.162 | -0.184 |
| 11 | NAM | {'band_mult': 1.2, 'trail_mode': 0, 'target_r': 0.0, 'regime_filter': 0, 'direction': 1} | 0.28 | 34% | 0.92 | 0.00 | +0.270 | +0.001 |
| 12 | NAM | {'band_mult': 1.5, 'trail_mode': 2, 'target_r': 0.0, 'regime_filter': 0, 'direction': 1} | 0.27 | 34% | 0.92 | -0.67 | +0.266 | -0.155 |
| 13 | NAM | {'band_mult': 0.8, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': 0, 'direction': 1} | 0.35 | 39% | 0.91 | -0.38 | +0.183 | -0.073 |
| 14 | NAM | {'band_mult': 1.2, 'trail_mode': 1, 'target_r': 2.0, 'regime_filter': 0, 'direction': 1} | 0.30 | 42% | 0.90 | -0.45 | +0.124 | -0.054 |
| 15 | NAM | {'band_mult': 1.2, 'trail_mode': 3, 'target_r': 3.0, 'regime_filter': 1, 'direction': 1} | 0.15 | 40% | 0.89 | -0.41 | +0.227 | -0.097 |

## Topstep objective: walk-forward OOS trades through the 50K lifecycle simulator (1 year)

Empirical model: 387 OOS trades, 0.28 trades/day, net E[R] -0.022.

| risk $/trade | net mean $ | net median $ | P(net>0) | pass rate/attempt |
|---|---|---|---|---|
| 200 | -600 | -588 | 0% | 7% |
| 400 | -554 | -637 | 5% | 20% |
| 600 | -411 | -686 | 15% | 21% |
