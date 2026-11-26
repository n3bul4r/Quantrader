# The plan for $4,000 a month, starting from €300

*2026-11-26. Simulations: [results/find_4k_plan_assumed.md](results/find_4k_plan_assumed.md) (162-plan search),
[results/best_4k_plan.md](results/best_4k_plan.md) (deep dive). Scripts: `engine/scripts/find_4k_plan.py`,
`engine/scripts/best_4k_plan.py`.*

## The answer
* **Strategy:** intraday momentum (noise-area breakout) on up to six micro futures: MES, MNQ, M2K, MCL, MGC, M6E.
  * Fully automated, flat every evening.
  * Only markets that pass the validation gate on real data are traded.
* **Accounts:** Topstep **50K** (about $49/month) at **$500 risk per trade**.
  * Build up to 5 Topstep accounts from payouts.
  * Then add 5 more at a second firm (10 accounts).
* **Money:** start with €300. **Add €100–200 a month**, used only for Combine fees and renewals.
* **The single most important step comes first:** validate the strategy on real data (free, see step 0).
  Every number below assumes it passes.

### What it produces (36-month simulations, all fees included)

| setup | year-2 median per month | year-3 median per month | P(year-3 average ≥ $4k) | P(a 3-month stretch ≥ $4k within 2 years) | 3-year net (median) | P(net loss) |
|---|---|---|---|---|---|---|
| 4 markets, 5 accounts, €100/mo | $1,073 | $1,431 | 13 % | 46 % | $41.7k | 11 % |
| 6 markets, 5 accounts, €100/mo | $1,400 | $2,063 | 23 % | 55 % | $55.3k | 11 % |
| 6 markets, 10 accounts, €100/mo | $2,571 | $3,794 | 48 % | 64 % | $100.5k | 13 % |
| **6 markets, 10 accounts, €200/mo** | **$3,878** | **$4,642** | **56 %** | **82 %** | **$127.6k** | **4 %** |
| 4 markets, 5 accounts, €100/mo, *optimistic edge* | $5,754 | $7,153 | 81 % | 91 % | $184.9k | 1 % |
| any setup, **no edge** | lose your top-ups | | 0 % | | −$4–5k | 65–98 % |

Notes:
* The rows use the "planning" edge (the published edge minus a 58 % decay haircut) unless marked optimistic.
* **$4k a month is a year-2/year-3 result, not a month-3 result.** Months 1–6 are about getting the first accounts
  funded; the median is still slightly negative while Combines are being bought.
* **Why this plan won the search:** ranking only by "chance of $4k" favours 150K accounts. Their *median* is stuck
  at −$124 a month, because a €300 bankroll can't keep re-buying $149 Combines. The 50K / $500 plan has the best
  median and the lowest loss risk, and it is also best outright when the edge is strong.

## Step 0: prove the edge on real data (free, ~1 week)
1. **Download the data.** Create a Databento account (new accounts get **$125 of free credit**). Then:
   * dataset `GLBX.MDP3`, schema `ohlcv-1m`, symbology `continuous`;
   * symbols `ES.v.0 NQ.v.0 RTY.v.0 CL.v.0 GC.v.0 6E.v.0`. The full-size contracts give a longer history and the
     same price moves as the micros you'll trade;
   * start 2012-01-01, CSV export. Check the cost estimate in the portal first; 1-minute bars should be small.
2. **Save the files** as `data/real/MES.csv`, `MNQ.csv`, `M2K.csv`, `MCL.csv`, `MGC.csv`, `M6E.csv` (the file name
   sets the micro contract's costs and session hours). The loader reads Databento's `ts_event` and `symbol`
   columns and rolls by volume.
   * Free alternative: Dukascopy's web export for the CFD equivalents (US500, USTEC, US2000, Light crude, XAUUSD,
     EURUSD). That works for research, but futures data is better.
3. **Run:** `cd engine && python scripts/find_4k_plan.py --data-dir ../data/real`. It:
   * searches each market (thousands of configurations);
   * applies the gate: walk-forward OOS Sharpe > 0.5, PBO < 20 %, deflated Sharpe ≥ 0.95;
   * replays the surviving markets' out-of-sample trades day by day across accounts, with real correlations;
   * re-optimises the account plan on that.
4. **Decide.** If no market passes, don't buy anything. If 2–3 pass, the plan still works, just slower; the
   results file tells you how much slower.

## The strategy (per market, identical rules)
* **Session (ET):**

  | market | session |
  |---|---|
  | MES, MNQ, M2K | 09:30–16:00 |
  | MCL | 09:00–14:30 |
  | MGC | 08:20–13:30 |
  | M6E | 08:20–15:00 |

* **Noise band at minute m:**
  * σₘ = average over the last 14 days of |price at minute m ÷ that day's open − 1|;
  * upper = max(today's open, yesterday's close) × (1 + σₘ); lower = min(today's open, yesterday's close) × (1 − σₘ).
* **Entry:** at every :00 and :30, from 30 minutes after the open until 30 minutes before the close: buy if the bar
  closes above the upper band, sell short if it closes below the lower band. Reversal allowed, at most 3 entries per
  market per day.
* **Stop:** the band or VWAP, whichever is closer to price, but at least 0.5 σ away. It is a server-side bracket
  order, re-checked every 30 minutes and only ever moved in your favour.
* **Exit:** stop, trailing exit, or market 1 minute before the session close. Never overnight.
* **Size: $500 risk per trade.** Contracts = $500 ÷ (stop distance × $ per point + costs).
  * MES and MNQ signalling the same way share the $500 ($250 each).
* **Daily limits:**
  * stop the account for the day at −$1,000;
  * stop after 3 losses in a row;
  * during the Combine only, stop at +$1,350 for the day (keeps the 50 % consistency target safe).
* **Per account:** each account trades a different mix of the validated markets, so the accounts don't all lose on
  the same day.

## Account and money rules, step by step
1. **Month 0:** buy one Topstep 50K Combine (≈ $49).
   * Keep $149 untouched for the activation fee.
   * Bots are allowed via the TopstepX API on Combine and funded (XFA) accounts.
2. **On failure:** buy the next Combine from the bankroll; never skip the rules to "win it back".
3. **Every month:** add €100–200 to the bankroll. €200 roughly doubles the odds of the 10-account outcome.
4. **Funded:** wait until the account is $2,000 in profit, then request the maximum payout every cycle.
5. **Payouts:** each one funds the next Combine until you have **5 funded Topstep 50Ks**. Spare cash stays in the
   bankroll as the reserve.
6. **Then add a second firm,** up to 5 accounts. Use 50K end-of-day-drawdown accounts and buy them during discount
   periods.
   * Apex reportedly forbids fully automated trading on funded accounts, so those run semi-automatic: the engine
     sends the bracket, you click.
   * Check each firm's rules on running the same strategy across firms.
7. **At $100k withdrawn:** switch to the two-phase plan (AGGRESSIVE_SYSTEM §3.6b) and keep the accounts running.

## What can still go wrong
* **The edge fails on real data.** That's the most likely single outcome; Step 0 exists to make it cost €0.
* **Firm rule changes:** caps, max accounts (sources say 3–5 funded at Topstep), automation rules. Presets are
  editable data; re-run the plan when they change.
* **Model assumptions to check:**
  * "3.2 effectively independent trades/day on 6 markets" and "second firm ≈ Topstep 50K economics";
  * the real-data run replaces both.
* **Execution:** automation outages, roll days, platform downtime near the close.
* **Behaviour:** turning off the bot after a losing month. The months-1–6 median is slightly negative *by design*.
* **Tax:** not modelled. Prop payouts are usually taxed as income.
