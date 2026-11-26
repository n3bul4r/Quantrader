# Quantrader — system design

*Prop-firm futures trading system: strategy core, risk engine, dashboard, roadmap, and an honest assessment.*
Date: 2026-11-26. Research and sources: [RESEARCH.md](RESEARCH.md). All Monte Carlo numbers can be reproduced with
`engine/scripts/prop_economics.py` and `engine/scripts/portfolio_economics.py`
(full tables: [results/prop_economics.md](results/prop_economics.md), [results/portfolio_economics.md](results/portfolio_economics.md)).
Trading your own money instead of a prop account: [OWN_CAPITAL.md](OWN_CAPITAL.md).
Max-speed mandate (aggressive sizing, edge search, fleets, flywheel): [AGGRESSIVE_SYSTEM.md](AGGRESSIVE_SYSTEM.md).

---

## 0. Summary

1. **There is one intraday futures edge with strong evidence that a retail/prop trader can actually reach:**
   *market intraday momentum*, caused by option dealers' short-gamma hedging (JFE 2018, JFE 2021, 60+ futures,
   1974–2020). Its best documented implementation, the **noise-area breakout** (Zarattini–Aziz–Barbon 2024: SPY
   Sharpe 1.33 net, 2007–2024), is the core strategy **S1**. Everything else is either decayed (overnight drift),
   killed by costs on micros (scalping, ORB on indices, naive MNQ momentum), or unproven (footprint/order flow,
   VWAP fades).
2. **Plan on less than half of the published edge.** Published anomalies lose ~58 % of their returns after
   publication (McLean & Pontiff 2016). Planning case for S1: **+0.064 R per trade net, profit factor 1.10,
   37 % win rate, annual Sharpe ≈ 0.56.** Optimistic (paper-level) case: +0.147 R, PF 1.25, Sharpe ≈ 1.26.
3. **A prop account is a knock-out call option on your edge.** Your loss is capped at fees, so the EV-maximising
   risk per trade is much larger than "1 % rules" suggest: **≈ 20–25 % of the max-loss limit per trade** (e.g.
   $500 on a $2,000 trailing MLL), daily stop 2R, fixed dollar risk. Shrinking size as the buffer falls (the usual
   "defensive" advice) **turns a profitable plan into a losing one** in simulation (§2.4).
4. **Income reality (Monte Carlo, planning edge, S1 on MES + MNQ):** one Topstep 50K slot ≈ **€8/day mean,
   €2/day median in year 1**; ≈ €10–13/day mean in year 2. Hitting **€100/day needs about five 150K accounts
   copy-traded for two years**, and even then the *median* is ≈ €50/day and ~31 % of paths are net-negative after
   two years. **€20–50/day is a realistic year-2 target; €100–300/day requires the optimistic edge to be real.**
5. **What you get here:** a working quant engine (strategies, cost-aware backtester, walk-forward / deflated-
   Sharpe validation gate, risk-of-ruin maths, live risk guard, prop-rule tracker, lifecycle Monte Carlo) with
   39 passing tests, a FastAPI service and a Next.js dashboard. **No strategy here has been validated on real data
   yet** — that is step 1 of the roadmap, and it needs ~$150–300 of historical data.

---

## 1. Strategy core

Instruments: **MES** (primary) and **MNQ** (secondary). Both micros, 1-tick spreads, deepest micro liquidity,
fine enough granularity ($5/pt and $2/pt) to size $100–700 of risk accurately. Trade **RTH only (09:30–16:00 ET)**,
decisions on 30-minute marks, risk managed on 1-minute bars, **always flat by 15:59** (no overnight, no weekend
gap risk, no prop-firm overnight-margin issues). MGC/MCL: research only (wider effective costs, news shocks).

### S1 — Noise-Area Intraday Momentum (core, ~85 % of risk)

Code: `engine/qtengine/strategies/noise_area_momentum.py`

