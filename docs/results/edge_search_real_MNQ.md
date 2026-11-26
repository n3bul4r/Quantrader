# Edge search — real_MNQ

Data: real data: ../data/real/MNQ.parquet. Instrument MNQ (all-in cost $2.40/RT). **12,144 configurations** across 4 families, searched in 27 s. In-sample = first 70 % of days, out-of-sample = last 30 %.

## Verdict on the search itself

| metric | value | meaning |
|---|---|---|
| best in-sample Sharpe | 1.61 | what a naive optimiser would show you |
| same config, out-of-sample Sharpe | 0.79 | what it actually did next |
| deflated Sharpe (P that the winner is real, 12,144 trials) | 0.00 | ≥ 0.95 required |
| deflated Sharpe with effective trials (≈ 33 independent bets) | 0.00 | configs are highly correlated; this is the fairer test |
| PBO (CSCV, 2000 splits) | 0.04 | ≥ 0.5 = the 'best' config is noise |
| walk-forward OOS Sharpe of the re-selection process | 0.31 | the honest number |
| walk-forward OOS mean daily R | +0.019 | |

## By family

| family | configs | median IS Sharpe | best IS Sharpe | its OOS Sharpe | share OOS > 0 | configs with win rate ≥ 60 % | their median OOS E[R] |
|---|---|---|---|---|---|---|---|
| LDM | 144 | 0.23 | 0.89 | 0.53 | 50% | 0 | +nan |
| NAM | 8,000 | 0.12 | 1.47 | 1.60 | 55% | 1,208 | -0.025 |
| ORB | 2,000 | -0.85 | 1.61 | 0.79 | 37% | 273 | -0.047 |
| VWR | 2,000 | -2.06 | -0.08 | 0.25 | 18% | 179 | -0.044 |

## In-sample leaderboard (top 15) — and what happened out of sample

| # | family | key params | trades/day | win % | IS Sharpe | OOS Sharpe | IS E[R] | OOS E[R] |
|---|---|---|---|---|---|---|---|---|
| 1 | ORB | {'or_len': 60, 'stop_frac': 0.5, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.29 | 25% | 1.61 | 0.79 | +0.302 | +0.122 |
| 2 | ORB | {'or_len': 60, 'stop_frac': 1.0, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.49 | 42% | 1.57 | 1.15 | +0.253 | +0.176 |
| 3 | NAM | {'band_mult': 1.5, 'trail_mode': 2, 'target_r': 3.0, 'regime_filter': 0, 'direction': 0} | 0.58 | 41% | 1.47 | 1.60 | +0.136 | +0.135 |
| 4 | ORB | {'or_len': 60, 'stop_frac': 0.5, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 0.98 | 29% | 1.46 | 1.18 | +0.294 | +0.211 |
| 5 | ORB | {'or_len': 60, 'stop_frac': 1.0, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.00 | 40% | 1.46 | 0.89 | +0.178 | +0.092 |
| 6 | NAM | {'band_mult': 1.5, 'trail_mode': 3, 'target_r': 2.0, 'regime_filter': 0, 'direction': 0} | 0.68 | 45% | 1.45 | 0.56 | +0.132 | +0.050 |
| 7 | ORB | {'or_len': 60, 'stop_frac': 1.0, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 0.90 | 41% | 1.44 | 0.54 | +0.158 | +0.054 |
| 8 | ORB | {'or_len': 60, 'stop_frac': 1.0, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 0.98 | 40% | 1.42 | 0.92 | +0.176 | +0.097 |
| 9 | ORB | {'or_len': 60, 'stop_frac': 0.5, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.76 | 26% | 1.41 | 1.27 | +0.335 | +0.281 |
| 10 | ORB | {'or_len': 60, 'stop_frac': 1.0, 'target_r': 4.0, 'regime_filter': -1, 'direction': 0} | 0.50 | 41% | 1.40 | 1.35 | +0.201 | +0.207 |
| 11 | NAM | {'band_mult': 1.5, 'trail_mode': 2, 'target_r': 2.0, 'regime_filter': 0, 'direction': 1} | 0.19 | 49% | 1.37 | 0.62 | +0.215 | +0.098 |
| 12 | NAM | {'band_mult': 0.8, 'trail_mode': 1, 'target_r': 2.0, 'regime_filter': 0, 'direction': 1} | 0.71 | 41% | 1.37 | -0.21 | +0.118 | -0.017 |
| 13 | ORB | {'or_len': 60, 'stop_frac': 1.0, 'target_r': 4.0, 'regime_filter': -1, 'direction': 0} | 0.49 | 41% | 1.37 | 1.39 | +0.200 | +0.218 |
| 14 | NAM | {'band_mult': 0.8, 'trail_mode': 2, 'target_r': 1.0, 'regime_filter': 1, 'direction': 0} | 0.57 | 52% | 1.37 | 1.14 | +0.092 | +0.073 |
| 15 | ORB | {'or_len': 60, 'stop_frac': 0.5, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.49 | 32% | 1.36 | 1.39 | +0.340 | +0.370 |

## Topstep objective: walk-forward OOS trades through the 50K lifecycle simulator (1 year)

Empirical model: 896 OOS trades, 0.59 trades/day, net E[R] +0.032.

| risk $/trade | net mean $ | net median $ | P(net>0) | pass rate/attempt |
|---|---|---|---|---|
| 200 | -525 | -637 | 5% | 32% |
| 400 | 22 | -627 | 29% | 29% |
| 600 | 409 | -621 | 39% | 24% |
