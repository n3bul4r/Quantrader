# Edge search — real_MGC

Data: real data: ../data/real/MGC.parquet. Instrument MGC (all-in cost $3.70/RT). **12,144 configurations** across 4 families, searched in 24 s. In-sample = first 70 % of days, out-of-sample = last 30 %.

## Verdict on the search itself

| metric | value | meaning |
|---|---|---|
| best in-sample Sharpe | 0.42 | what a naive optimiser would show you |
| same config, out-of-sample Sharpe | 0.19 | what it actually did next |
| deflated Sharpe (P that the winner is real, 12,144 trials) | 0.00 | ≥ 0.95 required |
| deflated Sharpe with effective trials (≈ 41 independent bets) | 0.00 | configs are highly correlated; this is the fairer test |
| PBO (CSCV, 2000 splits) | 0.05 | ≥ 0.5 = the 'best' config is noise |
| walk-forward OOS Sharpe of the re-selection process | -1.42 | the honest number |
| walk-forward OOS mean daily R | -0.052 | |

## By family

| family | configs | median IS Sharpe | best IS Sharpe | its OOS Sharpe | share OOS > 0 | configs with win rate ≥ 60 % | their median OOS E[R] |
|---|---|---|---|---|---|---|---|
| LDM | 144 | -1.01 | 0.15 | -1.02 | 1% | 0 | +nan |
| NAM | 8,000 | -1.46 | 0.42 | 0.19 | 31% | 410 | -0.039 |
| ORB | 2,000 | -2.66 | 0.23 | -0.91 | 9% | 150 | -0.084 |
| VWR | 2,000 | -3.27 | -0.50 | -0.60 | 2% | 126 | -0.088 |

## In-sample leaderboard (top 15) — and what happened out of sample

| # | family | key params | trades/day | win % | IS Sharpe | OOS Sharpe | IS E[R] | OOS E[R] |
|---|---|---|---|---|---|---|---|---|
| 1 | NAM | {'band_mult': 1.0, 'trail_mode': 1, 'target_r': 3.0, 'regime_filter': -1, 'direction': 0} | 0.30 | 39% | 0.42 | 0.19 | +0.081 | +0.029 |
| 2 | NAM | {'band_mult': 0.8, 'trail_mode': 0, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.33 | 35% | 0.40 | 0.59 | +0.091 | +0.200 |
| 3 | NAM | {'band_mult': 1.2, 'trail_mode': 2, 'target_r': 3.0, 'regime_filter': -1, 'direction': 0} | 0.27 | 38% | 0.40 | 0.29 | +0.072 | +0.049 |
| 4 | NAM | {'band_mult': 1.5, 'trail_mode': 2, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.18 | 31% | 0.38 | 0.19 | +0.164 | +0.075 |
| 5 | NAM | {'band_mult': 1.0, 'trail_mode': 1, 'target_r': 3.0, 'regime_filter': -1, 'direction': 0} | 0.42 | 39% | 0.38 | -0.15 | +0.050 | -0.018 |
| 6 | NAM | {'band_mult': 0.8, 'trail_mode': 0, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.31 | 27% | 0.38 | -0.84 | +0.159 | -0.257 |
| 7 | NAM | {'band_mult': 1.2, 'trail_mode': 1, 'target_r': 0.0, 'regime_filter': 0, 'direction': 1} | 0.30 | 39% | 0.36 | 0.12 | +0.071 | +0.021 |
| 8 | NAM | {'band_mult': 0.8, 'trail_mode': 1, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.48 | 38% | 0.35 | 0.46 | +0.058 | +0.099 |
| 9 | NAM | {'band_mult': 1.0, 'trail_mode': 3, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.40 | 32% | 0.35 | 0.42 | +0.088 | +0.141 |
| 10 | NAM | {'band_mult': 0.8, 'trail_mode': 1, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.49 | 33% | 0.35 | -0.60 | +0.074 | -0.133 |
| 11 | NAM | {'band_mult': 1.2, 'trail_mode': 0, 'target_r': 0.0, 'regime_filter': 1, 'direction': 1} | 0.14 | 35% | 0.34 | -1.13 | +0.141 | -0.216 |
| 12 | NAM | {'band_mult': 1.5, 'trail_mode': 1, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.22 | 36% | 0.32 | -0.05 | +0.072 | -0.016 |
| 13 | NAM | {'band_mult': 1.2, 'trail_mode': 1, 'target_r': 3.0, 'regime_filter': -1, 'direction': 0} | 0.23 | 38% | 0.31 | -0.37 | +0.055 | -0.064 |
| 14 | NAM | {'band_mult': 1.5, 'trail_mode': 2, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.33 | 36% | 0.31 | 0.03 | +0.061 | +0.005 |
| 15 | NAM | {'band_mult': 1.5, 'trail_mode': 1, 'target_r': 0.0, 'regime_filter': -1, 'direction': 0} | 0.22 | 37% | 0.30 | 0.34 | +0.064 | +0.108 |

## Topstep objective: walk-forward OOS trades through the 50K lifecycle simulator (1 year)

Empirical model: 315 OOS trades, 0.20 trades/day, net E[R] -0.258.

| risk $/trade | net mean $ | net median $ | P(net>0) | pass rate/attempt |
|---|---|---|---|---|
| 200 | -619 | -637 | 0% | 1% |
| 400 | -657 | -686 | 1% | 4% |
| 600 | -674 | -735 | 2% | 6% |
