# Edge search — noise

Data: SYNTHETIC 1500 days, injected momentum κ=0.0. Instrument MES (all-in cost $3.90/RT). **12,144 configurations** across 4 families, searched in 28 s. In-sample = first 70 % of days, out-of-sample = last 30 %.

## Verdict on the search itself

| metric | value | meaning |
|---|---|---|
| best in-sample Sharpe | 1.49 | what a naive optimiser would show you |
| same config, out-of-sample Sharpe | 0.64 | what it actually did next |
| deflated Sharpe (P that the winner is real, 12,144 trials) | 0.00 | ≥ 0.95 required |
| deflated Sharpe with effective trials (≈ 29 independent bets) | 0.30 | configs are highly correlated; this is the fairer test |
| PBO (CSCV, 2000 splits) | 0.27 | ≥ 0.5 = the 'best' config is noise |
| walk-forward OOS Sharpe of the re-selection process | 0.11 | the honest number |
| walk-forward OOS mean daily R | +0.007 | |

## By family

| family | configs | median IS Sharpe | best IS Sharpe | its OOS Sharpe | share OOS > 0 | configs with win rate ≥ 60 % | their median OOS E[R] |
|---|---|---|---|---|---|---|---|
| LDM | 144 | -0.07 | 0.50 | 0.87 | 35% | 0 | +nan |
| NAM | 8,000 | -0.12 | 1.49 | 0.64 | 55% | 1,108 | -0.047 |
| ORB | 2,000 | -0.58 | 1.29 | 0.61 | 47% | 316 | -0.049 |
| VWR | 2,000 | -0.81 | 0.91 | -0.14 | 12% | 192 | -0.050 |

## In-sample leaderboard (top 15) — and what happened out of sample

| # | family | key params | trades/day | win % | IS Sharpe | OOS Sharpe | IS E[R] | OOS E[R] |
|---|---|---|---|---|---|---|---|---|
| 1 | NAM | {'band_mult': 1.5, 'trail_mode': 2, 'target_r': 2.0, 'regime_filter': 0, 'direction': 0} | 0.37 | 42% | 1.49 | 0.64 | +0.208 | +0.091 |
| 2 | NAM | {'band_mult': 1.5, 'trail_mode': 3, 'target_r': 1.0, 'regime_filter': 0, 'direction': 0} | 0.79 | 55% | 1.42 | 0.50 | +0.093 | +0.033 |
| 3 | NAM | {'band_mult': 1.5, 'trail_mode': 0, 'target_r': 2.0, 'regime_filter': 0, 'direction': 0} | 0.37 | 42% | 1.42 | 0.69 | +0.202 | +0.098 |
| 4 | NAM | {'band_mult': 0.8, 'trail_mode': 1, 'target_r': 3.0, 'regime_filter': 1, 'direction': 0} | 0.55 | 41% | 1.32 | 0.59 | +0.159 | +0.058 |
| 5 | NAM | {'band_mult': 1.5, 'trail_mode': 3, 'target_r': 1.0, 'regime_filter': -1, 'direction': 1} | 0.20 | 58% | 1.30 | 0.61 | +0.152 | +0.102 |
| 6 | ORB | {'or_len': 60, 'stop_frac': 0.5, 'target_r': 4.0, 'regime_filter': 1, 'direction': 0} | 0.33 | 40% | 1.29 | 0.61 | +0.252 | +0.098 |
| 7 | NAM | {'band_mult': 1.0, 'trail_mode': 2, 'target_r': 3.0, 'regime_filter': -1, 'direction': 1} | 0.35 | 33% | 1.27 | -0.99 | +0.211 | -0.155 |
| 8 | NAM | {'band_mult': 1.0, 'trail_mode': 2, 'target_r': 3.0, 'regime_filter': -1, 'direction': 1} | 0.28 | 33% | 1.27 | -0.43 | +0.230 | -0.078 |
| 9 | ORB | {'or_len': 60, 'stop_frac': 0.25, 'target_r': 4.0, 'regime_filter': 1, 'direction': 0} | 0.39 | 29% | 1.26 | 1.01 | +0.273 | +0.202 |
| 10 | NAM | {'band_mult': 1.0, 'trail_mode': 0, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.03 | 32% | 1.25 | -0.04 | +0.172 | -0.004 |
| 11 | NAM | {'band_mult': 1.2, 'trail_mode': 2, 'target_r': 2.0, 'regime_filter': 1, 'direction': 0} | 0.40 | 41% | 1.25 | 0.18 | +0.150 | +0.018 |
| 12 | NAM | {'band_mult': 1.0, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.21 | 22% | 1.25 | 1.03 | +0.201 | +0.195 |
| 13 | NAM | {'band_mult': 1.5, 'trail_mode': 2, 'target_r': 2.0, 'regime_filter': 1, 'direction': 0} | 0.31 | 43% | 1.23 | -0.05 | +0.171 | -0.006 |
| 14 | NAM | {'band_mult': 0.8, 'trail_mode': 3, 'target_r': 3.0, 'regime_filter': 0, 'direction': 0} | 1.38 | 33% | 1.21 | 1.23 | +0.099 | +0.111 |
| 15 | NAM | {'band_mult': 0.8, 'trail_mode': 1, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.21 | 33% | 1.19 | 0.88 | +0.168 | +0.105 |

## Topstep objective: walk-forward OOS trades through the 50K lifecycle simulator (1 year)

Empirical model: 413 OOS trades, 0.47 trades/day, net E[R] +0.015.

| risk $/trade | net mean $ | net median $ | P(net>0) | pass rate/attempt |
|---|---|---|---|---|
| 200 | -557 | -637 | 3% | 24% |
| 400 | -22 | -686 | 27% | 27% |
| 600 | 287 | -784 | 36% | 22% |
