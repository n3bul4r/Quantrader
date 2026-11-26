# One Topstep 50K at ~$500 risk per trade — what a month really pays

Funded-account economics: account starts funded, trades 6 months, a lost account is NOT replaced. Topstep 50K XFA rules (max loss $2,000 EOD-trailing, payouts after 5 winning days ≥ $150, up to 50 % of the balance, cap $2,000 per payout, 90 % to you). Daily stop 2R. Trade models are assumptions.

## 1. '$500 per trade' is risk, not profit

| edge model | win rate | avg win / avg loss at $500 risk | expected profit per trade | trades/day | expected P&L per month (before rules) | risk per trade needed for $3,500/month |
|---|---|---|---|---|---|---|
| S1_planning | 37% | +$925 / −$475 | **$32** | 0.8 | $535 | $3,271 (164% of the $2,000 max loss) |
| basket_planning | 37% | +$925 / −$475 | **$32** | 2.4 | $1,605 | $1,090 (55% of the $2,000 max loss) |
| basket_optimistic | 40% | +$925 / −$475 | **$74** | 2.4 | $3,709 | $472 (24% of the $2,000 max loss) |

## 2. Passing the 50K Combine (one attempt)

| edge model | risk/trade | P(pass) | P(fail) | median days to pass |
|---|---|---|---|---|
| S1_planning | $200 | 37% | 59% | 99.0 |
| S1_planning | $300 | 32% | 67% | 48.0 |
| S1_planning | $500 | 25% | 75% | 22.0 |
| basket_planning | $200 | 39% | 61% | 40.0 |
| basket_planning | $300 | 32% | 68% | 19.0 |
| basket_planning | $500 | 24% | 76% | 10.0 |
| basket_optimistic | $200 | 61% | 39% | 36.0 |
| basket_optimistic | $300 | 48% | 52% | 18.0 |
| basket_optimistic | $500 | 35% | 65% | 10.0 |
| zero_edge_basket | $200 | 15% | 85% | 39.0 |
| zero_edge_basket | $300 | 15% | 85% | 18.0 |
| zero_edge_basket | $500 | 13% | 87% | 9.0 |

## 3. One funded 50K, first 6 months

| edge model | risk/trade | P(account lost within 6 months) | average payout per month (mean) | (median) | P(≥ $3,000/month on average) | P(no payout at all) |
|---|---|---|---|---|---|---|
| S1_planning | $200 | 90% | $113 | $45 | 0% | 26% |
| S1_planning | $300 | 96% | $146 | $42 | 0% | 39% |
| S1_planning | $500 | 97% | $175 | $0 | 0% | 60% |
| basket_planning | $200 | 98% | $161 | $52 | 0% | 30% |
| basket_planning | $300 | 99% | $193 | $30 | 0% | 47% |
| basket_planning | $500 | 98% | $230 | $0 | 1% | 68% |
| basket_optimistic | $200 | 94% | $312 | $97 | 0% | 18% |
| basket_optimistic | $300 | 96% | $381 | $94 | 0% | 34% |
| basket_optimistic | $500 | 91% | $481 | $0 | 4% | 57% |
| zero_edge_basket | $200 | 100% | $73 | $19 | 0% | 50% |
| zero_edge_basket | $300 | 100% | $86 | $0 | 0% | 62% |
| zero_edge_basket | $500 | 100% | $99 | $0 | 0% | 78% |

## 4. Several funded 50Ks (different market mix per account, ρ = 0.4), first 6 months

| edge model | accounts | risk/trade | average payout per month (mean) | (median) | P(≥ $3,000/month) | P(all accounts lost) |
|---|---|---|---|---|---|---|
| basket_planning | 1 | $300 | $215 | $43 | 0% | — |
| basket_planning | 3 | $300 | $617 | $281 | 3% | — |
| basket_planning | 5 | $300 | $975 | $566 | 6% | — |
| basket_planning | 5 | $500 | $1,157 | $535 | 12% | — |
| basket_optimistic | 1 | $300 | $436 | $114 | 0% | — |
| basket_optimistic | 3 | $300 | $1,161 | $617 | 9% | — |
| basket_optimistic | 5 | $300 | $1,915 | $1,318 | 22% | — |
| basket_optimistic | 5 | $500 | $2,295 | $1,284 | 31% | — |

## 5. Bigger and more accounts (payout only after a cushion = max loss), first 6 months, no replacement

| edge model | setup | risk/trade | average payout per month (mean) | (median) | P(≥ $3,000/month) | P(no payout at all) |
|---|---|---|---|---|---|---|
| basket_planning | 1 × 50K | $500 | $263 | $0 | 1% | 69% |
| basket_planning | 1 × 150K | $1125 | $620 | $0 | 7% | 70% |
| basket_planning | 5 × 50K | $500 | $1,213 | $504 | 13% | 30% |
| basket_planning | 3 × 150K | $1125 | $1,573 | $473 | 18% | 45% |
| basket_optimistic | 1 × 50K | $500 | $512 | $0 | 5% | 60% |
| basket_optimistic | 1 × 150K | $1125 | $1,191 | $0 | 15% | 61% |
| basket_optimistic | 5 × 50K | $500 | $2,418 | $1,408 | 34% | 19% |
| basket_optimistic | 3 × 150K | $1125 | $3,192 | $1,028 | 33% | 32% |
