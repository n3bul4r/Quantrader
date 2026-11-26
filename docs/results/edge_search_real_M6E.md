# Edge search — real_M6E

Data: real data: ../data/real/M6E.parquet. Instrument M6E (all-in cost $3.70/RT). **12,144 configurations** across 4 families, searched in 27 s. In-sample = first 70 % of days, out-of-sample = last 30 %.

## Verdict on the search itself

| metric | value | meaning |
|---|---|---|
| best in-sample Sharpe | 0.49 | what a naive optimiser would show you |
| same config, out-of-sample Sharpe | -1.54 | what it actually did next |
| deflated Sharpe (P that the winner is real, 11,859 trials) | 0.00 | ≥ 0.95 required |
| deflated Sharpe with effective trials (≈ 46 independent bets) | 0.00 | configs are highly correlated; this is the fairer test |
| PBO (CSCV, 2000 splits) | 0.00 | ≥ 0.5 = the 'best' config is noise |
| walk-forward OOS Sharpe of the re-selection process | -1.34 | the honest number |
| walk-forward OOS mean daily R | -0.022 | |

## By family

| family | configs | median IS Sharpe | best IS Sharpe | its OOS Sharpe | share OOS > 0 | configs with win rate ≥ 60 % | their median OOS E[R] |
|---|---|---|---|---|---|---|---|
| LDM | 144 | -2.72 | -0.39 | -1.33 | 0% | 0 | +nan |
| NAM | 7,998 | -2.47 | 0.19 | -0.66 | 0% | 4 | -0.227 |
| ORB | 1,843 | -2.80 | 0.49 | -1.54 | 1% | 26 | -0.237 |
| VWR | 1,874 | -3.63 | 0.19 | 0.14 | 1% | 5 | +0.277 |

## In-sample leaderboard (top 15) — and what happened out of sample

| # | family | key params | trades/day | win % | IS Sharpe | OOS Sharpe | IS E[R] | OOS E[R] |
|---|---|---|---|---|---|---|---|---|
| 1 | VWR | {'band_k': 1.5, 'stop_k': 0.5, 'time_stop': 60, 'regime_filter': 0} | 0.02 | 52% | 0.61 | 0.71 | +0.425 | +0.570 |
| 2 | ORB | {'or_len': 15, 'stop_frac': 0.25, 'target_r': 0.0, 'regime_filter': 1, 'direction': 1} | 0.05 | 25% | 0.49 | -1.54 | +0.743 | -0.906 |
| 3 | ORB | {'or_len': 15, 'stop_frac': 0.25, 'target_r': 4.0, 'regime_filter': 1, 'direction': 1} | 0.04 | 34% | 0.48 | -0.58 | +0.395 | -0.393 |
| 4 | VWR | {'band_k': 1.5, 'stop_k': 0.5, 'time_stop': 120, 'regime_filter': -1} | 0.01 | 52% | 0.48 | -0.33 | +0.588 | -0.371 |
| 5 | ORB | {'or_len': 15, 'stop_frac': 0.25, 'target_r': 0.0, 'regime_filter': 1, 'direction': 1} | 0.04 | 21% | 0.45 | -1.00 | +0.745 | -0.798 |
| 6 | ORB | {'or_len': 15, 'stop_frac': 0.25, 'target_r': 4.0, 'regime_filter': 1, 'direction': 1} | 0.04 | 35% | 0.45 | -0.36 | +0.331 | -0.233 |
| 7 | ORB | {'or_len': 15, 'stop_frac': 0.25, 'target_r': 4.0, 'regime_filter': 1, 'direction': 1} | 0.05 | 36% | 0.45 | -0.45 | +0.295 | -0.281 |
| 8 | ORB | {'or_len': 15, 'stop_frac': 0.25, 'target_r': 4.0, 'regime_filter': 1, 'direction': 1} | 0.05 | 34% | 0.44 | -0.44 | +0.314 | -0.276 |
| 9 | VWR | {'band_k': 1.5, 'stop_k': 0.5, 'time_stop': 30, 'regime_filter': 1} | 0.01 | 55% | 0.39 | 0.90 | +0.474 | +0.954 |
| 10 | VWR | {'band_k': 1.5, 'stop_k': 0.5, 'time_stop': 60, 'regime_filter': 1} | 0.01 | 55% | 0.39 | 0.97 | +0.474 | +1.041 |
| 11 | VWR | {'band_k': 1.5, 'stop_k': 0.5, 'time_stop': 30, 'regime_filter': 1} | 0.01 | 55% | 0.39 | 0.90 | +0.474 | +0.954 |
| 12 | VWR | {'band_k': 2.5, 'stop_k': 0.5, 'time_stop': 120, 'regime_filter': -1} | 0.02 | 31% | 0.39 | -1.41 | +0.325 | -1.543 |
| 13 | VWR | {'band_k': 1.5, 'stop_k': 0.5, 'time_stop': 30, 'regime_filter': -1} | 0.01 | 48% | 0.35 | -0.52 | +0.414 | -0.543 |
| 14 | VWR | {'band_k': 2.5, 'stop_k': 0.5, 'time_stop': 120, 'regime_filter': -1} | 0.01 | 31% | 0.33 | -1.26 | +0.480 | -1.588 |
| 15 | ORB | {'or_len': 15, 'stop_frac': 0.25, 'target_r': 0.0, 'regime_filter': 1, 'direction': 0} | 0.06 | 17% | 0.30 | -1.46 | +0.363 | -0.873 |

## Topstep objective: walk-forward OOS trades through the 50K lifecycle simulator (1 year)

Empirical model: 75 OOS trades, 0.05 trades/day, net E[R] -0.456.

| risk $/trade | net mean $ | net median $ | P(net>0) | pass rate/attempt |
|---|---|---|---|---|
| 200 | -589 | -588 | 0% | 0% |
| 400 | -612 | -588 | 0% | 0% |
| 600 | -627 | -637 | 0% | 0% |
