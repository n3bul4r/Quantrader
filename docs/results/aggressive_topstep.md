# Aggressive Topstep optimisation

Monte Carlo, 1,500 paths per cell. Trade models are assumptions (see AGGRESSIVE_SYSTEM.md §1). Rules: Topstep 2026 presets (partly secondary sources). Net = trader share of payouts − every fee.

## A. Single account slot, 2 years — best configuration per account type and edge

| edge model | account | eval risk $/trade (% of MLL) | funded policy | net mean 2y | net median 2y | P(net>0) | pass rate | evals bought |
|---|---|---|---|---|---|---|---|---|
| S1_planning | topstep_50k | 1000 (50%) | same risk funded | 4,029 | 353 | 52% | 16% | 35.7 |
| S1_planning | topstep_100k | 1500 (50%) | same risk funded | 5,054 | -766 | 46% | 15% | 36.0 |
| S1_planning | topstep_150k | 2250 (50%) | same risk funded | 8,523 | -410 | 49% | 15% | 36.8 |
| S1_planning | topstep_50k_consistency | 700 (35%) | same risk funded | 2,221 | 480 | 54% | 21% | 23.3 |
| S1_planning | topstep_150k_consistency | 1575 (35%) | same risk funded | 3,358 | -858 | 47% | 19% | 24.4 |
| basket_planning | topstep_50k | 1000 (50%) | same risk, cushion before payouts | 14,088 | 7,762 | 69% | 16% | 64.3 |
| basket_planning | topstep_100k | 1500 (50%) | same risk, cushion before payouts | 19,432 | 9,377 | 66% | 15% | 65.1 |
| basket_planning | topstep_150k | 2250 (50%) | same risk, cushion before payouts | 31,257 | 15,080 | 67% | 15% | 67.4 |
| basket_planning | topstep_50k_consistency | 500 (25%) | same risk funded | 6,355 | 4,789 | 74% | 24% | 28.4 |
| basket_planning | topstep_150k_consistency | 1125 (25%) | same risk, cushion before payouts | 11,210 | 7,650 | 67% | 22% | 29.9 |
| basket_optimistic | topstep_50k | 1000 (50%) | same risk, cushion before payouts | 36,849 | 38,493 | 94% | 22% | 36.7 |
| basket_optimistic | topstep_100k | 1500 (50%) | same risk, cushion before payouts | 53,409 | 55,176 | 91% | 21% | 38.1 |
| basket_optimistic | topstep_150k | 2250 (50%) | same risk, cushion before payouts | 86,970 | 86,758 | 92% | 21% | 40.3 |
| basket_optimistic | topstep_50k_consistency | 500 (25%) | same risk, cushion before payouts | 19,012 | 18,479 | 95% | 35% | 15.0 |
| basket_optimistic | topstep_150k_consistency | 1125 (25%) | same risk funded | 36,639 | 36,012 | 94% | 32% | 16.7 |

### Policy comparison (basket_planning, topstep_150k, risk 25 % of MLL)

| funded policy | net mean 2y | net median 2y | P(net>0) |
|---|---|---|---|
| same risk funded | 19,829 | 12,071 | 77% |
| half risk funded + scale-up 25 % | 13,053 | 6,266 | 75% |
| same risk, cushion before payouts | 20,001 | 12,104 | 77% |

## B. Fleet: several account slots at once, 3 years

Each slot re-buys a Combine whenever its account is lost. ρ = correlation of trade outcomes between slots (1.0 = copy-trading the same signals; 0.4 = different markets/strategies per slot).

