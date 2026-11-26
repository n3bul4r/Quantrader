# Portfolio / steady-state economics

S1 on MES and MNQ treated as 1.4 independent trades/day (optimistic: the two are ~0.8 correlated). 4,000 paths/cell, EURUSD 1.16. Net = payouts (trader share) − all fees over the horizon. €/day columns are per trading day over the whole horizon.

| program | model | horizon | risk $/trade | accounts | net mean $ | net median $ | p05 $ | p95 $ | P(net>0) | €/day mean | €/day median |
|---|---|---|---|---|---|---|---|---|---|---|---|
| topstep_50k | S1_planning_MES+MNQ | 1y | 300 | 1 | 937 | -88 | -1,031 | 6,470 | 48% | 3.2 | -0.3 |
| topstep_50k | S1_planning_MES+MNQ | 1y | 500 | 1 | 2,301 | 518 | -1,529 | 12,198 | 59% | 7.9 | 1.8 |
| topstep_50k | S1_planning_MES+MNQ | 1y | 700 | 1 | 2,837 | 239 | -2,119 | 16,965 | 54% | 9.7 | 0.8 |
| topstep_50k | S1_planning_MES+MNQ | 2y | 300 | 1 | 2,208 | 983 | -1,697 | 10,509 | 63% | 3.8 | 1.7 |
| topstep_50k | S1_planning_MES+MNQ | 2y | 500 | 1 | 5,599 | 3,205 | -2,525 | 21,772 | 73% | 9.6 | 5.5 |
| topstep_50k | S1_planning_MES+MNQ | 2y | 700 | 1 | 7,676 | 3,856 | -3,589 | 32,969 | 70% | 13.1 | 6.6 |
| topstep_150k | S1_planning_MES+MNQ | 1y | 675 | 1 | 1,478 | -869 | -2,682 | 13,842 | 41% | 5.1 | -3.0 |
| topstep_150k | S1_planning_MES+MNQ | 1y | 1125 | 1 | 4,670 | 617 | -3,725 | 28,419 | 54% | 16.0 | 2.1 |
| topstep_150k | S1_planning_MES+MNQ | 1y | 1500 | 1 | 5,817 | 270 | -4,917 | 37,500 | 52% | 19.9 | 0.9 |
| topstep_150k | S1_planning_MES+MNQ | 2y | 675 | 1 | 3,726 | 899 | -4,625 | 22,855 | 55% | 6.4 | 1.5 |
| topstep_150k | S1_planning_MES+MNQ | 2y | 1125 | 1 | 11,496 | 5,871 | -6,409 | 49,634 | 69% | 19.7 | 10.0 |
| topstep_150k | S1_planning_MES+MNQ | 2y | 1500 | 1 | 15,602 | 7,087 | -8,493 | 70,720 | 68% | 26.7 | 12.1 |
| topstep_150k | S1_planning_MES+MNQ | 2y | 1125 | 5 | 57,478 | 29,357 | -32,045 | 248,170 | 69% | 98.3 | 50.2 |
| topstep_50k | S1_optimistic_MES+MNQ | 1y | 300 | 1 | 3,001 | 1,605 | -919 | 11,658 | 72% | 10.3 | 5.5 |
| topstep_50k | S1_optimistic_MES+MNQ | 1y | 500 | 1 | 5,970 | 3,839 | -1,427 | 20,855 | 79% | 20.4 | 13.1 |
| topstep_50k | S1_optimistic_MES+MNQ | 1y | 700 | 1 | 7,237 | 4,555 | -2,017 | 24,855 | 74% | 24.8 | 15.6 |
| topstep_50k | S1_optimistic_MES+MNQ | 2y | 300 | 1 | 6,945 | 5,369 | -834 | 19,849 | 89% | 11.9 | 9.2 |
| topstep_50k | S1_optimistic_MES+MNQ | 2y | 500 | 1 | 15,091 | 12,022 | -638 | 41,195 | 93% | 25.8 | 20.6 |
| topstep_50k | S1_optimistic_MES+MNQ | 2y | 700 | 1 | 20,350 | 16,878 | -1,699 | 51,808 | 91% | 34.8 | 28.9 |
| topstep_150k | S1_optimistic_MES+MNQ | 1y | 675 | 1 | 6,259 | 2,826 | -2,384 | 26,965 | 67% | 21.4 | 9.7 |
| topstep_150k | S1_optimistic_MES+MNQ | 1y | 1125 | 1 | 13,383 | 7,851 | -3,427 | 49,265 | 76% | 45.8 | 26.9 |
| topstep_150k | S1_optimistic_MES+MNQ | 1y | 1500 | 1 | 16,159 | 9,315 | -4,470 | 60,925 | 74% | 55.3 | 31.9 |
| topstep_150k | S1_optimistic_MES+MNQ | 2y | 675 | 1 | 14,263 | 10,363 | -2,788 | 44,716 | 85% | 24.4 | 17.7 |
| topstep_150k | S1_optimistic_MES+MNQ | 2y | 1125 | 1 | 33,307 | 25,385 | -2,627 | 97,389 | 91% | 57.0 | 43.4 |
| topstep_150k | S1_optimistic_MES+MNQ | 2y | 1500 | 1 | 44,242 | 33,503 | -4,440 | 125,224 | 90% | 75.7 | 57.3 |
| topstep_150k | S1_optimistic_MES+MNQ | 2y | 1125 | 5 | 166,536 | 126,924 | -13,134 | 486,944 | 91% | 284.9 | 217.1 |
