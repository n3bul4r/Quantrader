# Trading your own money: €500 start + €100/month

*Study date 2026-11-26. Full tables: [results/own_capital_growth.md](results/own_capital_growth.md). Reproduce
with `python engine/scripts/own_capital_growth.py`. Interactive version: the dashboard's **Growth planner** page.*

## 1. Research: what changes without a prop firm

### 1.1 The vehicle problem: €500 is too small for futures
| | MES micro futures | US500 index CFD (EU broker) |
|---|---|---|
| Smallest position | 1 contract = **$5 per point** | IG lists a 0.10 minimum size. Many EU brokers trade in steps worth about $0.10–1 per point |
| Risk of one typical S1 trade (22-point stop) | **≈ $110 ≈ 19 % of €500** | $2.20 per $0.10/pt step, so 1 % risk is possible from day one |
| Intraday margin | $40–50 at discount brokers (NinjaTrader, Tradovate, AMP, Optimus); $125 at StoneX; ≈ $2,500 overnight | 5 % of notional (ESMA 1:20 for major indices) |
| Costs per round turn | ≈ $1.9 fees + 2 ticks slippage ≈ **$4.40** (3–4 % of R) | 0.4–0.7 point spread + slippage ≈ 0.85 pt (≈ 4 % of R) |
| Day-trading rules | CFTC rules, not FINRA. No $25k minimum | No minimum. Negative-balance protection |
| Main drawback | Can't be sized properly until ≈ **€8,000** (1 contract = 1.25 % risk) | The broker is your counterparty. **74–89 % of retail CFD accounts lose money** (ESMA's mandatory warning) |

* **US ETFs (SPY/QQQ, the instruments the S1 paper used)**: EU retail investors generally can't buy US-domiciled
  ETFs because of PRIIPs rules. The US $25,000 pattern-day-trader minimum was abolished by the SEC in April 2026,
  but that only matters if you use a US broker.
* **Conclusion**: at €500 the only practical way to run S1 with sane sizing is an index CFD. Move to MES once the
  account is ≈ €8,000+, because exchange-traded futures remove the broker-counterparty conflict.

### 1.2 Base rates for people trading their own money
* **Brazil, all individuals who day-traded equity futures from 2013–2015** (Chague, De-Losso & Giovannetti):
  **97 % of those who persisted more than 300 days lost money. Only 1.1 % earned more than the minimum wage.**
* **Taiwan, the complete market 1992–2006** (Barber, Lee, Liu & Odean): day traders as a group lose money. 74 %
  of day-trading volume comes from traders with a history of losses. Fewer than 1 % are predictably profitable
  after costs.
* **EU CFDs**: 74–89 % of retail accounts lose money (ESMA standardised warning). Large UK brokers report 68–71 %.
* **The benchmark you must beat**: a world index ETF. MSCI World returned ≈ 8–9 % a year nominal since 1970
  (≈ 6.7 % real over 1919–2023 in a longer world series). We use **7 % a year, 15 % volatility**, which is
  conservative.

## 2. Results (Monte Carlo, 5,000 paths, pre-tax, assumed edges)

You put in: **€1,700 after 1 year · €4,100 after 3 · €6,500 after 5 · €12,500 after 10.**

**Median outcome** (half of outcomes are better, half worse):

| Scenario | 1 year | 3 years | 5 years | 10 years | P(end below money put in) at 10 y |
|---|---|---|---|---|---|
| Savings only (0 %) | 1,700 | 4,100 | 6,500 | 12,500 | 0 % |
| **Index ETF (7 %/yr)** | **1,761** | **4,541** | **7,650** | **17,231** | 13 % |
| Day trading with **no edge** (costs only), CFD 1 % | 1,605 | 3,492 | 5,041 | 7,807 | **91 %** |
| No edge, always ≥ 1 MES (over-leveraged) | 517 | 1,916 | 3,106 | 5,749 | 87 % |
| S1 planning edge, MES, 1 % risk | 1,700 | 4,088 | 6,465 | 15,594 | 25 % |
| **S1 planning edge, CFD, 1 % risk** | **1,786** | **4,733** | **8,254** | **20,607** | 12 % |
| S1 planning edge, CFD, 2 % risk | 1,851 | 5,212 | 9,610 | 28,672 | 17 % |
| S1 planning edge, US500 + US100 CFDs, 1 % | 1,857 | 5,293 | 9,806 | 30,364 | 6 % |
| S1 optimistic edge, CFD, 1 % risk | 1,958 | 6,234 | 13,158 | 57,235 | 0 % |
| S1 optimistic edge, CFD, 2 % risk | 2,241 | 9,264 | 26,349 | 270,987 ⚠ | 0 % |

Range for the main case (S1 planning, CFD, 1 %), 5th to 95th percentile: **€1,470–2,254 after 1 year;
€10,479–44,371 after 10 years.** The median worst drawdown along the way is 26 %.

### How to read the table
1. **With the edge we planned for, day trading only modestly beats an index ETF.** After 10 years the median is
   €20.6k against €17.2k. After an illustrative 30 % flat tax (trading gains are taxed every year; the ETF is
   taxed once, on exit) the gap nearly closes: **€17.6k vs €15.8k**. In a tax wrapper such as a French PEA, the
   ETF would likely win.
2. **With no edge, day trading turns €12,500 of savings into about €7,800** (91 % chance of ending below what you
   put in). The studies above say this is the most common real-world outcome.
3. **MES with proper sizing barely trades for ~5–6 years.** At 1 % risk it can't take a trade until the account
   reaches ≈ €8k. That makes the CFD necessary at the start.