**Definitions** (day *t*, minute *m* after 09:30, 1-minute closes C):

```
O_t            RTH open,  C_{t-1} prior RTH close (16:00 settlement area)
σ_{t,m}      = (1/14) Σ_{i=1..14} | C_{t-i,m} / O_{t-i} − 1 |        noise width at minute m
U_{t,m}      = max(O_t, C_{t-1}) · (1 + σ_{t,m})                       upper boundary
L_{t,m}      = min(O_t, C_{t-1}) · (1 − σ_{t,m})                       lower boundary
VWAP_{t,m}   = Σ (typical price × volume) / Σ volume, from 09:30
Decision times D = {10:00, 10:30, …, 15:30}
```

**Entry** at a decision time m ∈ D (fill at that bar's close + slippage):
* Long if `C_{t,m} > U_{t,m}`; short if `C_{t,m} < L_{t,m}`; reversal allowed; max 3 entries/day.

**Initial stop**: long `S₀ = min( max(U_m, VWAP_m),  C_m − 0.5·σ_{t,m}·O_t )` (short symmetric). The floor
prevents near-zero risk when price has only just crossed the boundary.

**Trailing**: at each later decision time, trail = `max(U_m, VWAP_m)` (long). If the 30-min close is back below
the trail → exit at market; otherwise ratchet the resting stop to `max(stop, trail)`. The resting stop is live
on every bar (server-side bracket), so gaps/disconnects are covered.

**Exit**: stop, trail, or **market-on-close at 15:59**.

**Sizing** (§2): `contracts = min( ⌊R$ / (stop_pts·$/pt + cost)⌋ , ⌊VolTarget$ / (P·σ_daily·$/pt)⌋ )`.
The volatility cap (from the paper's vol-targeting) stops tight-stop entries from becoming outsized positions
whose winners break the consistency rule.

**Statistical edge**

| | Planning (58 % haircut) | Optimistic (≈ paper) |
|---|---|---|
| Win rate (net) | 37 % | 40 % |
| Average win / average loss | +1.85 R / −0.95 R (2 % of losses slip to −1.6 R) | same |
| Net expectancy per trade | **+0.064 R** | +0.147 R |
| Profit factor (net) | **1.10** | 1.25 |
| Trades/day (one instrument) | ≈ 0.8 | ≈ 0.8 |
| Annualised Sharpe | **0.56** | 1.26 |
| Costs as % of risk | 3.5 % (MES, 22-pt stop) | |

Shape: low win rate, positive skew. Most days are small losses or scratches; a few trend days make the year.
That is also what makes it *uncorrelated with market direction*: it is long-and-short symmetric, flat every
night, and earns on **large moves in either direction** (it behaves like being long intraday volatility — the
paper reports good results in 2008, 2020 and 2022).

**Why it should keep working**: the counterparties are *forced* hedgers (dealers short gamma, leveraged/inverse
ETF rebalancing into the close). Their flows are price-insensitive and have grown with options/0DTE volume. The
risk to the edge is regime: when dealers are **long** gamma the effect disappears (Baltussen et al.), and 0DTE
positioning can flip that sign — this is why a regime filter (realised-vol regime now; dealer-gamma estimates
later) is part of the research backlog, and why S3 exists.

**Prop compatibility**
* EOD-trailing drawdown accounts only (Topstep standard, Apex EOD). **Avoid intraday-trailing accounts**: S1
  gives back open profit to the VWAP trail by design, and an intraday trail ratchets on unrealised peaks.
* Positive skew vs consistency rules: a big trend day can exceed 50 % of total profit. Mitigation is a **daily
  profit cap at 45 % of the profit target** (auto in the guard); in simulation it adds ~$500 of mean net over two
  years versus no cap.
* Automation: allowed on Topstep Combine/XFA via the TopstepX (ProjectX) API; Apex reportedly disallows fully
  automated bots on PA, so use *confirm mode* there (the engine proposes the bracket, a human clicks).

### S2 — Late-Session Momentum (satellite, ≤ 15 % of risk, OFF until forward-tested)

Code: `engine/qtengine/strategies/late_day_momentum.py`

```
r_ROD = C_{t,15:30} / C_{t-1} − 1          z = r_ROD / stdev(r_ROD over last 60 sessions)
Enter at 15:30 in sign(r_ROD) iff |z| ≥ 0.75 AND 14-day RV > its 60-day median (short-gamma proxy)
Stop: entry ∓ 1.5 · stdev(15:30→16:00 move over 60 sessions)      Exit: 15:59 close
```

Evidence is strong (JFE 2018/2021) but the per-trade edge is a few basis points. On MES the haircut gross edge
on an unfiltered day (~0.8 bp ≈ $2.8/contract) is **below the $3.90 all-in cost**. Only the filtered high-vol
subset (~60–80 trades/yr) has a chance. Planning edge: **0 to +0.05 R**. It overlaps with S1 (S1 already holds
winners into the close), so it adds little diversification. Enable only if, after ≥ 100 forward trades, net
expectancy's 90 % lower confidence bound is > 0.

### S3 — Regime-gated VWAP reversion (research candidate, zero planning edge)

Code: `engine/qtengine/strategies/vwap_reversion.py`

Active **only when S1 is idle** (price inside the noise area) and only in the low realised-vol regime (proxy for
dealers long gamma, which dampens intraday moves). Fade `|C − VWAP| ≥ 2·sd_VWAP`, stop at 3·sd, target VWAP,
60-minute time stop, max 2/day. The design goal is a return stream that is *negatively correlated in regime*
with S1. Evidence is weak (no rigorous ES/NQ study survives costs), so **planning edge = 0** and it gets no
capital until it clears the validation gate.

### What was rejected, and why

| Idea | Verdict |
|---|---|
| Footprint / delta / absorption scalping | No OOS evidence; the predictive horizon of order-flow imbalance is seconds, owned by co-located HFT; scalping cost drag is 26–39 % of risk on micros. Used only as journal context. |
| Opening-range breakout on index futures | Gross edge replicates, net ≈ 0 after costs (2015–2026 replication). |
| Overnight drift (02:00–03:00 ET) | Weakened post-publication (NY Fed, July 2026); overnight is hostile to prop rules. |
| Naive OHLCV momentum / pattern systems on MNQ | Failed walk-forward + cost + cross-year tests in two 2026 falsification studies. |
| ML on bars | Same data as above, more parameters: higher multiple-testing risk, no structural mechanism. |

### Validation gate (no capital before this passes)

Code: `engine/qtengine/validation.py`. On ≥ 3 years of real 1-minute data (2021-11 → today minimum; ideally
2018+), per instrument:

1. Rolling walk-forward (250-day train, 63-day test, small grid: band multiplier {0.8, 1.0, 1.2}, stop floor
   {0.3, 0.5, 0.8}, max entries {1, 2, 3}; 27 configurations, all counted).
2. ≥ 200 out-of-sample trades; 95 % bootstrap CI of net expectancy **entirely > 0 R**.
3. Sign-flip permutation test p ≤ 0.05 (direction skill, costs included).
4. **Deflated Sharpe Ratio ≥ 0.95** using the number of configurations actually tried.
5. Positive net result in ≥ 3 of 4 calendar years; no single year > 50 % of total P&L.
6. Then re-run the prop Monte Carlo with `EmpiricalTradeModel.from_trades(oos_trades)` instead of the
   parametric model. If the empirical EV at the chosen risk is negative, stop.

---

## 2. Risk & money-management engine

Code: `engine/qtengine/risk/{sizing,ruin,guard}.py`, `engine/qtengine/prop/{account,simulator}.py`.

### 2.1 The unit of risk is the drawdown buffer

A "$50K" account with a $2,000 trailing max loss is economically a **$2,000 account with free leverage**.
`buffer = equity − MLL level`. All sizing, alerts and risk-of-ruin numbers are expressed against the buffer and
the max-loss limit, never against nominal size.

### 2.2 Position sizing

```
R$          = risk per trade in dollars (fixed, see 2.4)
contracts   = min( ⌊R$ / (stop_pts·point_value + cost_rt)⌋,                 risk cap
                   ⌊VolTarget$ / (price · σ_daily · point_value)⌋,           volatility cap (S1)
                   firm max contracts / scaling-plan limit,
                   ⌊0.8 · (DLL_remaining) / (stop_pts·point_value)⌋ )        never let one stop breach the DLL
one contract is allowed if it risks ≤ 1.25·R$, otherwise the trade is skipped
```

Off-prop (own capital), use **fractional Kelly**: `kelly_fraction_r()` solves max E[log(1+fR)] exactly. With a
per-trade edge of +0.064 R and σ ≈ 1.6 R, full Kelly is ~2.5 % of capital per trade; use ¼–½ Kelly.

### 2.3 Risk-of-ruin maths (all in the engine and the Risk page)

Treat cumulative P&L as Brownian motion with drift μ and volatility σ per day (or per trade):

* Static barriers: `P(+T before −D) = (e^{aD} − 1) / (e^{aD} − e^{−aT})`, `a = 2μ/σ²` (→ D/(D+T) when μ = 0).
* Static, no target: `P(ruin) = e^{−2μD/σ²}`.
* **Trailing drawdown D (Lehoczky 1977)**: the high-water-mark gain when the trail is first hit is exponential
  with mean `m = (σ²/2μ)(e^{2μD/σ²} − 1)`, so `P(HWM gains L before breach) = e^{−L/m}`. For Topstep-style MLLs
  that lock at the starting balance, `P(reach lock) = e^{−D/m}` — **36.8 % for a zero-edge trader**.
* Expected time to a drawdown of D (Taylor 1975): `σ²/(2μ²)·(e^{2μD/σ²} − 1 − 2μD/σ²)`.
* Model-free: Lundberg bound `P(ruin) ≤ e^{−λD}` with `E[e^{−λX}] = 1` on the empirical trade/day P&L, plus
  bootstrap Monte Carlo with trailing + lock semantics (the dashboard shows P(breach in 20/60 days) live).

Anchors for a 50K account ($3,000 target, $2,000 MLL):

| daily μ | daily σ | P(+3000 before −2000) static | P(reach MLL lock) trailing | E[days to a $2,000 DD] |
|---|---|---|---|---|
| $0 | $250 | 40 % | 37 % | 64 |
| $20 | $250 | 75 % | 61 % | 103 |
| $50 | $400 | 75 % | 61 % | 40 |

A daily Sharpe of 0.08 (annual 1.27 — *paper-level*) still fails about a quarter of evaluations. Failure is
normal; the plan budgets for it.

### 2.4 How big? The option regime (Monte Carlo)

Topstep 50K, S1 on MES + MNQ (planning edge), 2-year horizon, 4,000 paths:

| Sizing policy | Net mean | Net median | 5th pct | P(net > 0) |
|---|---|---|---|---|
| **Fixed $500/trade (25 % of MLL), daily stop 2R** | **+$5,599** | **+$3,205** | −$2,525 | **73 %** |
| Fixed $500, daily stop 3R | +$5,841 | +$3,475 | −$2,558 | 75 % |
| Fixed $500, daily stop 1R | +$3,849 | +$1,665 | −$2,253 | 65 % |
| Fixed $500, no daily profit cap | +$5,071 | +$2,702 | −$2,499 | 71 % |
| Buffer-scaled 25 % of buffer, halve below 50 % | +$105 | −$1,109 | −$1,372 | 25 % |
| Buffer-scaled 20 % of buffer | −$172 | −$1,118 | −$1,323 | 22 % |

Risk-per-trade sweep (1 year, one instrument, Topstep 50K): mean net rises from −$576 at $100 to ≈ +$1,000 at
$500 and peaks around $700 (35 % of MLL), then falls; zero-edge traders lose money at every size.

Rules that follow:
1. **Fixed dollar risk of 20–25 % of the max-loss limit per trade** ($400–500 on 50K, $900–1,125 on 150K),
   daily stop 2R, stop after 3 consecutive losses. Never above 35 %.
2. **Do not shrink size as the buffer shrinks.** With fees and a minimum winning-day threshold for payouts
   ($150–250/day), small size stalls both passing and payouts; you pay subscription fees while you wait. The
   cheap "ruin" (losing a $49 evaluation) is better than the slow one.
3. **Daily profit cap at 45 % of the profit target** while a consistency rule applies (evaluation; Apex payouts).
4. **EOD-trailing accounts only** for S1.
5. Each evaluation is a disposable option: budget for 5–13 resets a year (§5).

### 2.5 Drawdown control for trailing MLLs

* The guard (`risk/guard.py`) runs before every order and every minute in a position:
  internal daily stop (2R) < firm DLL; block at 80 % of the firm DLL, flatten at 90 %; consecutive-loss stop;
  10-minute cool-down after a loss (anti-revenge); 09:30–09:35 and 15:58+ blackouts; scheduled-event blackout
  (FOMC 14:00, CPI is pre-RTH); minimum buffer to open a trade; profit lock once the soft target is hit (stop if
  40 % of the day's peak is given back).
* All orders are **brackets with the stop held server-side**; the engine only modifies the stop. A
  disconnect never leaves a naked position.
* EOD trailing nuance: intraday open profit does not ratchet the MLL, but a *closing balance* high does. Ending
  the day at a large unrealised-then-realised high moves the floor up permanently — the profit cap also limits
  how fast the floor climbs before it locks.
* After the MLL locks (Topstep: at the starting balance; Apex: start + $100), the account becomes static-
  drawdown and risk per trade can stay the same in dollars.

### 2.6 Scaling rules

`ScalingPolicy` (engine): tiers of risk per trade by buffer, e.g. 50K funded: $100 → $150 (buffer ≥ $2.5k) →
$200 (≥ $3.5k) → $300 (≥ $5k) → $450 (≥ $8k). Step **up** only when *all* hold: buffer ≥ next tier; the lower
90 % confidence bound of the rolling 60-trade expectancy is > 0; live expectancy is not more than 2 standard
errors below the backtest (drift check). Step **down** immediately when the buffer falls 15 % below the current
tier threshold. Scale accounts, not risk: once one account clears its first two payouts with the live edge
intact, add a second copy-traded account, up to the firm maximum (Topstep 5, Apex 20). **Copy-traded accounts
are perfectly correlated** — they pass and fail together; diversification needs different instruments/strategies,
not more copies.

---

## 3. Dashboard / application architecture

### 3.1 Stack and why

| Layer | Choice | Why |
|---|---|---|
| Quant engine | **Python 3.11+** (numpy, pandas, scipy) | The whole quant ecosystem; vectorised Monte Carlo (10k paths × 252 days in ~1 s). Add numba/polars only if profiling demands it. |
| API | **FastAPI** + WebSocket | Typed, async, auto OpenAPI docs; same process imports the engine directly. |
| UI | **Next.js 15 + React 19 + Tailwind + Recharts** (dark-first) | Real multi-page app with proper state, charts and responsive layout; a Streamlit prototype would be faster to write but is weak for real-time panels, auth and polish. |
| Storage | SQLite (scaffold) → **PostgreSQL + TimescaleDB** | Trades/journal relational; bars as hypertables. |
| Real-time bus | Redis pub/sub (prod) | Execution adapter publishes fills/positions; API relays to the browser over WebSocket. |
| Market data | **Databento** (GLBX.MDP3, 1-minute OHLCV for research; live via broker feed) | Clean CME history at low cost; continuous contracts with volume roll. |
| Execution | `BrokerAdapter` interface: **TopstepX/ProjectX**, Tradovate, Rithmic; PaperBroker for forward tests | One code path for paper and live; bracket-only orders. |
| Deployment | Docker compose: `engine` (uvicorn), `web` (next start), `postgres`, `redis`; a small VPS for the dashboard | Check the firm's ToS about where orders may be sent from — one source reports Topstep restricts VPS/VPN order routing; run the execution bot locally if so. |

### 3.2 Components

```
                 ┌──────────────── Next.js dashboard (web/) ────────────────┐
                 │ Overview · Risk · Analytics · Journal · Backtest · Prop  │
                 └───────────────▲──────────────────────────▲──────────────┘
                          REST /api/*                  WS /ws/live
                 ┌───────────────┴──────────────────────────┴──────────────┐
                 │                FastAPI  (engine/qtengine/api)            │
                 └──┬─────────┬──────────┬──────────┬───────────┬──────────┘
          strategies│ backtest│ validation│ risk.guard│ prop.sim  │ journal
                    │         │           │ risk.ruin │ prop.acct │ tagging
                 ┌──┴─────────┴───────────┴───────────┴───────────┴──────┐
                 │  store (SQLite → Postgres/Timescale)   Redis (live)    │
                 └──────────────▲────────────────────────────▲───────────┘
                    historical bars (Databento)     execution bot (BrokerAdapter)
                                                    TopstepX / Tradovate / Rithmic / Paper
```

### 3.3 Feature map (implemented in this repo unless marked)

| Requirement | Where |
|---|---|
| Real-time tracking | Overview: last-session P&L vs daily target, live WebSocket panel (demo feed now; broker adapter = roadmap) |
| Strategy analytics | Analytics: equity, drawdown, Sharpe/PSR, expectancy (R and $), PF, by session / strategy / tag, rolling 30-trade expectancy |
| Risk dashboard | Overview + Risk: buffer to MLL, MLL lock state, DLL usage, consistency-safe max profit today, P(breach in 20/60 days), Lundberg bound, guard decision; analytic ruin calculator |
| Trade journal with auto-tagging | Journal: session, side, strategy, exit, hold time, outcome, **violation:oversized / after_daily_stop / overtrading**, **behaviour:possible_revenge**, **news:FOMC…**, regime/day type |
| Backtesting + forward tracker | Backtest: synthetic or uploaded real 1-min data, S1–S3, sized $ with costs, by-hour/exit breakdowns, R histogram; forward-vs-backtest drift z-score |
| Prop simulator / rule checker | Prop: full lifecycle Monte Carlo (pass rate, payouts, fees, net, fan chart, risk sweep), pre-computed income table; rule checker = `PropAccountTracker` replaying the journal (Overview) |
| Alerts & daily targets | Guard alerts (critical/warning/info) on Overview + live panel; push/SMS/Telegram delivery = roadmap |

API endpoints: `GET /api/health · /api/presets · /api/models · /api/economics · /api/journal/trades ·
/api/journal/analytics · /api/account/status · /api/account/config`, `POST /api/prop/simulate · /api/prop/sweep ·
/api/risk/ruin · /api/risk/guard · /api/backtest/synthetic · /api/backtest/upload · /api/journal/trades ·
/api/demo/seed`, `WS /ws/live`. Interactive docs at `http://localhost:8000/docs`.

### 3.4 Data model (core tables)

`trades(id, account, source[manual|paper|live|demo-synthetic], date, entry_time, exit_time, symbol, strategy,
side, contracts, entry, exit, stop, risk_dollars, pnl, r_net, exit_reason, mae_r, mfe_r, notes, tags)`;
`config(key, value)` (account program/phase/start date/guard settings). Production adds `bars_1m` (hypertable),
`orders`, `fills`, `positions`, `daily_account_snapshots` (balance, MLL, buffer at EOD — the firm's own numbers,
reconciled daily against the tracker).

---

## 4. Implementation roadmap

Each phase has an exit gate and a kill criterion. Calendar times assume ~10 h/week.

| # | Phase | Work | Exit gate | Kill criterion | Time | Cost |
|---|---|---|---|---|---|---|
| 0 | **Done (this repo)** | Engine, tests, API, dashboard, Monte Carlo economics | — | — | — | — |
| 1 | **Real data + validation** | Buy MES/MNQ/ES/NQ 1-min history 2018→now (Databento ~$100–300); run S1 walk-forward per §1 gate; replace parametric model with `EmpiricalTradeModel`; re-run economics | All gate items pass on MES *or* MNQ; empirical EV at chosen risk > 0 | Gate fails on both → stop or research S3/regime filters. **Do not tweak until it passes** (that is curve fitting; the DSR counts your trials) | 3–5 weeks | $100–300 |
| 2 | **Paper / forward test** | Implement the broker adapter (TopstepX API, $29/mo reported) in paper mode + PaperBroker; run S1 live-paper 60–100 trades (~3–5 months); journal everything | Live expectancy within 2 SE of backtest; slippage ≤ 1.5 ticks avg; zero guard violations | Drift z < −2, or slippage > 2 ticks | 3–5 months | ~$30–60/mo |
| 3 | **First evaluation** | One Topstep 50K Combine (EOD trailing), $400–500/trade, daily stop 2R, auto profit cap; reset on fail (budget 6 resets) | Pass + first two XFA payouts | 6 failed evaluations with live expectancy < 0 | 1–6 months | $300–600 |
| 4 | **Funded operations** | XFA: same rules; track payout cadence vs simulator; reconcile firm statements daily | Two payout cycles with live edge intact | Live 60-trade LCB90 < 0 → back to paper | 2–4 months | activation fees |
| 5 | **Scale accounts** | Add copies up to 5 (Topstep) — or 150K accounts; add MNQ as a second instrument; consider Apex EOD accounts in confirm mode | Each new account follows phase 3–4 gates | Correlated blow-up of ≥ 3 accounts in a month → cut to 1 | 6–12 months | $5–12.5k/yr fees at 5 slots |
| 6 | **Research backlog** | Dealer-gamma regime filter (SpotGamma-type data or own estimate from CBOE OI), S3 validation, S2 forward test, MGC as uncorrelated sleeve | Each through the same gate | — | ongoing | — |

---

## 5. Honesty section

### 5.1 Realistic expectancy after costs and psychology

* Published S1 numbers: Sharpe 1.33 net (SPY, 2007–2024). **Planning number: Sharpe ≈ 0.56, +0.064 R/trade,
  PF ≈ 1.10.** That is a thin edge: 37 % winners, and the chance of a run of **10+ consecutive losers** somewhere in
  a 200-trade year is ≈ 52 % (simulated).
* Execution and psychology usually cost more than commissions: skipping the trade after three losses, moving
  stops, taking profits early on the trend day that pays for the month. S1's payoff is concentrated in a few
  trend days — **skip 2–3 of the best days a year and the edge is gone.** This is the strongest argument for
  automation (allowed on Topstep via API).
* Industry base rates: ~17 % of evaluations pass; ~33 % of Topstep funded traders ever get a payout; estimates
  of ~1–7 % of evaluation buyers ever being paid. Your plan should beat these only because it is systematic,
  cost-aware and sized for the option regime, and even so, the simulations say **failing several evaluations a
  year is the expected path**, not a sign that something is broken (fixed-$500 sizing buys ≈ 9–13 evaluations/year).

### 5.2 Probability of €100+/day consistently

Monte Carlo (S1 on MES + MNQ treated as 1.4 independent trades/day — optimistic, since MES/MNQ correlate
~0.8–0.9; Topstep rules as configured; EURUSD 1.16):

| Setup | Horizon | €/day mean | €/day median | P(net > 0) |
|---|---|---|---|---|
| 1 × Topstep 50K, planning edge, $500/trade | year 1 | 7.9 | 1.8 | 59 % |
| 1 × Topstep 50K, planning edge, $500/trade | 2 years | 9.6 | 5.5 | 73 % |
| 1 × Topstep 150K, planning edge, $1,125/trade | 2 years | 19.7 | 10.0 | 69 % |
| **5 × Topstep 150K copy-traded, planning edge** | 2 years | **98** | **50** | 69 % |
| 5 × Topstep 150K copy-traded, optimistic edge | 2 years | 285 | 217 | 91 % |

My judgement:
* **€20–50/day by year 2**: achievable *if* S1's edge validates on real data (I'd put that at roughly 40–55 %).
* **€100+/day sustained**: needs ≈ 5 × 150K accounts, two years, and an edge closer to the paper than to the
  haircut. Overall probability from today: **roughly 10–20 %**; within the first 6 months: **< 5 %**.
* **€300/day**: only in the optimistic-edge world with the maximum number of large accounts — treat it as an
  upside scenario, not a plan.

### 5.3 Main ways this fails

1. **The edge isn't there on futures after costs** — the 2026 MNQ falsification studies are a warning; gate 1
   exists to find out cheaply.
2. **Regime change**: dealer gamma flips positive for long periods (heavy 0DTE call/put selling, vol
   suppression) → momentum disappears for months. Mitigation: regime filter research, S3 diversification, kill
   criteria.
3. **Rule changes**: firms changed consistency (Apex 30 → 50 %), payout caps (Topstep Apr-2026) and platforms
   (ProjectX) within this year. The edge over the firm can disappear overnight; every preset is editable data.
4. **Behaviour**: overriding the system after losses; oversizing after wins. The journal tags these
   automatically; the guard blocks the mechanical versions.
5. **Copy-trading correlation**: five accounts fail on the same bad week. Expect clustered resets.
6. **Operational**: disconnects, wrong contract month at roll, platform outages near the close (S1 exits at
   15:59). Bracket orders and a 15:58 blackout cover most of it.
7. **Model risk in this repo**: the simulator does not model Topstep's move to a Live Funded account,
   discretionary account reviews, payout processing delays, or taxes. Rule presets come from secondary sources.

### 5.4 Capital actually required

* **Prop route** (recommended): no trading capital at risk, but **risk capital for fees**: ≈ $1,000/yr per 50K
  slot at the EV-optimal size, ≈ $2,500/yr per 150K slot (≈ 9–10 resets + activations, simulated). For the
  €100/day plan (5 × 150K) budget **≈ €10–11k per year of fees you may lose entirely**, plus data ($100–300 once),
  API (~$30/mo), and 6+ months of living costs: the median first payout comes after ≈ 100–120 trading days.
* **Own-capital route** for comparison: €100/day ≈ €25k/yr. At the planning Sharpe of 0.56 and a sane half-Kelly
  volatility of ~25–30 %, expected return is ~14–17 %/yr → **≈ €150–180k of capital**, with ~−30 % drawdowns.
  With the optimistic Sharpe (1.26) at 20 % vol: ≈ €100k. This is why the prop route — an option written by the
  firm — is economically rational for a small trader *if* the edge is real.
* **€20–50/day** (≈ €5–12k/yr): one to three 150K slots in year 2 under the planning edge; fee budget
  ≈ €2–7k/yr.

---

## Appendix — reproduce everything

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e "engine[dev]"
cd engine && pytest -q                                   # 39 tests
python scripts/prop_economics.py --paths 6000            # docs/results/prop_economics.md (~5 min)
python scripts/portfolio_economics.py                    # docs/results/portfolio_economics.md
uvicorn qtengine.api.main:app --port 8000                # API + /docs
cd ../web && npm install && npm run build && npm start   # dashboard on :3000 (proxies /api to :8000)
```
