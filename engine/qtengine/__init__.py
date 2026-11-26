"""qtengine — quantitative core for prop-firm futures trading.

Layers (each usable on its own):
    instruments   contract specs + all-in cost model
    data          bar loading / session handling / synthetic data for tests
    features      session VWAP, noise area, realized vol, regimes
    strategies    S1 noise-area momentum, S2 late-day momentum, S3 VWAP reversion (candidate)
    backtest      bar-driven intraday simulator producing a trade list in points / R
    metrics       expectancy, PF, Sharpe, PSR/DSR, drawdowns, breakdowns
    validation    walk-forward, sign-flip permutation test, bootstrap CIs
    risk          sizing, analytic + Monte Carlo risk of ruin, live risk guard
    prop          prop-firm rule presets, account state machine, lifecycle Monte Carlo
    journal       automatic trade tagging
"""

__version__ = "0.1.0"
