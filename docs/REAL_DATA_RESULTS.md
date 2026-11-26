# Real-data results (HistData 1-minute, 2018 → Nov 2026)

*2026-11-26. Data: HistData.com free 1-minute quotes: SPXUSD (S&P 500), NSXUSD (Nasdaq-100), XAUUSD (gold),
EURUSD (2018 → Nov 2026), WTIUSD (crude, 2018–2023; not published after 2023). Volume is not provided, so VWAP
becomes a time-weighted average. Costs: micro-futures all-in costs (fees plus 2 ticks of slippage).
Reproduce: `engine/scripts/fetch_histdata.py` → `import_histdata.py` → `edge_search.py` / `find_4k_plan.py`.
Per-market reports: [results/edge_search_real_*.md](results/), plan run: [results/find_4k_plan_real.md](results/find_4k_plan_real.md).*

## 1. Which markets have an edge after costs?

| market | big search (12k configs): walk-forward OOS Sharpe | same, 3 other config samples | 24 variants fixed in advance: WF OOS Sharpe | share of those variants profitable OOS | verdict |
|---|---|---|---|---|---|
| **Nasdaq-100 (MNQ)** | **+0.31** | **+0.50 / +0.96 / +0.81** | **+0.72** (1,512 OOS days; deflated Sharpe 0.99) | **83 %** | **real edge** |
| S&P 500 (MES) | −0.18 | +0.14 / −0.50 / +0.13 | −0.27 | 8 % | no robust edge (gross edge ≈ costs) |
| Gold (MGC) | −1.42 | | | | fails |
| Crude (MCL, to 2023) | −1.21 | | | | fails |
| EUR/USD (M6E) | −1.34 | | | | fails |

* **S&P 500:** the published strategy makes about 0.7 index points per trade *before* costs, positive in 7 of 9
  years. A micro round trip costs about 0.78 points, so after costs it is roughly break-even.
* **Gold, crude, EUR/USD:** intraday moves are too small relative to micro costs, and most configurations lose
  money after costs.
* **High-win-rate variants** (profit targets) lose money out of sample on every market. A 1R target turns the
  Nasdaq edge negative.

## 2. The Nasdaq edge, in detail (walk-forward out-of-sample trades, after costs)
* **Per trade:** 0.89 trades a day, +0.10R net per trade, 33 % winners.
* **The pay-off comes from rare big winners:** the 95th percentile trade is +3.5R, the 99th is +9.7R.
* **Annual Sharpe 0.72**, but with up to 10 losing days in a row and a maximum drawdown of **30R** (50–60R for
  some variants).
* **Year by year,** the variant with a fixed stop and exit at the close was positive in 7 of 9 years
  (2019 and 2025 negative).

## 3. Why it still doesn't make $4k/month at Topstep
A Topstep 50K closes the account after a $2,000 loss from the peak. At $500 risk per trade that is **4R of room**,
against historical drawdowns of 30R+, so accounts usually die before the big winners arrive.

2-year net per account slot on the real trades (re-buying the Combine whenever it fails, all fees included):

| account | risk / trade | net mean | net median | P(net > 0) |
|---|---|---|---|---|
| Topstep 150K | 35 % ($1,575) | +$4,322 (≈ $180/month) | −$2,640 | 37 % |
| Topstep 150K | 25 % | +$2,993 | −$2,157 | 38 % |
| Topstep 50K | 25 % ($500) | +$1,436 | −$954 | 36 % |
| Topstep 50K static drawdown (Labs) | 15 % | +$1,386 | −$298 | 46 % |
| Topstep 150K, Consistency path | any | negative | | ≤ 28 % |
| Apex 50K end-of-day drawdown | 10 % | +$179 | −$598 | 39 % |

* **Fleet plans from €300 + €100–200/month on these trades:** median −$1k to −$8k over 3 years; a 59–79 % chance
  of a net loss; a 0–4 % chance of averaging $4k/month in year 3.
* **Exit changes don't fix it.** Scaling out (half the position at +2R, half rides to the close) keeps a Sharpe
  of 0.67 and shortens losing streaks to 7 days, but drawdowns stay around 50R.
* **On your own capital** (no knock-out), the same edge at half-Kelly sizing (≈ 1.1 % risk per trade) expects
  roughly 25 %/yr with ~36 % volatility. $4k/month would need **≈ $185k** of capital.

## 4. What changed versus the earlier plan
The earlier $4k plan assumed a 4–6 market basket (≈ 2.4–3.2 independent trades a day) with a smoother pay-off.
Real data says only **one market** has an edge after costs, and its pay-off is **fat-tailed**. Those two facts
remove both levers the plan relied on: breadth, and survival inside a 4R drawdown.

## 5. Honest bottom line
* **The Nasdaq intraday momentum edge looks real** (6 years out of sample, robust to how the search is run), but it
  is modest and lumpy.
* **Inside Topstep it is a lottery ticket with a small positive mean and a typically negative result.** Expect
  about +$50–180 a month per account slot on average, while most slots lose their fees.
* **$4k a month is not achievable** with this edge, a €300 budget and prop-firm drawdown rules.
* **Next steps that could change this:**
  1. **Forward-test the Nasdaq strategy on paper for 3 months.** Topstep's Combine is itself a cheap forward test:
     one 50K static or standard account at 10–15 % risk.
  2. **New strategy families with more frequent, smaller wins.** Session gaps and event days (CPI, FOMC) are next
     in the research queue; the engine and gate are ready.
  3. **Full-size NQ instead of MNQ** once account size allows. It costs about 40 % less per index point, which
     lifts net edge from +0.10R to about +0.11R: helpful, not transformative.
  4. **Grow own capital.** This edge fits own capital (no knock-out) far better than a trailing-drawdown account.
