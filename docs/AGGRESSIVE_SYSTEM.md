# Aggressive Topstep system — maximum speed of growth

*2026-11-26. Supersedes the "sustainable" sizing advice in SYSTEM_DESIGN.md for the max-speed mandate; the
evidence base and validation rules still apply. Reproduce: `engine/scripts/edge_search.py`,
`engine/scripts/aggressive_topstep.py`. Full tables: [results/aggressive_topstep.md](results/aggressive_topstep.md),
[results/edge_search_noise.md](results/edge_search_noise.md), [results/edge_search_edge.md](results/edge_search_edge.md).*

## 0. The answer on one screen

* **Speed comes from four multipliers, in this order:**
  1. **Breadth.** Run the edge on several uncorrelated markets (ES/NQ, CL, GC micros) to get ~2.4 independent bets
     a day instead of 0.8. Sharpe roughly doubles, and compounding speed scales with Sharpe².
  2. **Option-sized risk.** Risk 25–50 % of the max-loss limit per trade, in evaluations *and* funded accounts.
  3. **Slots.** Run 3–5 accounts at once, assigning each a different market or strategy mix (ρ ≈ 0.4), not copies.
  4. **Flywheel.** Send every payout into a personal futures account with no payout cap, compounded at ≤ Kelly.
* **Things that do not add speed** (each one measured): high win rates from profit targets, scalping micros,
  shrinking size in funded accounts, the 40 % Consistency payout path (for this strategy type), and copy-trading
  identical accounts.
* **Realistic speed, simulated with the edge I'd actually plan for ("planning"):** 5 × 150K slots, diversified:
  * Cumulative net cash (after all fees): median **$33k after 1 year**, **$231k after 3 years**.
  * 80 % chance of reaching $100k within 3 years; median time to $100k is 18 months.
  * With the payout flywheel: median wealth **$300–350k after 3 years**, and a **6–18 % chance of $1M**.
* **Seven figures in ≤ 3 years needs the optimistic edge:** a basket Sharpe of about 2.2, i.e. the published edge
  holding on every market. In that world the 3-year median is $0.8M from payouts alone, or $2–8M with the
  flywheel. I give that world **under 10 %** probability.
* **Overall odds from today** (my judgement, combining the real-data edge validation with the simulations):
  * ≈ **20 %** to reach $100k cumulative net within 2 years;
  * ≈ **5–10 %** to reach $1M within 3 years;
  * ≈ **50–60 %** to lose the fee budget ($5–25k a year at aggressive sizing) because the edge doesn't survive
    real data and live execution.

---

## 1. Re-evaluating edges for speed

### 1.1 What "fast" means mathematically
With Kelly-optimal leverage, wealth grows at g = c(2 − c)/2 · Sharpe² per year (c = fraction of Kelly).

| annual Sharpe | ×10 at full Kelly | ×100 | ×1000 |
|---|---|---|---|
| 0.5 | 18 y | 37 y | 55 y |
| 1.0 | 4.6 y | 9.2 y | 13.8 y |
| 2.0 | 1.2 y | 2.3 y | 3.5 y |
| 3.0 | 0.5 y | 1.0 y | 1.5 y |

**Doubling Sharpe makes growth four times as fast. No amount of leverage substitutes for it.** Leverage beyond
Kelly *reduces* growth. Inside a prop account the leverage is free (an option), but the firm caps how much of it
you can withdraw. So every edge is judged by **Sharpe after costs, multiplied by how many independent bets it gives
per day**.

### 1.2 Edge-by-edge verdict

| Candidate | Evidence | Speed potential | Verdict |
|---|---|---|---|
| **Intraday momentum, noise-area breakout** (S1 / NAM) | A (JFE 2018/2021; 60+ futures; SPY Sharpe 1.33 net) | High once spread across markets | **CORE — scale across MES, MNQ, MCL, MGC** |
| **Opening-range breakout, 60-min range, wide stop, run to close** | B/C (equities strong; index CFDs net ≈ 0) | Medium; complements NAM | **TEST on real data** (it was a top family in the calibration search) |
| **Late-session momentum** (last 30 min) | A | Low per trade, but adds bets across asset classes | **SATELLITE**, only on high-vol days |
| **CL around EIA (Wed 10:30 ET)** | C (crude intraday-predictability study) | Medium, 1 event per week | **RESEARCH** |
| High-win-rate VWAP fades / profit-target variants | D | Negative: targets cut off the right tail that carries momentum edges | **DISCARD** unless real data proves otherwise |
| Micro scalping, footprint/order flow | D; costs 26–39 % of risk | Negative after costs | **DISCARD** |
| Martingale, grid, averaging down | none | Fast blow-up against a trailing max loss | **DISCARD** |
| Overnight drift | B, decayed | Low; overnight is hostile to prop rules | **DISCARD** |

