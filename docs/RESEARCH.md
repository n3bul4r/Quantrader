# Research phase — findings (compiled 2026-11-26)

Scope: which futures day-trading edges have *published, out-of-sample* support; what they cost on micros; how
the 2026 prop-firm rulebooks change the economics. Every claim below is tagged with its evidence quality.
Secondary sources (blogs, affiliate review sites) were used only for prop-firm rules, and they disagree with
each other — treat all rule numbers as "verify before use".

Evidence grades: **A** peer-reviewed / top journal · **B** working paper or central-bank research ·
**C** independent replication / preprint · **D** practitioner or vendor content (no verifiable OOS test).

---

## 1. Which intraday edges actually have evidence?

### 1.1 Market intraday momentum — the strongest evidence base (A)
* **Gao, Han, Li & Zhou (2018), *Journal of Financial Economics* 129(2)**: on SPY 1993–2013, the first
  half-hour return (from the prior close) predicts the last half-hour return; out-of-sample predictive R² ≈ 1.2 %.
  Small R² but economically meaningful for a 30-minute trade.
* **Baltussen, Da, Lammers & Martens (2021), *JFE* 142(1)**: the same "rest-of-day predicts last 30 minutes"
  pattern in **60+ futures** (equity, bond, commodity, FX) 1974–2020. Mechanism: **short-gamma hedging** by option
  dealers and leveraged-ETF rebalancing — hedgers must trade *with* the move. Momentum is present when dealer
  gamma is negative and grows as it gets more negative; **absent when gamma is positive**.
* Extensions: Chinese commodity futures (Jin et al. 2019), crude oil around EIA releases.
* **Why it should persist**: it is driven by *forced, price-insensitive* hedging flows (structural), not by an
  informational inefficiency that arbitrage removes. The flows have grown with options volume.

### 1.2 Noise-area breakout (practical implementation of 1.1) (B)
* **Zarattini, Aziz & Barbon (2024), "Beat the Market: An Effective Intraday Momentum Strategy for SPY"**
  (Swiss Finance Institute RP 24-97; 4th place Quantpedia Awards 2025). Noise area = mean absolute move from the
  open at each minute over the last 14 days; trade breakouts at 30-minute decision points, VWAP/boundary trailing
  stop, flat at the close. **2007–early 2024: 19.6 % annualised, Sharpe 1.33, net of costs**, ~−25 % max DD,
  with volatility-targeted sizing (up to 4× leverage).
* Independent community replications: initially weaker, later "much closer to the paper" after bug fixes (C/D).
* **This is the basis of strategy S1.**

### 1.3 Opening-range breakout (B → C, mixed)
* Zarattini & Aziz (2023) 5-minute ORB on QQQ; Zarattini, Barbon & Aziz (2024) ORB on "stocks in play" (7,000+
  US stocks) — profitable after costs **for stocks with news-driven relative volume**.
* An independent replication on index CFDs (NQ, SPX, DAX, FTSE, Dow, 2015–2026) reproduced the **gross** edge but
  found **net ≈ 0 after costs** (C). → ORB on index futures is *not* recommended as a standalone edge.

### 1.4 Systematic falsification on MNQ (C — important negative result)
* **arXiv 2605.04004 (2026)**, "Structural Limits of OHLCV-Based Intraday Momentum Signals in MNQ Futures: a
  Systematic Falsification Study" — fixed 2-point round-trip cost, null result.
* **arXiv 2605.11423 (2026)**, volatility-volume-gap regime classifier on 947 MNQ RTH days (2021–2025):
  **all eight directional strategies failed** walk-forward OOS + positive-net-of-cost + cross-year
  consistency. The classifier itself was useful only as a context filter.
* Take-away: naive OHLCV pattern strategies on MNQ, especially with short holding periods, do not survive costs.
  The noise-area strategy differs (multi-hour holds, structural mechanism) but this is the prior we must beat.

### 1.5 Overnight drift / FOMC drift (B, decaying)
* Boyarchenko, Larsen & Whelan (NY Fed): large positive ES return 02:00–03:00 ET, tied to dealer inventory after
  closing imbalances. **NY Fed Liberty Street (July 2026): the drift has weakened post-publication.**
* Lucca & Moench pre-FOMC drift: strong historically; recent evidence less clear. → Not used (decayed, and the
  overnight window is hostile to prop-firm rules and human sleep).

