# Edge search — edge

Data: SYNTHETIC 1500 days, injected momentum κ=0.01. Instrument MES (all-in cost $3.90/RT). **12,144 configurations** across 4 families, searched in 28 s. In-sample = first 70 % of days, out-of-sample = last 30 %.

## Verdict on the search itself

| metric | value | meaning |
|---|---|---|
| best in-sample Sharpe | 2.28 | what a naive optimiser would show you |
| same config, out-of-sample Sharpe | 1.88 | what it actually did next |
| deflated Sharpe (P that the winner is real, 12,144 trials) | 0.00 | ≥ 0.95 required |
| deflated Sharpe with effective trials (≈ 26 independent bets) | 0.73 | configs are highly correlated; this is the fairer test |
| PBO (CSCV, 2000 splits) | 0.07 | ≥ 0.5 = the 'best' config is noise |
| walk-forward OOS Sharpe of the re-selection process | 1.00 | the honest number |
| walk-forward OOS mean daily R | +0.108 | |

## By family

| family | configs | median IS Sharpe | best IS Sharpe | its OOS Sharpe | share OOS > 0 | configs with win rate ≥ 60 % | their median OOS E[R] |
|---|---|---|---|---|---|---|---|
| LDM | 144 | 0.24 | 0.99 | 1.43 | 50% | 0 | +nan |
| NAM | 8,000 | 0.51 | 2.28 | 1.88 | 73% | 1,265 | -0.018 |
| ORB | 2,000 | 0.10 | 2.15 | 1.34 | 67% | 332 | -0.022 |
| VWR | 2,000 | -0.88 | 0.84 | -0.17 | 15% | 165 | -0.051 |

## In-sample leaderboard (top 15) — and what happened out of sample

| # | family | key params | trades/day | win % | IS Sharpe | OOS Sharpe | IS E[R] | OOS E[R] |
|---|---|---|---|---|---|---|---|---|
| 1 | NAM | {'band_mult': 0.8, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.04 | 33% | 2.28 | 1.88 | +0.354 | +0.288 |
| 2 | NAM | {'band_mult': 1.0, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 0.80 | 26% | 2.16 | 1.83 | +0.548 | +0.431 |
| 3 | ORB | {'or_len': 60, 'stop_frac': 0.25, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.00 | 28% | 2.15 | 1.34 | +0.382 | +0.218 |
| 4 | ORB | {'or_len': 60, 'stop_frac': 0.25, 'target_r': 4.0, 'regime_filter': 0, 'direction': 0} | 0.70 | 31% | 2.13 | 1.78 | +0.337 | +0.286 |
| 5 | NAM | {'band_mult': 0.8, 'trail_mode': 1, 'target_r': 3.0, 'regime_filter': 1, 'direction': 0} | 0.54 | 43% | 2.12 | 1.32 | +0.266 | +0.135 |
| 6 | ORB | {'or_len': 60, 'stop_frac': 0.25, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 0.80 | 27% | 2.12 | 1.56 | +0.425 | +0.293 |
| 7 | NAM | {'band_mult': 0.8, 'trail_mode': 0, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.64 | 31% | 2.08 | 2.09 | +0.289 | +0.238 |
| 8 | NAM | {'band_mult': 0.8, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.44 | 21% | 2.03 | 1.56 | +0.414 | +0.285 |
| 9 | NAM | {'band_mult': 1.0, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.17 | 24% | 2.02 | 1.63 | +0.396 | +0.324 |
| 10 | ORB | {'or_len': 60, 'stop_frac': 0.25, 'target_r': 4.0, 'regime_filter': 0, 'direction': 0} | 0.70 | 36% | 2.02 | 1.43 | +0.287 | +0.205 |
| 11 | NAM | {'band_mult': 0.8, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 0.96 | 39% | 2.01 | 2.19 | +0.272 | +0.278 |
| 12 | NAM | {'band_mult': 0.6, 'trail_mode': 1, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.20 | 34% | 2.01 | 1.75 | +0.230 | +0.175 |
| 13 | NAM | {'band_mult': 0.6, 'trail_mode': 0, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.13 | 30% | 1.99 | 1.46 | +0.360 | +0.215 |
| 14 | NAM | {'band_mult': 1.2, 'trail_mode': 0, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.07 | 33% | 1.99 | 1.44 | +0.284 | +0.174 |
| 15 | NAM | {'band_mult': 0.8, 'trail_mode': 1, 'target_r': 0.0, 'regime_filter': 0, 'direction': 0} | 1.17 | 36% | 1.98 | 1.93 | +0.321 | +0.248 |

## Topstep objective: walk-forward OOS trades through the 50K lifecycle simulator (1 year)

Empirical model: 718 OOS trades, 0.81 trades/day, net E[R] +0.133.

| risk $/trade | net mean $ | net median $ | P(net>0) | pass rate/attempt |
|---|---|---|---|---|
| 200 | -160 | -637 | 18% | 39% |
| 400 | 1,303 | -147 | 47% | 32% |
| 600 | 2,012 | 267 | 53% | 25% |
