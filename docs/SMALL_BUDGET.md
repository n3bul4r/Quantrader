# The best plan with €300

*2026-11-26. Full tables: [results/small_budget.md](results/small_budget.md) (`engine/scripts/small_budget.py`).
Bootstrap simulation: every Combine, renewal and activation fee is paid from the bankroll (start money, top-ups,
payouts); payouts buy more accounts, up to 5. Trade models are assumptions; the edge is unvalidated.*

## What changes with a small bankroll
1. **Lower risk per trade: 10–15 % of the max loss, not 35 %.**
   * The 35 % figure assumed you can always re-buy a Combine.
   * $348 buys about three Topstep attempts, so surviving each one matters more.
   * Results on Topstep 50K (planning basket, 3 years):

     | risk/trade | P(bust) | P(≥ $10k) |
     |---|---|---|
     | 15 % | 74 % | 25 % |
     | 35 % | 90 % | 10 % |

2. **Cost per attempt matters a lot.**
   * A discounted one-time evaluation (~$30, no monthly fee) does far better than Topstep's $49/month plus $149 on
     passing: busted 44 % vs 74 %, and P(≥ $10k in 3 years) 49 % vs 25 %.
   * Black Friday is the usual time for the deepest prop-firm discounts.
   * Trade-off: Apex reportedly bans fully automated bots on funded accounts, so you'd need semi-automatic execution
     (the engine alerts you, you click).
3. **€100/month is the biggest lever of all** (Topstep 50K, planning edge, 3 years):

   | | bust | median net | P(≥ $10k) |
   |---|---|---|---|
   | €300 only | 74 % | −$294 | 25 % |
   | **€300 + €100/month** | **3 %** | **+$29.5k** | **84 %** |

   * With top-ups you can afford retries again, and 25 % risk becomes better: median +$38.6k, and a 14 % chance of
     $100k in 3 years.
4. **Without an edge, money only drains.** With no edge you lose the €300 (93–97 %), or everything you add each
   month. Hence step 1.
5. **Your own trading account at €300 is pointless.** The median gain is about €20 a year even with the edge; the
   money is only useful for buying evaluations.

## The plan
1. **Weeks 0–4: prove the edge (cost €0).**
   * Databento gives new accounts $125 of free credit. Use it for 1-minute history of MES, MNQ, MCL, MGC
     (2018 onward).
   * Run `edge_search.py --data …` per market and apply the gate (AGGRESSIVE_SYSTEM §2.4).
   * Rehearse execution on a free broker demo (Tradovate or NinjaTrader sim).
   * **If no market passes, stop:** don't buy anything, and put the €300 in an index ETF.
2. **First attempts.**
   * Buy the cheapest qualifying evaluation: a Black Friday deal, or Topstep with a 15 % referral code.
   * **Keep the activation fee ($99–149) untouched in reserve.**
   * Risk **10–15 % of the max loss per trade** (Topstep 50K: $200–300); daily stop 2R.
   * Trade only markets that passed the gate.
3. **Every month: add €100 to the bankroll.** It's only for evaluations and renewals, never for chasing losses.
4. **After the first payouts:**
   * buy more accounts, up to 5;
   * give each account a different market mix (decorrelated);
   * raise risk to 25 % once the bankroll covers ~10 attempts (~$500 on Topstep).
5. **At $100k withdrawn:** switch to the two-phase plan (AGGRESSIVE_SYSTEM §3.6b) and keep the accounts running.

## Odds (3 years, if the planning edge is real)

| setup | busted | median net | P(≥ $10k) | P(≥ $100k) |
|---|---|---|---|---|
| €300 only, Topstep 50K, 15 % risk | 74 % | −$294 | 25 % | 0 % |
| €300 only, discounted Apex, 10 % risk | 44 % | +$8.9k | 49 % | 0 % |
| €300 + €100/mo, Topstep, 15 % risk | 3 % | +$29.5k | 84 % | 1 % |
| €300 + €100/mo, Topstep, 25 % risk | 10 % | +$38.6k | 78 % | 14 % |

* Whether the planning edge holds on real data is the unknown. I put it at roughly 35 %.
* Step 1 is designed so that a failed edge costs you nothing but time.

## The "one 50K, $500 per trade" plan — what it really pays
Full tables: [results/fifty_k_plan.md](results/fifty_k_plan.md) (`engine/scripts/fifty_k_plan.py`).

**$500 per trade is the risk (the loss if the stop is hit), not the profit.**

| edge | win rate | typical win / loss at $500 risk | average profit per trade | expected P&L per month *if the account survived* |
|---|---|---|---|---|
| basket, planning | 37 % | +$925 / −$475 | **+$32** | $1,605 |
| basket, optimistic | 40 % | +$925 / −$475 | +$74 | $3,709 |

**Why one 50K can't sustain $3–4k a month:**
* At $500 risk a normal day swings about ±$1,250, while the 50K can only drop $2,000 from its peak.
* After a payout, the floor moves up to the starting balance, so a typical funded 50K survives **about a month**.

First 6 months of one funded 50K, $500/trade, account not replaced:

| edge | average payout per month | median | P(≥ $3,000/month) | P(no payout at all) |
|---|---|---|---|---|
| planning | $263 | **$0** | 1 % | 69 % |
| optimistic | $512 | $0 | 5 % | 60 % |

**How to get to $3–4k a month: more accounts, replaced when lost, over time.**
* First 6 months without replacing lost accounts:
  * 5 × 50K at $500: mean $1.2k/month, median $504 (planning); optimistic $2.4k / $1.4k.
  * 3 × 150K at $1,125: mean $1.6k/month (planning); optimistic $3.2k.
* With continuous replacement (AGGRESSIVE_SYSTEM §3.4), 5 × 150K decorrelated, planning edge:
  * **year-1 median ≈ $33k (≈ $2.7k a month)**;
  * 3-year median ≈ $231k.
* From €300, the €100/month top-up is what keeps the machine going (see the table above).

### Strategy rules at $500 risk on a Topstep 50K
* **Markets:** MES, MNQ, MCL, MGC. Use only those that pass the validation gate.
* **Entry (noise-area momentum):**
  * band = max/min(today's open, yesterday's close) ± the 14-day average move from the open at that time of day;
  * at every :00 and :30 from 30 min after the session opens until 1 h before it closes: long if the price closes
    above the upper band, short if below the lower band.
* **Stop:** the band or VWAP, whichever is tighter; re-checked every 30 minutes and only ever moved in your
  favour. It is always held on the server as a bracket order.
* **Exit:** stop, or 1 minute before the session closes. Never hold overnight.
* **Size:** $500 per trade (25 % of the $2,000 max loss).
  * If MES and MNQ signal the same direction, risk $250 each, because they are ~0.85 correlated.
  * Contracts = $500 ÷ (stop distance × $ per point + costs). Examples: MES 20-pt stop → 4 MES; MNQ 60-pt stop →
    4 MNQ; MCL $0.40 stop → 12 MCL; MGC $8 stop → 6 MGC.
* **Daily limits:**
  * daily stop $1,000;
  * stop after 3 losses in a row;
  * during the Combine, stop for the day at +$1,350 (keeps the 50 % consistency target safe).
* **Payouts:** wait for a $2,000 cushion, then take the maximum each cycle.
* **When an account is lost,** buy the next Combine from the bankroll and keep going.
* **Before trading CL/GC:** the engine currently assumes the equity session (09:30–16:00 ET). Crude (09:00–14:30)
  and gold (08:20–13:30) need their own session settings and validation before going live.
