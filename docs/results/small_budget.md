# Starting with €300: bootstrap into a prop fleet

Bankroll $348 (€300). Every Combine purchase, monthly renewal and activation fee is paid from the bankroll (start money + payouts); a new Combine is only bought when the bankroll still covers its activation fee afterwards. Payouts buy more accounts, up to 5. ρ = 0.4 between slots, payout once profit ≥ max loss. 800 paths, 3 years. Net = bankroll − €300 start. Trade models are assumptions; firm prices vary with promotions.


## Topstep 50K Trading Combine -> Express Funded (Standard payout path)

| edge | risk/trade (% of max loss) | P(ever ahead) | P(busted) | median net 1y | mean net 1y | mean net 3y | P(≥$10k by 3y) | P(≥$100k by 3y) | median months to $10k |
|---|---|---|---|---|---|---|---|---|---|
| S1_planning | $200 (10%) | 6% | 98% | $-343 | $-271 | $-123 | 1% | 0% | 23 |
| S1_planning | $300 (15%) | 16% | 92% | $-343 | $44 | $677 | 5% | 0% | 24 |
| S1_planning | $500 (25%) | 20% | 89% | $-343 | $929 | $2,999 | 10% | 0% | 12 |
| S1_planning | $700 (35%) | 15% | 91% | $-245 | $956 | $3,105 | 8% | 1% | 11 |
| basket_planning | $200 (10%) | 31% | 78% | $-343 | $1,405 | $4,702 | 19% | 0% | 16 |
| basket_planning | $300 (15%) | 32% | 74% | $-294 | $3,396 | $10,515 | 25% | 0% | 10 |
| basket_planning | $500 (25%) | 21% | 85% | $-196 | $3,680 | $11,085 | 14% | 4% | 5 |
| basket_planning | $700 (35%) | 15% | 90% | $-196 | $3,067 | $10,526 | 10% | 5% | 5 |
| basket_optimistic | $200 (10%) | 57% | 46% | $4,245 | $9,837 | $38,954 | 54% | 8% | 9 |
| basket_optimistic | $300 (15%) | 54% | 48% | $5,944 | $17,307 | $61,248 | 52% | 33% | 5 |
| basket_optimistic | $500 (25%) | 36% | 68% | $-196 | $17,732 | $72,564 | 32% | 30% | 4 |
| basket_optimistic | $700 (35%) | 24% | 79% | $-196 | $13,273 | $61,003 | 20% | 20% | 4 |
| zero_edge_basket | $200 (10%) | 8% | 100% | $-343 | $-279 | $-304 | 0% | 0% | 24 |
| zero_edge_basket | $300 (15%) | 12% | 96% | $-245 | $-49 | $-39 | 1% | 0% | 19 |
| zero_edge_basket | $500 (25%) | 10% | 97% | $-196 | $-25 | $26 | 2% | 0% | 8 |
| zero_edge_basket | $700 (35%) | 6% | 98% | $-196 | $-124 | $-131 | 2% | 0% | 8 |

## Apex 50K EOD at a ~70 % discount ($30 eval, $99 activation)

