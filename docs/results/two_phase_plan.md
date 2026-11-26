# Two-phase plan: prop until $100k withdrawn → trade it as your own account

Phase 1: 5 × Topstep 150K slots, decorrelated (ρ = 0.4), 35 % of max loss per trade ($1,575), cushion before payouts. Phase 2: switch when cumulative net prop cash ≥ $100,000; own account trades the same edge (MES-equivalent, ≤ 500 contracts/trade). 600 paths, 5-year horizon, pre-tax unless stated. Trade models are assumptions.


## Edge: basket_planning

**Phase 1:** P(reach $100,000 withdrawn within 5 y) = 96%; months to get there: median 21, 25th–75th pct 13–32.

| phase 2 variant | own risk/trade | wealth median 3y | median 5y | 5th pct 5y | P(own account ever −30 %) | P(−50 %) | median own-account return/yr after switch |
|---|---|---|---|---|---|---|---|
| stop prop at $100k | 0.5% | $116,651 | $153,759 | $83,711 | 5% | 0% | 18% |
| stop prop at $100k | 1.0% | $123,582 | $205,803 | $71,240 | 49% | 9% | 32% |
| stop prop at $100k | 2.0% | $123,996 | $289,298 | $44,183 | 91% | 59% | 50% |
| keep prop running, keep feeding | 0.5% | $203,611 | $464,548 | $101,422 | 2% | 0% | n/a (fed) |
| keep prop running, keep feeding | 1.0% | $227,054 | $576,909 | $98,587 | 31% | 3% | n/a (fed) |
| keep prop running, keep feeding | 2.0% | $235,725 | $733,244 | $83,291 | 84% | 45% | n/a (fed) |

## Edge: basket_optimistic

**Phase 1:** P(reach $100,000 withdrawn within 5 y) = 100%; months to get there: median 9, 25th–75th pct 7–13.

| phase 2 variant | own risk/trade | wealth median 3y | median 5y | 5th pct 5y | P(own account ever −30 %) | P(−50 %) | median own-account return/yr after switch |
|---|---|---|---|---|---|---|---|
| stop prop at $100k | 0.5% | $234,427 | $495,806 | $261,075 | 0% | 0% | 49% |
| stop prop at $100k | 1.0% | $490,889 | $2,092,028 | $550,468 | 14% | 0% | 115% |
| stop prop at $100k | 2.0% | $1,711,196 | $10,373,250 | $1,702,290 | 62% | 13% | 212% |
| keep prop running, keep feeding | 0.5% | $1,136,039 | $3,452,117 | $1,665,054 | 0% | 0% | n/a (fed) |
| keep prop running, keep feeding | 1.0% | $1,793,455 | $8,666,582 | $2,982,687 | 3% | 0% | n/a (fed) |
| keep prop running, keep feeding | 2.0% | $4,460,144 | $14,969,750 | $6,902,435 | 32% | 5% | n/a (fed) |

## Phase 2 alone: $100,000 of your own money, no further contributions

| edge | risk/trade | median after 1y | after 3y | 5th pct 3y | P(lose money over 3y) | P(drawdown ≥ 30 %) | median income if you withdraw gains yearly |
|---|---|---|---|---|---|---|---|
| zero_edge_basket | 0.5% | $87,348 | $67,905 | $44,898 | 92% | 75% | $0/trading day (year 1) |
| zero_edge_basket | 1.0% | $72,372 | $40,147 | $18,450 | 94% | 99% | $0/trading day (year 1) |
| basket_planning | 0.5% | $112,773 | $145,727 | $90,943 | 9% | 5% | $51/trading day (year 1) |
| basket_planning | 1.0% | $124,777 | $203,845 | $73,919 | 12% | 54% | $98/trading day (year 1) |
| basket_optimistic | 0.5% | $139,474 | $287,940 | $173,863 | 0% | 0% | $157/trading day (year 1) |
| basket_optimistic | 1.0% | $196,269 | $833,259 | $293,224 | 0% | 9% | $382/trading day (year 1) |
