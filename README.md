# Quantrader

A quantitative trading system for **prop-firm futures accounts** (Topstep, Apex): a research-backed strategy
core, a risk engine built around trailing-drawdown rules, a prop-firm lifecycle simulator, and a dark-mode web
dashboard.

> **Read first:** [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) — strategies, risk engine, architecture,
> roadmap and the honesty section. [docs/RESEARCH.md](docs/RESEARCH.md) — evidence and sources.
> [docs/OWN_CAPITAL.md](docs/OWN_CAPITAL.md) — trading your own money without a prop firm (€500 + €100/month,
> 1/3/5/10-year projections vs an index ETF). Monte Carlo tables: [docs/results/](docs/results/).

## Main findings

* **Core edge:** market intraday momentum (dealer short-gamma hedging; JFE 2018/2021), implemented as the
  *noise-area breakout* (Zarattini–Aziz–Barbon 2024) on MES/MNQ, flat every night. This is strategy S1.
* **Planning edge after the post-publication haircut:** +0.064 R/trade net, profit factor 1.10, Sharpe ≈ 0.56.
* **Sizing:** a prop account is an option, so fixed risk of 20–25 % of the max-loss limit per trade maximises
  EV. Shrinking size as the drawdown buffer falls lowers EV.
* **Income:** with the planning edge, one Topstep 50K slot is worth about €8/day (mean) in year 1. €100/day needs
  about 5 × 150K accounts over two years, and even then the median is about €50/day. No strategy here has been
  validated on real data yet; that is roadmap step 1.
* **Own money, no prop firm (€500 + €100/month):** with the planning edge, the 10-year median is about €20.6k vs
  €17.2k for an index ETF and €12.5k put in. After tax the two are nearly equal. With no edge it is about €7.8k.

## Layout

```
engine/                     Python quant engine (package: qtengine)
  qtengine/instruments.py   contract specs + all-in cost model
  qtengine/data.py          1-min bar loading, RTH sessions, synthetic generator (tests/demo only)
  qtengine/features.py      day panel, VWAP, noise area, realised-vol regimes
  qtengine/strategies/      S1 noise-area momentum · S2 late-session momentum · S3 VWAP reversion (candidate)
  qtengine/backtest.py      cost-aware intraday backtester (points → R → sized $)
  qtengine/metrics.py       expectancy, PF, Sharpe, PSR / Deflated Sharpe, MinTRL, breakdowns
  qtengine/validation.py    walk-forward, sign-flip permutation test, bootstrap CI, promotion gate
  qtengine/risk/            sizing (buffer, vol-target, Kelly, scaling policy) · ruin maths · live guard
  qtengine/prop/            rule presets (YAML) · account rule tracker · lifecycle Monte Carlo
  qtengine/journal.py       automatic trade tagging (session, outcome, violations, revenge, news)
  qtengine/growth.py        own-capital growth Monte Carlo (contributions, vehicle granularity, tax) vs ETF
  qtengine/execution.py     BrokerAdapter contract + PaperBroker (TopstepX/Tradovate/Rithmic adapters: roadmap)
  qtengine/api/main.py      FastAPI service (REST + WebSocket)
  scripts/                  prop_economics.py · portfolio_economics.py · sizing_policies.py · own_capital_growth.py
  tests/                    39 tests
web/                        Next.js 15 dashboard (Overview, Risk, Analytics, Journal, Backtest, Prop simulator, Growth planner)
docs/                       design, research, generated results
```

## Run it

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e "engine[dev]"
(cd engine && pytest -q)

uvicorn qtengine.api.main:app --port 8000          # API, docs at http://localhost:8000/docs
cd web && npm install && npm run build && npm start   # http://localhost:3000 (proxies /api → :8000)
```

On the Overview page, click **Load demo data** to fill the journal with *synthetic* trades. They are labelled as
such everywhere. To backtest real data, upload 1-minute OHLCV (CSV/Parquet: `ts, open, high, low, close,
volume`, UTC) on the Backtest page, or use `qtengine.data.load_bars` together with `qtengine.validation.walk_forward`.

## Caveats

* The prop-firm rule presets in `engine/qtengine/prop/presets/programs.yaml` are planning values compiled in
  Nov 2026 from partly conflicting secondary sources. Verify them on the firm's own rulebook and edit the file.
* Trade models in the simulator are assumptions until you replace them with your own out-of-sample trades
  (`EmpiricalTradeModel.from_trades`).
* This is research software, not investment advice. Futures trading can lose more than you expect.
