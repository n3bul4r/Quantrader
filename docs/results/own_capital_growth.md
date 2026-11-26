# Own-capital growth: €500 start + €100/month

Monte Carlo, 5,000 paths per scenario, 252 trading days/year, contribution at each month end, EURUSD 1.16 fixed, **pre-tax** unless stated. Trade models are assumptions (see SYSTEM_DESIGN.md §1).

## 1. Deterministic compounding (what a constant return would give)

| annual return | 1 year | 3 years | 5 years | 10 years |
|---|---|---|---|---|
| 0% | €1,700 | €4,100 | €6,500 | €12,500 |
| 3% | €1,731 | €4,306 | €7,038 | €14,617 |
| 5% | €1,752 | €4,448 | €7,420 | €16,251 |
| 7% | €1,773 | €4,593 | €7,821 | €18,089 |
| 10% | €1,804 | €4,816 | €8,461 | €21,283 |
| 15% | €1,855 | €5,207 | €9,639 | €28,020 |
| 20% | €1,906 | €5,619 | €10,966 | €37,008 |
| 30% | €2,007 | €6,514 | €14,130 | €64,736 |
| 50% | €2,205 | €8,598 | €22,984 | €193,719 |

## 2. Monte Carlo by scenario

p05/p95 = 5th/95th percentile outcome. 'Below contributed' = ended with less than you put in. Max DD = median of each path's worst peak-to-trough drop.