| edge model | account | slots | ρ | net mean 1y | median 1y | mean 3y | median 3y | p05 3y | P(≥$100k by 3y) | median months to $100k | P(≥$1M by 3y) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| basket_planning | topstep_150k | 1 | 1.0 | 9,487 | 1,291 | 57,563 | 34,853 | -17,866 | 26% | 25 | 0% |
| basket_planning | topstep_150k | 3 | 1.0 | 24,539 | -5,498 | 167,403 | 99,107 | -55,830 | 53% | 19 | 0% |
| basket_planning | topstep_150k | 5 | 1.0 | 53,664 | 4,025 | 297,412 | 172,366 | -87,834 | 64% | 14 | 7% |
| basket_planning | topstep_150k | 5 | 0.4 | 42,367 | 32,686 | 256,345 | 231,185 | -1,976 | 80% | 18 | 0% |
| basket_optimistic | topstep_150k | 1 | 1.0 | 30,289 | 22,456 | 160,448 | 175,686 | 9,688 | 74% | 22 | 0% |
| basket_optimistic | topstep_150k | 3 | 1.0 | 81,394 | 50,067 | 471,867 | 512,042 | 14,016 | 90% | 14 | 0% |
| basket_optimistic | topstep_150k | 5 | 1.0 | 147,833 | 109,307 | 821,299 | 885,080 | 60,613 | 94% | 11 | 42% |
| basket_optimistic | topstep_150k | 5 | 0.4 | 139,357 | 132,013 | 776,808 | 794,048 | 335,983 | 100% | 10 | 17% |

## C. Flywheel: 5 diversified slots, payouts recycled into an own MES account, 3 years

Own account trades the same edge (sized as % of its equity per trade, no payout caps, capped at 500 MES ≈ 50 ES per trade for market capacity; its trades are simulated independently of the prop accounts, which flatters diversification). Fees are paid from the account when possible, otherwise out of pocket. Wealth = own account − out-of-pocket fees. Full Kelly for the per-trade edge is ≈ 2.5 % (planning); 4 % is over-betting.

| edge model | own-account risk/trade | wealth median 1y | median 3y | mean 3y | p05 3y | p95 3y | P(≥$100k) | P(≥$1M) |
|---|---|---|---|---|---|---|---|---|
| basket_planning | 1% | 34,097 | 304,483 | 386,011 | 3,525 | 1,068,697 | 86% | 6% |
| basket_planning | 2% | 37,073 | 344,057 | 615,163 | 6,137 | 2,092,597 | 89% | 18% |
| basket_planning | 4% | 36,854 | 355,278 | 1,063,417 | -6,254 | 5,301,929 | 89% | 33% |
| basket_optimistic | 1% | 163,343 | 1,857,995 | 2,256,947 | 639,330 | 5,144,514 | 100% | 87% |
| basket_optimistic | 2% | 200,614 | 4,478,685 | 5,172,389 | 996,224 | 11,137,815 | 100% | 97% |
| basket_optimistic | 4% | 281,356 | 7,890,320 | 8,105,513 | 1,865,670 | 14,774,589 | 100% | 99% |

## D. The speed limit: growth law and payout ceilings

Years to multiply capital at Kelly leverage — growth rate g = c(2−c)/2 · Sharpe² (c = Kelly fraction):

| annual Sharpe | ×10 full Kelly | ×10 half Kelly | ×100 full | ×100 half | ×1000 full | ×1000 half |
|---|---|---|---|---|---|---|
| 0.5 | 18.4 | 24.6 | 36.8 | 49.1 | 55.3 | 73.7 |
| 1.0 | 4.6 | 6.1 | 9.2 | 12.3 | 13.8 | 18.4 |
| 1.5 | 2.0 | 2.7 | 4.1 | 5.5 | 6.1 | 8.2 |
| 2.0 | 1.2 | 1.5 | 2.3 | 3.1 | 3.5 | 4.6 |
| 3.0 | 0.5 | 0.7 | 1.0 | 1.4 | 1.5 | 2.0 |

Theoretical maximum XFA extraction per year if *every* payout cycle hits the cap in the minimum number of days (requires earning ≥ 2× the cap per cycle, because payouts are limited to 50 % of the balance):

| account / path | cap per payout | min days per cycle | 1 account | 5 accounts | daily profit needed per account |
|---|---|---|---|---|---|
| 50K Standard | $2,000 | 5 | $90,720 | $453,600 | $800 |
| 150K Standard | $5,000 | 5 | $226,800 | $1,134,000 | $2,000 |
| 50K Consistency | $3,000 | 3 | $226,800 | $1,134,000 | $2,000 |
| 150K Consistency | $6,000 | 3 | $453,600 | $2,268,000 | $4,000 |
