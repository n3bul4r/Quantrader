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