| scenario | years | put in | p05 | median | mean | p95 | P(below put in) | median max DD |
|---|---|---|---|---|---|---|---|---|
| Contributions only (0 %) | 1 | €1,700 | €1,700 | **€1,700** | €1,700 | €1,700 | 0% | 0% |
| Contributions only (0 %) | 3 | €4,100 | €4,100 | **€4,100** | €4,100 | €4,100 | 0% | 0% |
| Contributions only (0 %) | 5 | €6,500 | €6,500 | **€6,500** | €6,500 | €6,500 | 0% | 0% |
| Contributions only (0 %) | 10 | €12,500 | €12,500 | **€12,500** | €12,500 | €12,500 | 0% | 0% |
| Index ETF (MSCI World-like, 7 %/yr, 15 % vol) | 1 | €1,700 | €1,504 | **€1,761** | €1,773 | €2,076 | 36% | 8% |
| Index ETF (MSCI World-like, 7 %/yr, 15 % vol) | 3 | €4,100 | €3,534 | **€4,541** | €4,616 | €5,928 | 25% | 10% |
| Index ETF (MSCI World-like, 7 %/yr, 15 % vol) | 5 | €6,500 | €5,526 | **€7,650** | €7,841 | €10,769 | 21% | 13% |
| Index ETF (MSCI World-like, 7 %/yr, 15 % vol) | 10 | €12,500 | €10,837 | **€17,231** | €18,178 | €28,855 | 13% | 19% |
| Day trading with NO edge (costs only), CFD, 1 % risk | 1 | €1,700 | €1,331 | **€1,605** | €1,624 | €1,988 | 68% | 9% |
| Day trading with NO edge (costs only), CFD, 1 % risk | 3 | €4,100 | €2,560 | **€3,492** | €3,596 | €5,010 | 78% | 14% |
| Day trading with NO edge (costs only), CFD, 1 % risk | 5 | €6,500 | €3,443 | **€5,041** | €5,268 | €7,837 | 84% | 19% |
| Day trading with NO edge (costs only), CFD, 1 % risk | 10 | €12,500 | €4,754 | **€7,807** | €8,393 | €13,847 | 91% | 32% |
| NO edge, always ≥1 MES from day one (over-leveraged) | 1 | €1,700 | €100 | **€517** | €1,305 | €4,520 | 69% | 100% |
| NO edge, always ≥1 MES from day one (over-leveraged) | 3 | €4,100 | €100 | **€1,916** | €2,667 | €8,088 | 74% | 100% |
| NO edge, always ≥1 MES from day one (over-leveraged) | 5 | €6,500 | €107 | **€3,106** | €3,873 | €10,754 | 78% | 100% |
| NO edge, always ≥1 MES from day one (over-leveraged) | 10 | €12,500 | €126 | **€5,749** | €6,492 | €15,891 | 87% | 100% |
| S1 planning edge, MES futures, 1 % risk (skips trades it can't size) | 1 | €1,700 | €1,700 | **€1,700** | €1,700 | €1,700 | 0% | 0% |
| S1 planning edge, MES futures, 1 % risk (skips trades it can't size) | 3 | €4,100 | €3,989 | **€4,088** | €4,099 | €4,268 | 53% | 1% |
| S1 planning edge, MES futures, 1 % risk (skips trades it can't size) | 5 | €6,500 | €5,634 | **€6,465** | €6,626 | €8,154 | 52% | 5% |
| S1 planning edge, MES futures, 1 % risk (skips trades it can't size) | 10 | €12,500 | €9,376 | **€15,594** | €16,483 | €26,402 | 25% | 17% |
| S1 planning edge, always ≥1 MES from day one (over-leveraged) | 1 | €1,700 | €108 | **€2,387** | €2,647 | €6,679 | 39% | 97% |
| S1 planning edge, always ≥1 MES from day one (over-leveraged) | 3 | €4,100 | €183 | **€6,970** | €7,140 | €13,981 | 24% | 99% |
| S1 planning edge, always ≥1 MES from day one (over-leveraged) | 5 | €6,500 | €3,378 | **€11,596** | €11,921 | €21,261 | 15% | 99% |
| S1 planning edge, always ≥1 MES from day one (over-leveraged) | 10 | €12,500 | €11,517 | **€23,763** | €26,515 | €50,422 | 7% | 99% |
| S1 planning edge, CFD, 1 % risk/trade | 1 | €1,700 | €1,470 | **€1,786** | €1,814 | €2,254 | 35% | 8% |
| S1 planning edge, CFD, 1 % risk/trade | 3 | €4,100 | €3,332 | **€4,733** | €4,910 | €7,111 | 27% | 12% |
| S1 planning edge, CFD, 1 % risk/trade | 5 | €6,500 | €5,319 | **€8,254** | €8,757 | €13,876 | 20% | 17% |
| S1 planning edge, CFD, 1 % risk/trade | 10 | €12,500 | €10,479 | **€20,607** | €23,192 | €44,371 | 12% | 26% |
| S1 planning edge, CFD, 2 % risk/trade | 1 | €1,700 | €1,247 | **€1,851** | €1,950 | €3,016 | 38% | 18% |
| S1 planning edge, CFD, 2 % risk/trade | 3 | €4,100 | €2,628 | **€5,212** | €6,002 | €12,199 | 30% | 30% |
| S1 planning edge, CFD, 2 % risk/trade | 5 | €6,500 | €4,073 | **€9,610** | €12,260 | €28,388 | 24% | 39% |
| S1 planning edge, CFD, 2 % risk/trade | 10 | €12,500 | €7,544 | **€28,672** | €47,803 | €145,755 | 17% | 53% |
| S1 planning edge on US500 + US100 CFDs, 1 % risk | 1 | €1,700 | €1,424 | **€1,857** | €1,901 | €2,541 | 30% | 11% |
| S1 planning edge on US500 + US100 CFDs, 1 % risk | 3 | €4,100 | €3,322 | **€5,293** | €5,610 | €9,035 | 20% | 18% |
| S1 planning edge on US500 + US100 CFDs, 1 % risk | 5 | €6,500 | €5,394 | **€9,806** | €11,029 | €20,667 | 13% | 24% |
| S1 planning edge on US500 + US100 CFDs, 1 % risk | 10 | €12,500 | €11,705 | **€30,364** | €38,814 | €92,615 | 6% | 35% |
| S1 optimistic edge, CFD, 1 % risk/trade | 1 | €1,700 | €1,587 | **€1,958** | €1,991 | €2,504 | 14% | 8% |
| S1 optimistic edge, CFD, 1 % risk/trade | 3 | €4,100 | €4,251 | **€6,234** | €6,494 | €9,650 | 4% | 11% |
| S1 optimistic edge, CFD, 1 % risk/trade | 5 | €6,500 | €7,957 | **€13,158** | €14,152 | €23,350 | 1% | 15% |
| S1 optimistic edge, CFD, 1 % risk/trade | 10 | €12,500 | €25,301 | **€57,235** | €66,786 | €138,657 | 0% | 22% |
| S1 optimistic edge, CFD, 2 % risk/trade | 1 | €1,700 | €1,464 | **€2,241** | €2,382 | €3,761 | 15% | 16% |
| S1 optimistic edge, CFD, 2 % risk/trade | 3 | €4,100 | €4,200 | **€9,264** | €11,112 | €24,010 | 4% | 27% |
| S1 optimistic edge, CFD, 2 % risk/trade | 5 | €6,500 | €9,007 | **€26,349** | €36,201 | €91,202 | 1% | 34% |
| S1 optimistic edge, CFD, 2 % risk/trade | 10 | €12,500 | €46,774 | **€270,987** | €480,723 | €1,680,977 | 0% | 43% |

## 3. After an illustrative 30 % flat tax (e.g. France's PFU — check your own country)

Trading gains are realised and taxed every year; the accumulating ETF is taxed once, on exit at the horizon (tax-advantaged wrappers such as a French PEA would lower this further).

| scenario | median after 5 y | median after 10 y | mean after 10 y |
|---|---|---|---|
| Index ETF (MSCI World-like, 7 %/yr, 15 % vol) | €7,305 | €15,812 | €16,414 |
| S1 planning edge, CFD, 1 % risk/trade | €7,636 | €17,574 | €18,620 |
| S1 optimistic edge, CFD, 1 % risk/trade | €10,727 | €36,445 | €39,628 |

## 4. The contribution lever (S1 planning edge, CFD, 1 % risk — median after 10 years)

| monthly contribution | put in | median 10 y | ETF median 10 y |
|---|---|---|---|
| €100 | €12,500 | €20,484 | €17,370 |
| €200 | €24,500 | €39,843 | €33,855 |
| €300 | €36,500 | €59,201 | €50,371 |
| €500 | €60,500 | €97,972 | €83,307 |

## 5. When does trading become an income?

Capital needed for **€100/day (≈ €25,000/yr)** from trading = 25,000 ÷ net annual return. At the planning edge sized at ~1 % risk (≈ 15 %/yr expected, ~25-30 % vol) that is ≈ **€165,000**.

| monthly contribution | years to €165k at 7 % | at 15 % | at 30 % |
|---|---|---|---|
| €100 | 34.2 | 21.2 | 13.4 |
| €300 | 20.8 | 14.2 | 9.8 |
| €500 | 15.5 | 11.2 | 8.0 |
| €1000 | 9.8 | 7.7 | 5.8 |