4. **Over-leveraging (1 MES on €500) is a coin you can't afford to flip.** With the planning edge the median looks
   good (€23.8k), but the median path loses **97–99 % at some point**. Most people quit at that point, and the
   simulation assumes you don't. Without an edge you end with €5.7k.
5. **The optimistic rows need the published, in-sample edge to hold live, every year, for 10 years.** The
   €271k figure (2 % risk) also assumes you sit through a median 43 % drawdown. Treat those rows as the ceiling of
   what the maths allows, not as forecasts.
6. **The contribution matters more than the strategy.** At 10 years, raising the monthly amount from €100 to €300
   adds ≈ €38k to the median. The planning edge adds ≈ €3k over the ETF at €100/month.

### Probability-weighted view (my judgement, not a measurement)
Weights: no edge 50 %, planning edge 35 %, optimistic edge 15 %. On those weights, the expected 10-year value of
trading CFDs at 1 % risk is ≈ **€22k pre-tax / ≈ €16.6k after 30 % tax**. The ETF gives **≈ €18k / €16.4k**.
After tax it's a draw on expected value, but trading has a much wider spread of outcomes. It also needs either automation or you at the screen for the
whole US session (15:30–22:00 Paris time) every trading day, which is ≈ 1,600 hours a year by hand.

## 3. When does it become an income?
€100/day ≈ €25,000/yr. At ~15 %/yr (planning edge, 1 % risk) that needs ≈ **€165,000** of capital.

| Monthly contribution | Years to €165k at 7 % | at 15 % | at 30 % |
|---|---|---|---|
| €100 | 34 | 21 | 13 |
| €300 | 21 | 14 | 10 |
| €500 | 15.5 | 11 | 8 |

With €100/month, own-capital trading cannot become an income within 10 years in any realistic scenario. Its role
is to **prove the edge cheaply** and compound a small account.

## 4. Recommended plan for €500 + €100/month
1. **Months 0–6: core first, prove the edge.** Put the €500 and the monthly €100 into a world index ETF (in a
   tax-advantaged wrapper if your country has one). In parallel, validate S1 on real data (validation gate in
   SYSTEM_DESIGN §1) and paper-trade it on a CFD demo account for 60–100 trades.
2. **If, and only if, the gate passes and live paper results match: start a satellite trading account.** Move a
   fixed slice (e.g. €500–1,000) to a regulated EU CFD broker. Trade S1 at **1 % risk per trade**, daily stop 2R.
   Keep the ETF contributions going; add new money to the trading account only after 6 months of results inside
   the expected range.
3. **Kill switch**: if the trading account is down 25 % from its peak, or the rolling 60-trade expectancy's lower
   confidence bound turns negative, stop and go back to paper.
4. **Switch to MES at ≈ €8k** (1 contract ≈ 1.25 % risk) to leave broker-counterparty CFDs behind.
5. **Consider prop fees as a parallel use of the €100.** One Topstep 50K subscription is ≈ $49/month. Once the
   edge is proven, that buys more edge exposure than €100/month of own capital. The prop study shows a positive
   mean, but the median is still negative in year 1.

## Sources
* Margins: [NinjaTrader margins](https://ninjatrader.com/pricing/margins/?text=micro) · [NinjaTrader EU pricing](https://ninjatrader.com/eu/en-fr/pricing/) · [broker margin comparison 2026](https://damnpropfirms.com/trading-guides/futures-day-trading-margins-by-broker-ninjatrader-tradovate-amp-tradestation/) · [Optimus margins](https://optimusfutures.com/Platforms/Margin-Rates.php) · [StoneX day-trading margins](https://futures.stonex.com/day-trading-margins)
* IBKR futures commissions (Ireland): [interactivebrokers.ie](https://www.interactivebrokers.ie/en/pricing/commissions-futures.php?re=amer)
* PDT rule removal: [FINRA Notice 26-10](https://www.finra.org/rules-guidance/notices/26-10) · [Federal Register](https://www.federalregister.gov/documents/2026/04/17/2026-07485/self-regulatory-organizations-financial-industry-regulatory-authority-inc-notice-of-filing-of) · [Schwab summary](https://www.schwab.com/learn/story/sec-approves-scrapping-25000-day-trader-minimum)
* CFDs: [IG US 500 product page](https://www.ig.com/uk/indices/markets-indices/us-spx-500) · [IG margin rates](https://ig.com/uk/charges/margin) · [BrokerChooser IG S&P 500 spread](https://brokerchooser.com/ru/broker-reviews/ig-review/ig-sp-500-cfd-spread) · [CFD loss statistics](https://www.finder.com/uk/share-trading/share-trading-research/cfd-trading-statistics) · [ESMA complex-products data](https://www.financemagnates.com/forex/regulation/cfds-account-for-35-of-eu-retail-complex-product-trades-esma-finds/)
* Day-trader outcomes: [Chague, De-Losso, Giovannetti — Day Trading for a Living?](https://econpapers.repec.org/RePEc:spa:wpaper:2019wpecon47) · [COVID & day trading in Brazil](https://periodicos.fgv.br/rbfin/article/view/94291) · [Barber, Lee, Liu, Odean, Zhang — Learning, Fast or Slow](https://econpapers.repec.org/RePEc:oup:rasset:v:10:y:2020:i:1:p:61-93.) · [working paper](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/day%20trading%20and%20learning%20110217.pdf)
* Index returns: [MSCI World (Wikipedia)](https://en.wikipedia.com/wiki/MSCI_World) · [Deutsche Börse long-run MSCI World](https://live.deutsche-boerse.com/news/128949fb-98aa-4e8f-9487-fdb07aad5c36) · [Monevator world index](https://monevator.com/world-index/)