**The search itself confirms the high-win-rate verdict.** In both calibration runs, configurations with ≥ 60 % win
rate had *negative* median out-of-sample expectancy (−0.047 R on noise, −0.018 R even when a real momentum edge was
present), while the winning configs had 21–43 % win rates. **"High win rate + good R" doesn't exist for a real
momentum edge after costs; chasing it is the fastest way to give the edge back.**

### 1.3 The aggressive strategy stack
* **A1 — Momentum basket (≈ 85 % of risk).** NAM and ORB-60 on MES, MNQ, MCL, MGC, with per-market parameters chosen
  by the search engine and only kept if they pass the gate (§2.4).
  * Correlation control: ES and NQ share one risk budget (ρ ≈ 0.85); CL and GC each get their own.
  * Assumption to verify on real data: ≈ 2.4 effectively independent bets per day.
* **A2 — Late-session momentum on all four markets (≈ 15 %)**, high-volatility regime only.
* **A3 — Research queue:** CL-EIA event momentum, a dealer-gamma regime filter, more markets (M2K, M6E, 10-year).

Trade models used in the simulator (assumptions until real data replaces them):

| model | net E[R]/trade | trades/day | annual Sharpe | meaning |
|---|---|---|---|---|
| S1_planning | +0.064 | 0.8 | 0.56 | single market, published edge minus a 58 % decay haircut |
| **basket_planning** | +0.064 | 2.4 | **0.97** | the same edge on four markets |
| basket_optimistic | +0.147 | 2.4 | 2.19 | the paper's in-sample edge on four markets (upside case) |
| zero / negative edge | −0.04 / −0.07 | 2.4 | < 0 | control: what no skill gets you |

---

## 2. Simulation and optimisation engine

Code: `engine/qtengine/research/` (kernels, engine, overfit), UI: **Research lab** page.

### 2.1 Architecture
1. **JIT strategy kernels (numba).** Each family is a single pass over the day×minute panel.
   * Families: NAM (12 parameters), ORB (8), VWAP reversion (10), late-session momentum (6).
   * The NAM grid alone has 583,200 combinations, so configurations are sampled at random.
   * Speed: **0.4 ms per config per 300 days. 12,144 configs × 1,500 days (6 years) in ~30 s on one core.**
   * The kernel reproduces the reference Python strategy trade-for-trade (tested).
2. **Scoring.** Each config produces a daily net-R series with costs charged per trade in R. Stats are computed
   in-sample (first 70 %) and out-of-sample (last 30 %).
3. **The search is audited, not just the winner:**
   * **Walk-forward re-selection:** pick the best config on a rolling 2-year window, trade it the next quarter,
     repeat. This is the honest out-of-sample curve of what the search finds.
   * **CSCV probability of backtest overfitting (PBO)**, Bailey–Borwein–López de Prado–Zhu, over 2,000
     combinatorial splits.
   * **Deflated Sharpe** with raw *and* effective trial counts. Effective count = the participation ratio of the
     configs' correlation matrix; 12,144 configs behave like ≈ 26–29 independent bets.
4. **Topstep objective.** The walk-forward trades become an `EmpiricalTradeModel`, run through the Topstep
   lifecycle simulator. Configs are ranked by **net cash under Topstep rules**, not by Sharpe.
5. **Optimiser over account policy.** Account type × evaluation risk × funded policy × payout policy × slots ×
   correlation × reinvestment fraction (`scripts/aggressive_topstep.py`, ~180 lifecycle simulations plus fleets).

### 2.2 Calibration: proof the search doesn't fool itself

| | Pure noise (κ = 0) | Small real edge (κ = 0.01) |
|---|---|---|
| best in-sample Sharpe | 1.49 | 2.28 |
| same config out-of-sample | 0.64 | 1.88 |
| **walk-forward OOS Sharpe** | **0.11** | **1.00** |
| PBO | 27 % | 7 % |
| deflated Sharpe (effective trials) | 0.30 | 0.73 |