### 1.6 Order flow / footprint / absorption (A for microstructure, D for retail footprint trading)
* Order-flow imbalance (Cont et al.) has **short-horizon** (seconds to minutes) predictive power that decays
  fast and is regime-dependent (A/C, e.g. CSI-300 futures 2025 preprint).
* **No peer-reviewed or out-of-sample study** supports retail footprint/delta/absorption patterns as a tradable
  edge (D only). Horizons where OFI works are dominated by co-located HFT; a retail trader on a prop platform
  (100–300 ms round trip, market-order fills) is on the wrong side of that latency race.
* → Order flow is used **only as an optional execution filter / journal context**, never as the edge.

### 1.7 VWAP / σ-band mean reversion (D, weak)
* No rigorous ES/NQ study after costs. A QuantConnect reproduction of a VWAP strategy decayed toward Sharpe ≈ 0.7
  OOS and disappeared under retail costs (C/D).
* Mechanistic argument in its favour: when dealers are **long** gamma, their hedging dampens moves (Adams et al.
  find S&P volatility ~60 bp lower on days with 0DTE activity, effect lasting ~1 h). → Kept only as **S3, a
  research candidate with zero planning edge**, gated to low-vol regimes and only when S1 is idle.

### 1.8 Post-publication decay (A)
* **McLean & Pontiff (2016, *Journal of Finance*)**: anomaly returns are ~26 % lower out-of-sample and ~58 %
  lower post-publication. We apply the 58 % haircut to every published number → the "planning" models.

---

## 2. Costs on micro contracts (Nov 2026)

| item | figure | source quality |
|---|---|---|
| Tradovate micro commission | $0.39/side (free plan), $0.29 (monthly), $0.09 (lifetime) + exchange/NFA/clearing | broker page / review |
| All-in MES/MNQ round turn, prop-firm bundles | ~$1.34–1.42 (Topstep, Feb-2025 schedule), $1.82 (Tradeify), $1.90 (Top One) | firm help centres |
| CME non-member MES exchange fee | ~$0.30/side + ~$0.02 NFA | NexusFi table |
| Slippage assumption used | 1 tick per side for market/stop orders (MES $1.25, MNQ $0.50) | conservative planning |
| **Planning all-in** | **MES $3.90 / MNQ $2.40 per round turn** | |

**The cost geometry decides viability** (docs/results/prop_economics.md):

| setup | cost as % of risk | net break-even win rate |
|---|---|---|
| MES 8-tick scalp (2 pt stop / 2 pt target) | 39 % | 69.5 % |
| MES 3:4 pt scalp | 26 % | 54 % |
| MES S1 typical (22 pt stop) | 3.5 % | 36.7 % |
| MNQ S1 typical (60 pt stop) | 2.0 % | 36.0 % |

Scalping micros is a cost-drag machine: a strategy with *the same gross edge per R* as S1 but $50 stops and 3
trades/day ends up at +0.008 R net (vs +0.064 R) — costs eat ~90 % of it.

---

## 3. Prop-firm rules (2026) and their economic meaning

| | Topstep 50K Combine → XFA | Apex 4.0 50K EOD → PA |
|---|---|---|
| Profit target | $3,000 | $3,000 |
| Max loss | $2,000, **end-of-day trailing**, stops at start balance | $2,000 EOD trailing, stops at start + $100 |
| Daily loss limit | reported optional on standard Combine | $1,000 (pauses the day) |
| Consistency | best day ≤ 50 % of total profit to pass | 50 % (raised from 30 % on 1 Mar 2026) on payouts |
| Payout | 5 winning days ≥ $150 (one source: $200), up to 50 % of balance, per-cycle cap reported $2,000 (Apr 2026), 90/10 split | 5 qualifying days (≥ $250 reported), $1,500 cap on early payouts, 100 % of first $25k then 90/10 |
| Fees | ~$49/month subscription + activation | one-time evaluation fee (heavily discounted) + activation |
| Automation | API bots allowed on Combine/XFA via TopstepX/ProjectX; not on Live; no HFT | fully automated bots reportedly not allowed on PA |
| Max accounts | 5 XFA | 20 PA |

Industry outcome data: Topstep 2025 Combine completion 16.8 % per Combine started / 51.8 % per person; ~33 % of
Topstep funded traders received a payout; Tradeify 17.2 % per evaluation (Aug-2025–Jul-2026); estimates of
~1–7 % of all evaluation buyers ever being paid.

