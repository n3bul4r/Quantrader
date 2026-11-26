# Best plan for $4,000/month — real

Start $348 (€300) + $116/month (€100). Every Combine, renewal and activation fee is paid from that bankroll plus payouts; payouts buy more accounts. Target = average monthly net cash (payouts − all fees) over months 13-24 ≥ $4,000. 500 paths per plan; plans searched: account size × risk/trade × number of accounts × payout cushion (54 per edge).

## Validation gate per market (real data)

| market | days | configs | walk-forward OOS Sharpe | PBO | deflated Sharpe (eff.) | strict gate | candidate |
|---|---|---|---|---|---|---|---|
| MES | 2041 | 24 | -0.27 | 44% | 0.85 | fail | — |
| MNQ | 2097 | 24 | 0.72 | 54% | 0.99 | PASS | — |

## Edge: real (walk-forward OOS trades, day replay)

**Best plan:** 5 × topstep_150k at $1125/trade (25% of max loss), markets per account: all, payout cushion $4,500. P(≥ $4,000/month in year 2) = **3%**; year-2 monthly net: median $-124 (25–75 %: $-137 … $-117); P(any 3-month stretch ≥ $4,000/month) 7%, first reached around month 15 (median); P(net loss after 2 years) 88%.

| rank | account | risk/trade | accounts | markets per account | cushion | P(≥ target, yr 2) | yr-2 median $/month | yr-2 mean | P(any 3-mo ≥ target) | P(2-yr net < 0) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | topstep_150k | $1125 (25%) | 5 | all | $4,500 | 3% | $-124 | $131 | 7% | 88% |
| 2 | topstep_150k | $1125 (25%) | 5 | all | $0 | 2% | $-124 | $108 | 7% | 88% |
| 3 | topstep_150k | $1125 (25%) | 3 | all | $0 | 2% | $-124 | $106 | 9% | 85% |
| 4 | topstep_150k | $1125 (25%) | 3 | all | $4,500 | 2% | $-124 | $115 | 10% | 85% |
| 5 | topstep_50k | $700 (35%) | 5 | all | $2,000 | 2% | $-114 | $249 | 11% | 77% |
| 6 | topstep_100k | $1050 (35%) | 3 | all | $0 | 2% | $-116 | $139 | 8% | 83% |
| 7 | topstep_100k | $1050 (35%) | 3 | all | $3,000 | 2% | $-116 | $136 | 8% | 83% |
| 8 | topstep_100k | $1050 (35%) | 5 | all | $3,000 | 2% | $-116 | $142 | 8% | 86% |
| 9 | topstep_150k | $1575 (35%) | 5 | all | $0 | 2% | $-124 | $133 | 7% | 88% |
| 10 | topstep_150k | $1575 (35%) | 5 | all | $4,500 | 2% | $-124 | $149 | 7% | 88% |

Month-by-month net cash of the best plan (25th / median / 75th percentile):

| month | 3 | 6 | 9 | 12 | 15 | 18 | 21 | 24 |
|---|---|---|---|---|---|---|---|---|
| net $ | -149 / **-149** / 0 | -298 / **-149** / -149 | -149 / **-149** / -149 | -149 / **-149** / 0 | -298 / **-149** / -149 | -149 / **-149** / -149 | -149 / **-149** / 0 | -298 / **-149** / -149 |

## Fixed plans on the real trades, 36 months (50K accounts, $500 risk/trade, $2,000 payout cushion)

All accounts trade the same validated market(s) on the same historical days (perfectly correlated when only one market passes).

| accounts | top-up | year-2 median $/mo | year-3 median $/mo | P(year-3 avg ≥ target) | P(a 3-month stretch ≥ target) | 36-month net median | P(net loss) |
|---|---|---|---|---|---|---|---|
| 1 | €100/mo | $-61 | $-53 | 0% | 0% | $-1,018 | 59% |
| 1 | €200/mo | $-61 | $-53 | 0% | 0% | $-1,033 | 59% |
| 5 | €100/mo | $-111 | $-114 | 2% | 14% | $-4,279 | 74% |
| 5 | €200/mo | $-225 | $-225 | 3% | 25% | $-5,883 | 62% |
| 10 | €100/mo | $-114 | $-114 | 3% | 14% | $-4,320 | 79% |
| 10 | €200/mo | $-225 | $-229 | 4% | 22% | $-8,348 | 73% |