* **A naive optimiser finds Sharpe 1.5 in pure noise.** The walk-forward and deflated-Sharpe checks expose it.
* **PBO alone is not enough.** In the noise run it was only 27 %, because thousands of similar momentum configs
  shared one lucky out-of-sample stretch. That's why the gate requires all three tests.
* **The engine finds a real edge when one exists.** On the edge data, walk-forward OOS Sharpe was 1.00, though
  6 years still left the deflated Sharpe short of 0.95. **Plan on 8+ years of real history per market.**

### 2.3 Continuous discovery loop (production design)
* **Nightly:** append the day's bars, then re-run the search on a rolling window per market.
* **Champion/challenger:** a challenger replaces the live config only if it passes the gate *and* beats the
  champion's walk-forward OOS over the last 6 months.
* **Live drift monitor:** if live expectancy falls 2 standard errors below the walk-forward expectation, drop that
  market's risk to zero and send it back to research.
* **Throughput:** about 1–2 minutes per 12k configs per market, audit included; 50k configs × 4 markets nightly fits
  on a small VPS.
* **Hard rule:** every config ever tried is counted, so the deflated Sharpe penalises re-runs. **Re-searching until
  something passes is itself overfitting; the trial counter makes that visible.**

### 2.4 Promotion gate (per market config)
* walk-forward OOS Sharpe > 0.5;
* PBO < 20 %;
* deflated Sharpe (effective trials) ≥ 0.95;
* ≥ 300 OOS trades;
* positive in ≥ 3 of 4 calendar years;
* Topstep-simulator EV > 0 at the chosen risk.

A config that fails any one of these trades nothing.

---

## 3. Fast scaling path: Combine → funded → fleet → Live → flywheel

All numbers from `aggressive_topstep.md`: basket_planning unless stated, Topstep 2026 presets, every fee included.

### 3.1 Choose the account: 150K, Standard payout path
2-year net per slot at EV-optimal sizing:

| account | basket_planning mean | median | basket_optimistic mean |
|---|---|---|---|
| 50K Standard | $14.1k | $7.8k | $36.8k |
| 100K Standard | $19.4k | $9.4k | $53.4k |
| **150K Standard** | **$31.3k** | **$15.1k** | **$87.0k** |
| 50K Consistency (3 days, 40 %) | $6.4k | $4.8k | $19.0k |
| 150K Consistency | $11.2k | $7.7k | $36.6k |

**The Consistency path is worse for this strategy.** Positive-skew momentum makes big single days, and the 40 %
consistency limit blocks payouts until the rest of the window catches up.

### 3.2 Evaluation phase (the "Combine blitz")
* **Risk per trade: 35 % of the max-loss limit** ($1,575 on 150K) as the default.
  * At 25 %: 2-year median $13.5k, 80 % chance of ending positive, ~19 Combines a year.
  * At 50 % (max EV): mean $31.7k, but median $15.4k, 68 % positive, ~37 Combines a year.
  * Zero or negative edge loses money at *every* size (control runs), so aggressive sizing only pays with a real edge.
* **Day limits:** daily stop 2R; stop after 3 consecutive losses; daily profit cap at 45 % of the target so the 50 %
  consistency target can't block the pass.
* **On a fail, buy the next Combine the same day.** Budget per 150K slot: **≈ $3.8k a year at 25 % risk,
  ≈ $5.0k at 35 %, ≈ $6.5k at 50 %**, with the first payout after ~4.5 months (median).
* **The Combine *is* the forward test.** Its fills are simulated like a paper account, but it can pay, so skip a
  separate paper phase once the gate is passed.

### 3.3 Funded (XFA) phase
* **Keep the evaluation risk.** Cutting to half risk plus a scale-up rule lowered the 2-year mean from $19.8k to
  $13.1k. The funded account is still a cheap option.
* **Payouts:** request the maximum every cycle once profit ≥ the max loss. This was slightly better than paying out
  immediately ($20.0k vs $19.8k mean).
* **Upsizing a funded account has a ceiling** set by the payout cap. 150K Standard pays at most $5k per 5-winning-day
  cycle, and only 50 % of the balance, so anything beyond ≈ $2k/day of expected P&L just accumulates unwithdrawn.
  With the planning edge (≈ 0.15R expected per day), the cap never binds, so size is limited by survival, not the cap.
* **Scaling tiers** shown live on the Fleet page:

