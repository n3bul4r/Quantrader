# The $4k/month plan, in depth: 5 × Topstep 50K, $500 risk per trade

Start €300 ($348); every Combine ($49/month), renewal and $149 activation is paid from the bankroll (start money + top-ups + payouts); payouts buy new Combines until 5 accounts run. $500 risk per trade (25 % of the $2,000 max loss), daily stop $1,000, payouts only after a $2,000 cushion. Accounts trade different market mixes (ρ = 0.4). 1500 paths, 36 months. 'Net' = payouts − all fees (top-ups are your money, not income).

| edge | top-up | P(a 3-month stretch ≥ $4k/mo) by month 12 | by 24 | by 36 | median month it first happens | year-2 median $/mo | year-3 median $/mo | P(year-3 avg ≥ $4k) | 36-month net median | P(net loss after 3 y) |
|---|---|---|---|---|---|---|---|---|---|---|
| zero_edge_basket | €0/mo | 1% | 1% | 1% | 7 | $0 | $0 | 0% | $-196 | 98% |
| zero_edge_basket | €100/mo | 1% | 5% | 7% | 22 | $-115 | $-114 | 0% | $-4,275 | 75% |
| zero_edge_basket | €200/mo | 2% | 7% | 12% | 22 | $-217 | $-221 | 0% | $-4,970 | 65% |
| S1_planning | €0/mo | 1% | 3% | 4% | 16 | $0 | $0 | 0% | $-343 | 89% |
| S1_planning | €100/mo | 3% | 12% | 20% | 22 | $209 | $301 | 1% | $10,397 | 22% |
| S1_planning | €200/mo | 5% | 16% | 25% | 20 | $394 | $434 | 1% | $15,060 | 12% |
| basket_planning | €0/mo | 8% | 11% | 14% | 10 | $0 | $0 | 2% | $-196 | 85% |
| basket_planning | €100/mo | 19% | 46% | 68% | 19 | $1,073 | $1,431 | 13% | $41,676 | 11% |
| basket_planning | €200/mo | 27% | 59% | 79% | 17 | $1,503 | $1,731 | 15% | $52,215 | 3% |
| basket_optimistic | €0/mo | 29% | 31% | 32% | 5 | $0 | $0 | 27% | $-196 | 68% |
| basket_optimistic | €100/mo | 62% | 91% | 98% | 10 | $5,754 | $7,153 | 81% | $184,869 | 1% |
| basket_optimistic | €200/mo | 75% | 96% | 100% | 8 | $6,366 | $7,449 | 84% | $203,042 | 0% |

## Median net per month, by quarter (€100/month top-up)

| edge | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | Q8 | Q9 | Q10 | Q11 | Q12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| zero_edge_basket | $-148 | $-114 | $-114 | $-115 | $-115 | $-114 | $-114 | $-114 | $-114 | $-115 | $-114 | $-114 |
| S1_planning | $-164 | $-91 | $-98 | $-82 | $-65 | $-33 | $-24 | $64 | $11 | $48 | $80 | $45 |
| basket_planning | $-148 | $-82 | $-82 | $-33 | $268 | $511 | $719 | $795 | $901 | $979 | $1,065 | $1,205 |
| basket_optimistic | $-147 | $718 | $2,339 | $3,729 | $4,711 | $5,601 | $6,004 | $6,214 | $6,770 | $6,823 | $7,197 | $7,439 |

## Levers that move the planning case toward $4k/month

6 markets = MES, MNQ, M2K, MCL, MGC, M6E ≈ 3.2 effectively independent trades/day (assumption: equity indices count ≈ 1.3 markets because they are ~0.85 correlated). 10 accounts = 5 Topstep 50K + 5 at a second firm, approximated with Topstep 50K economics.

| setup (planning edge) | top-up | P(3-mo ≥ $4k by 24 / 36) | year-2 median $/mo | year-3 median $/mo | P(year-3 avg ≥ $4k) | 36-month net median | P(net loss) |
|---|---|---|---|---|---|---|---|
| 4 markets × 5 accounts | €100/mo | 46% / 68% | $1,073 | $1,431 | 13% | $41,676 | 11% |
| 6 markets × 5 accounts | €100/mo | 55% / 75% | $1,400 | $2,063 | 23% | $55,304 | 11% |
| 6 markets × 10 accounts | €100/mo | 64% / 81% | $2,571 | $3,794 | 48% | $100,461 | 13% |
| 6 markets × 10 accounts | €200/mo | 82% / 94% | $3,878 | $4,642 | 56% | $127,552 | 4% |