**Economic meaning**: the account is a *knock-out call option on your edge*. Downside = fees. The firm sets the
strike (target), the knock-out (trailing MLL) and caps the payoff (payout caps, consistency). With zero edge the
option is worth less than its premium; with a small edge it is worth more — but only if you size for the option
regime (see SYSTEM_DESIGN §2).

---

## Sources

Academic / institutional
* Gao, Han, Li, Zhou — Market intraday momentum, JFE 2018: https://econpapers.repec.org/RePEc:eee:jfinec:v:129:y:2018:i:2:p:394-414 · working paper https://www3.nd.edu/~zda/intramom.pdf
* Baltussen, Da, Lammers, Martens — Hedging demand and market intraday momentum, JFE 2021: https://econpapers.repec.org/RePEc:eee:jfinec:v:142:y:2021:i:1:p:377-403 · https://pure.eur.nl/en/publications/hedging-demand-and-market-intraday-momentum/
* Zarattini, Aziz, Barbon — Beat the Market (SPY intraday momentum): https://www.sfi.ch/de/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy · https://ideas.repec.org/p/chf/rpseri/rp2497.html · Quantpedia award: https://fsi.unisg.ch/de/newsdetail/news/quantpedia-awards-2025-fsis-barbon-and-team-secure-4th-place-with-intraday-momentum-strategy/
* Zarattini, Aziz — Can Day Trading Really Be Profitable?: https://papers.ssrn.com/abstract=4416622 · stocks-in-play follow-up: https://abarbon.com/papers/a-profitable-day-trading-strategy-for-the-u-s-equity-market
* ORB replication on indices (gross reproduced, net zero): https://www.mql5.com/en/blogs/post/776235
* MNQ falsification studies: https://arxiv.org/abs/2605.04004 · https://arxiv.org/abs/2605.11423
* Overnight drift (NY Fed): https://libertystreeteconomics.newyorkfed.org/tag/overnight-drift · https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf
* 0DTE / dealer gamma: https://quantpedia.com/do-sp500-0dtes-options-increase-market-volatility/ · https://www.cboe.com/insights/posts/volatility-insights-evaluating-the-market-impact-of-spx-0-dte-options
* Order-flow imbalance (CSI-300 futures): https://ar5iv.labs.arxiv.org/html/2505.17388
* McLean & Pontiff (2016), "Does Academic Research Destroy Stock Return Predictability?", Journal of Finance 71(1).
* Bailey & López de Prado — Probabilistic / Deflated Sharpe Ratio (2012, 2014).
* Lehoczky (1977), "Formulas for stopped diffusion processes with stopping times based on the maximum"; Taylor (1975) — drawdown hitting times.

Prop-firm rules, pass rates, costs (secondary unless marked)
* Topstep help centre (official): payout policy https://help.topstep.com/en/articles/8284233 · fees https://intercom.help/topstep-llc/en/articles/8284213 · API https://help.topstep.com/en/articles/11187768 · Labs https://intercom.help/topstep-llc/en/articles/15520357-topstep-labs
* Topstep rule summaries: https://www.futureshive.com/blog/topstep-rules-explained · https://blog.traderspost.io/article/how-to-get-funded-with-topstep · https://fortraders.com/blog/topstep-new-payout-rules · https://phidiaspropfirm.com/education/topstep-payout-rules
* Apex 4.0: https://dev.to/acesley_chan_5b46dfd6bd24/apex-just-doubled-its-consistency-rule-from-30-to-50-heres-who-gets-richer-and-who-gets-culled-4n5i · https://phidiaspropfirm.com/education/apex-trader-funding-4-0-explained · https://damnpropfirms.com/prop-firms/apex-trader-funding-profit-target-and-payout-ladder-rules-2026/ · https://tradetanto.com/learn/apex-trader-funding-rules-what-you-need-to-know
* Automation rules: https://www.jptradingcapital.com/blog/en/does-topstep-allow-bot-trading · https://blog.pickmytrade.io/topstepx-automation-2026/ · https://fortraders.com/blog/project-x-trading
* Pass-rate statistics: https://track360.io/blog/prop-trading-industry-statistics-2026 · https://www.rswebsols.com/?p=142805 · https://quantvps.com/blog/prop-firm-statistics · https://thepropfirmguide.com/prop-firm-statistics/
* Costs: https://tradovate.com/pricing · https://www.quantvps.com/blog/tradovate-review · https://intercom.help/tradeify/en/articles/10468315-trading-commission-fees · https://nexusfi.com/a/brokers/futures-commissions-and-fees