| buffer above the max-loss level | risk per trade | condition |
|---|---|---|
| < 1.5 × MLL | base (eval risk) | — |
| ≥ 1.5 × MLL | 1.5 × base | rolling 60-trade expectancy LCB90 > 0 and no live-vs-research drift |
| ≥ 2 × MLL | 2 × base | same, and still within the XFA scaling-plan contract limits |
| ≥ 3 × MLL | 3 × base | same |

* **Drop a tier immediately** when the buffer falls 15 % below the tier threshold.

### 3.4 Fleet phase: 3–5 slots, decorrelated
Sources disagree on Topstep's concurrent-XFA limit (3 to 5), so verify it. Results over 3 years:

| configuration | 1-year median | 3-year median | 3-year 5th pct | P(≥ $100k) | median months to $100k |
|---|---|---|---|---|---|
| 1 slot | $1.3k | $34.9k | −$17.9k | 26 % | 25 |
| 5 slots, copy-traded (ρ = 1) | $4.0k | $172k | **−$87.8k** | 64 % | 14 |
| **5 slots, decorrelated (ρ = 0.4)** | **$32.7k** | **$231k** | **−$2.0k** | **80 %** | 18 |
| 5 slots ρ = 0.4, optimistic edge | $132k | $794k | $336k | 100 % | 10 |

**Rule: never copy-trade identical accounts.** Give each slot a different market mix or strategy variant
(e.g. A: ES+CL, B: NQ+GC, C: ES+GC, D: NQ+CL, E: late-session basket). The mean is almost unchanged, the median rises
8×, and the bad tail shrinks from −$88k to −$2k.

### 3.5 Live Funded Account
* **Call-up:** Topstep promotes consistent XFA traders to Live at its discretion. You can hold one Live account at
  a time, sized from the average of your active XFAs.
* **Forfeit risk:** any XFA balance above the Live cap is forfeited at transfer, so **withdraw down to the cap
  before accepting**.