| edge | risk/trade (% of max loss) | P(ever ahead) | P(busted) | median net 1y | mean net 1y | mean net 3y | P(≥$10k by 3y) | P(≥$100k by 3y) | median months to $10k |
|---|---|---|---|---|---|---|---|---|---|
| S1_planning | $200 (10%) | 58% | 47% | $-240 | $342 | $3,649 | 14% | 0% | 28 |
| S1_planning | $300 (15%) | 45% | 59% | $-240 | $1,080 | $5,039 | 26% | 0% | 24 |
| S1_planning | $500 (25%) | 33% | 73% | $-249 | $1,302 | $4,689 | 23% | 0% | 20 |
| S1_planning | $700 (35%) | 26% | 83% | $-309 | $642 | $2,544 | 14% | 0% | 20 |
| basket_planning | $200 (10%) | 59% | 44% | $868 | $3,235 | $13,807 | 49% | 0% | 18 |
| basket_planning | $300 (15%) | 46% | 58% | $-240 | $3,989 | $14,380 | 41% | 0% | 13 |
| basket_planning | $500 (25%) | 31% | 74% | $-279 | $3,203 | $10,369 | 25% | 0% | 10 |
| basket_planning | $700 (35%) | 22% | 84% | $-279 | $1,650 | $5,701 | 16% | 0% | 10 |
| basket_optimistic | $200 (10%) | 90% | 10% | $12,873 | $13,978 | $65,103 | 90% | 8% | 10 |
| basket_optimistic | $300 (15%) | 74% | 26% | $16,330 | $16,397 | $62,178 | 74% | 18% | 7 |
| basket_optimistic | $500 (25%) | 50% | 51% | $-240 | $13,166 | $44,933 | 49% | 18% | 6 |
| basket_optimistic | $700 (35%) | 40% | 63% | $-249 | $8,157 | $28,492 | 37% | 5% | 7 |
| zero_edge_basket | $200 (10%) | 16% | 93% | $-240 | $-21 | $60 | 1% | 0% | 16 |
| zero_edge_basket | $300 (15%) | 17% | 93% | $-249 | $92 | $231 | 2% | 0% | 19 |
| zero_edge_basket | $500 (25%) | 14% | 95% | $-279 | $159 | $203 | 3% | 0% | 13 |
| zero_edge_basket | $700 (35%) | 10% | 99% | $-279 | $-230 | $-193 | 1% | 0% | 14 |

## The biggest lever: adding €100/month ($116) to the bankroll

Net = payouts − every fee, i.e. the result versus everything you put in (€300 + €100/month = $4,524 over 3 years).

| firm | edge | risk/trade | top-up | P(busted) | median net 3y | mean net 3y | 5th pct 3y | P(≥$10k) | P(≥$100k) | median months to $10k |
|---|---|---|---|---|---|---|---|---|---|---|
| topstep_50k | basket_planning | $300 | none | 74% | $-294 | $10,515 | $-494 | 25% | 0% | 10 |
| topstep_50k | basket_planning | $300 | €100/mo | 3% | $29,484 | $31,095 | $-2,314 | 84% | 1% | 16 |
| topstep_50k | zero_edge_basket | $300 | none | 96% | $-294 | $-39 | $-494 | 1% | 0% | 19 |
| topstep_50k | zero_edge_basket | $300 | €100/mo | 50% | $-4,113 | $-922 | $-4,446 | 10% | 0% | 21 |
| topstep_50k | basket_planning | $500 | none | 85% | $-196 | $11,085 | $-494 | 14% | 4% | 5 |
| topstep_50k | basket_planning | $500 | €100/mo | 10% | $38,649 | $47,633 | $-4,304 | 78% | 14% | 15 |
| topstep_50k | zero_edge_basket | $500 | none | 97% | $-196 | $26 | $-494 | 2% | 0% | 8 |
| topstep_50k | zero_edge_basket | $500 | €100/mo | 63% | $-4,275 | $-181 | $-4,414 | 16% | 0% | 19 |
| apex_50k_eod_discounted | basket_planning | $200 | none | 44% | $8,917 | $13,807 | $-507 | 49% | 0% | 18 |
| apex_50k_eod_discounted | basket_planning | $200 | €100/mo | 0% | $21,445 | $23,346 | $4,799 | 84% | 0% | 20 |
| apex_50k_eod_discounted | zero_edge_basket | $200 | none | 93% | $-249 | $60 | $-507 | 1% | 0% | 16 |
| apex_50k_eod_discounted | zero_edge_basket | $200 | €100/mo | 6% | $-1,437 | $-424 | $-4,290 | 2% | 0% | 24 |

## For comparison: €300 traded as your own account (CFD, 1 % risk per trade, no contributions)

| edge | median after 1 y | after 3 y | P(below €300 at 3 y) |
|---|---|---|---|
| Day trading with NO edge (costs only), CFD, 1 % risk | €277 | €240 | 80% |
| S1 planning edge, CFD, 1 % risk/trade | €321 | €367 | 24% |
| S1 optimistic edge, CFD, 1 % risk/trade | €360 | €526 | 3% |