* **Payouts:** Live unlocks **daily payouts** after 30 days with ≥ $150 net. Dynamic Live Risk Expansion raises
  contract limits with profit (up to 100 lots in Topstep's example table).
* **Automation:** reported to be *not* allowed on Live, so run Live in confirm mode (engine proposes, you click).
* **Upside bound:** `topstep_150k_uncapped_hypothetical` approximates a funded account with no payout cap.

### 3.6 Flywheel: the only uncapped compounding
Every payout goes into a personal futures account trading the same validated basket. Results after 3 years:

| own-account risk per trade | planning median | P(≥ $1M) | optimistic median | P(≥ $1M) |
|---|---|---|---|---|
| 1 % | $304k | 6 % | $1.9M | 87 % |
| 2 % (≈ 0.8 × Kelly) | $344k | 18 % | $4.5M | 97 % |
| 4 % (over-betting) | $355k | 33 % (5th pct < 0) | $7.9M | 99 % |

* **Use 1–2 % (≤ Kelly).** 4 % raises the lottery tail but puts the bad case below zero.
* **Caveats:**
  * The personal account is capped at 500 MES ≈ 50 ES per trade for market capacity.
  * It is simulated independently of the prop accounts, which flatters diversification. Live, the same signals fire
    in both, so drawdowns coincide.

### 3.6b Two-phase plan: prop until $100k withdrawn, then trade it as your own money
Full tables: [results/two_phase_plan.md](results/two_phase_plan.md) (`scripts/two_phase_plan.py`). Setup: 5 × 150K,
decorrelated, 35 % of the max loss per trade.

**Phase 1, time to $100k withdrawn:**
* planning edge: median **21 months** (25th–75th percentile 13–32); 96 % chance within 5 years;
* optimistic edge: median 9 months.

**Phase 2, $100k of own money alone** (planning edge):

| risk per trade | year-1 median gain | 3-year median | P(≥ 30 % drawdown) | median income if you withdraw gains |
|---|---|---|---|---|
| **0.5 %** | +$12.8k | $146k | 5 % | ≈ $51 per trading day |
| 1 % | +$24.8k | $204k | 54 % | ≈ $98 per trading day |
| no edge, 0.5 % | −$12.7k | $68k | 75 % | $0 |

**Keep the prop fleet running after the switch.** 5-year median wealth (planning edge, 0.5 % own risk):
* stop the prop fleet at $100k: **$154k**;
* keep it running and keep feeding the own account: **$465k**, with the 5th percentile still ≈ $100k.

**Rules at the switch:**
1. Plan on the **after-tax** amount: prop payouts are usually taxed as income.
2. Keep ≈ 30 % outside trading (cash or an index ETF).
3. Own-account risk **0.5 % per trade**, at most 1 % (full Kelly ≈ 2.5 %).
4. Kill switch at −20 % from peak.
5. **Never carry the option-sized prop risk into your own account.**

### 3.7 Daily and weekly targets
Expected P&L per slot = trades/day × E[R] × risk ≈ **0.15R per day**: ≈ $240/day and $1.2k/week per 150K slot at
35 % risk (planning edge). Five slots ≈ $1.2k/day.

* **These are expectations, not quotas.** A single day's standard deviation is about 2.5R, so most days miss.
* **Never trade to hit a target.** The Fleet page shows targets so that drift (being far below them over 60+ trades)
  is visible.

---

## 4. Command center (dashboard)
* **Fleet command:**
  * per-slot cards: phase, attempt #, passes/losses, buffer meter, risk per trade, daily stop, daily/weekly
    target, current tier and the next scale trigger ("scale to $X when buffer ≥ $Y"), payout readiness;
  * fleet totals;
  * fleet simulator (slots, ρ, sizing, payout policy, milestones, fan chart);
  * pre-computed fleet scenarios.
* **Research lab:**
  * calibration panel (noise vs edge);
  * launch a background search on synthetic data or a server-side real data file;
  * live progress, the gate verdict (WF Sharpe, PBO, effective deflated Sharpe), PBO logit histogram, walk-forward
    equity, family table, and the in-sample-vs-out-of-sample leaderboard.
* **Unchanged:** Overview / Risk (real-time guard), Prop simulator, Analytics, Journal, Backtest, Growth planner.
* **To build next for live trading:**
  * a TopstepX (ProjectX) API adapter (bots allowed on Combine/XFA, not Live; no HFT; one source reports VPS/VPN
    order routing is restricted, so check);
  * push alerts;
  * the nightly re-search scheduler;
  * daily reconciliation against Topstep statements.

---

## 5. Brutal honesty

1. **The edge is still unproven on real data.** Every income number above assumes the basket exists at the planning
   level on four markets with ≈ independent signals. Two 2026 studies found naive momentum on MNQ fails after costs.
   The calibration proves the *engine* works; it does not prove the *market* has the edge. **Step one is still
   buying 8+ years of 1-minute data** for MES, MNQ, MCL, MGC (≈ $200–400 at Databento) and running the gate.
2. **Aggressive mode is expensive before it pays.**
   * ≈ $5k a year in Combines per 150K slot at 35 % risk; ≈ $25k a year for five slots. You need that bankroll
     *before* the first payout, which comes after ~4–5 months (median).
   * With copy-trading, the 5th-percentile 3-year outcome is **−$88k**.
3. **Behaviour at 35–50 % risk is brutal.** Two losing trades end an evaluation. Expect ~25–35 resets a year per slot
   and multi-week losing streaks across the fleet. This only works fully automated and with the reset budget fixed
   in advance.
4. **Firm risk.**
   * Topstep changed payout caps (April 2026), payout paths (February 2026) and platform rules this year.
   * Caps and payout paths limit extraction (theoretical ceiling: $227k per 150K Standard account per year, and only
     with $2k/day of profit).
   * Accounts can be reviewed; aggressive one-direction sizing can draw scrutiny.
   * Concentrating on one firm is a single point of failure. Keep the engine firm-agnostic (presets are data).
5. **Six figures:** plausible within 1.5–2 years *if* the planning basket edge is real (sim: median $231k by 3 years
   for 5 decorrelated slots).
   **Seven figures within 3 years:** needs either the optimistic edge (Sharpe ≈ 2.2) or the flywheel *plus* a better
   than planning edge. Combined probability from today: about **5–10 %**.
   **Most likely single outcome:** the gate fails on real data for 2–3 of the 4 markets, the surviving basket is
   closer to Sharpe 0.6–0.8, and the realistic result is the €20–50/day range from the earlier study, reached
   faster through slots.
6. **Not modelled:** taxes; Topstep's discretionary decisions (Live call-up timing, account reviews); payout
   processing delays; correlation between personal and prop trades; regime breaks where the edge disappears for a
   year.
