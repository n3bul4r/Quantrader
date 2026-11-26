"""JIT-compiled intraday strategy kernels for massive parameter searches.

Each kernel walks a minute-aligned day panel (D days x 390 minutes) once and writes
trades into preallocated arrays. Conventions match qtengine.strategies (decision on a
bar close, fill at that close, stops checked on later bars, gap-through fills at the
open, stop assumed before target inside one bar, flat by `exit_min`).

Trade record columns (float64 array [n, 9]):
    0 day  1 side  2 entry_min  3 exit_min  4 entry  5 exit  6 stop_init  7 mae_pts  8 mfe_pts
"""
from __future__ import annotations

import numpy as np
from numba import njit

NCOL = 9


@njit(cache=True)
def _write(out, n, day, side, emin, xmin, entry, exitp, stop, mae, mfe):
    out[n, 0] = day
    out[n, 1] = side
    out[n, 2] = emin
    out[n, 3] = xmin
    out[n, 4] = entry
    out[n, 5] = exitp
    out[n, 6] = stop
    out[n, 7] = mae
    out[n, 8] = mfe
    return n + 1


@njit(cache=True)
def _manage(side, entry, stop, target, o, h, l):
    """Return (filled, price, reason) for one bar. reason 1=stop 2=target."""
    if side > 0:
        if l <= stop:
            return True, min(stop, o), 1
        if target > 0 and h >= target:
            return True, max(target, o), 2
    else:
        if h >= stop:
            return True, max(stop, o), 1
        if target > 0 and l <= target:
            return True, min(target, o), 2
    return False, 0.0, 0


@njit(cache=True)
def noise_momentum(O, H, L, C, V, SIG, day_open, prev_close, regime,
                   band_mult, first_dec, dec_every, last_entry, exit_min, stop_floor,
                   trail_mode, target_r, max_entries, regime_filter, direction, out):
    """F1 noise-area momentum family.
    trail_mode: 0 max(band,VWAP) 1 VWAP 2 band 3 none (fixed stop)
    target_r: 0 = no target, else take profit at target_r * initial risk
    regime_filter: 0 all days, 1 high-vol only, -1 low-vol only
    direction: 0 both, 1 long only, -1 short only"""
    D, M = C.shape
    n = 0
    for t in range(D):
        if np.isnan(SIG[t, 0]):
            continue
        if regime_filter != 0 and regime[t] != regime_filter:
            continue
        hi_ref = max(day_open[t], prev_close[t])
        lo_ref = min(day_open[t], prev_close[t])
        pos = 0
        entry = stop = stop0 = target = mae = mfe = 0.0
        emin = 0
        entries = 0
        for i in range(M):
            up = hi_ref * (1 + band_mult * SIG[t, i])
            dn = lo_ref * (1 - band_mult * SIG[t, i])
            if pos != 0 and i > emin:
                if pos > 0:
                    mfe = max(mfe, H[t, i] - entry)
                    mae = max(mae, entry - L[t, i])
                else:
                    mfe = max(mfe, entry - L[t, i])
                    mae = max(mae, H[t, i] - entry)
                f, px, _r = _manage(pos, entry, stop, target, O[t, i], H[t, i], L[t, i])
                if f:
                    n = _write(out, n, t, pos, emin, i, entry, px, stop0, mae, mfe)
                    pos = 0
                elif i >= exit_min:
                    n = _write(out, n, t, pos, emin, i, entry, C[t, i], stop0, mae, mfe)
                    pos = 0
                    break
            if i >= first_dec and (i - first_dec) % dec_every == 0 and i <= last_entry:
                if pos != 0 and trail_mode != 3:
                    if trail_mode == 0:
                        tr = max(up, V[t, i]) if pos > 0 else min(dn, V[t, i])
                    elif trail_mode == 1:
                        tr = V[t, i]
                    else:
                        tr = up if pos > 0 else dn
                    if pos * (C[t, i] - tr) < 0:
                        n = _write(out, n, t, pos, emin, i, entry, C[t, i], stop0, mae, mfe)
                        pos = 0
                    elif pos > 0:
                        stop = max(stop, tr)
                    else:
                        stop = min(stop, tr)
                if entries >= max_entries:
                    continue
                want = 0
                if C[t, i] > up and direction >= 0:
                    want = 1
                elif C[t, i] < dn and direction <= 0:
                    want = -1
                if want == 0 or want == pos:
                    continue
                if pos != 0:
                    n = _write(out, n, t, pos, emin, i, entry, C[t, i], stop0, mae, mfe)
                    pos = 0
                floor = stop_floor * SIG[t, i] * day_open[t]
                entry = C[t, i]
                if want > 0:
                    stop = entry - floor
                    if trail_mode != 3:
                        stop = min(max(up, V[t, i]) if trail_mode == 0 else (V[t, i] if trail_mode == 1 else up), entry - floor)
                else:
                    stop = entry + floor
                    if trail_mode != 3:
                        stop = max(min(dn, V[t, i]) if trail_mode == 0 else (V[t, i] if trail_mode == 1 else dn), entry + floor)
                stop0 = stop
                target = entry + want * target_r * abs(entry - stop) if target_r > 0 else 0.0
                pos, emin, mae, mfe = want, i, 0.0, 0.0
                entries += 1
        if pos != 0:
            n = _write(out, n, t, pos, emin, M - 1, entry, C[t, M - 1], stop0, mae, mfe)
    return n


@njit(cache=True)
def opening_range(O, H, L, C, day_open, regime, or_len, last_entry, exit_min, stop_frac,
                  target_r, max_entries, regime_filter, direction, min_range_pts, out):
    """F2 opening-range breakout. Range = high/low of the first `or_len` minutes.
    Enter on a close beyond the range; stop = entry -/+ stop_frac * range; optional target."""
    D, M = C.shape
    n = 0
    for t in range(D):
        if regime_filter != 0 and regime[t] != regime_filter:
            continue
        orh = -1e18
        orl = 1e18
        for i in range(or_len):
            orh = max(orh, H[t, i])
            orl = min(orl, L[t, i])
        rng = orh - orl
        if rng < min_range_pts:
            continue
        pos = 0
        entry = stop = target = mae = mfe = 0.0
        emin = 0
        entries = 0
        for i in range(or_len, M):
            if pos != 0 and i > emin:
                if pos > 0:
                    mfe = max(mfe, H[t, i] - entry)
                    mae = max(mae, entry - L[t, i])
                else:
                    mfe = max(mfe, entry - L[t, i])
                    mae = max(mae, H[t, i] - entry)
                f, px, _r = _manage(pos, entry, stop, target, O[t, i], H[t, i], L[t, i])
                if f:
                    n = _write(out, n, t, pos, emin, i, entry, px, stop, mae, mfe)
                    pos = 0
                elif i >= exit_min:
                    n = _write(out, n, t, pos, emin, i, entry, C[t, i], stop, mae, mfe)
                    pos = 0
                    break
            if pos == 0 and entries < max_entries and i <= last_entry:
                want = 0
                if C[t, i] > orh and direction >= 0:
                    want = 1
                elif C[t, i] < orl and direction <= 0:
                    want = -1
                if want != 0:
                    entry = C[t, i]
                    stop = entry - want * stop_frac * rng
                    target = entry + want * target_r * stop_frac * rng if target_r > 0 else 0.0
                    pos, emin, mae, mfe = want, i, 0.0, 0.0
                    entries += 1
        if pos != 0:
            n = _write(out, n, t, pos, emin, M - 1, entry, C[t, M - 1], stop, mae, mfe)
    return n


@njit(cache=True)
def vwap_reversion(O, H, L, C, V, VSD, SIG, day_open, prev_close, regime,
                   start_min, last_entry, exit_min, band_k, stop_k, target_mode, time_stop,
                   max_entries, regime_filter, inside_noise, out):
    """F3 VWAP fade (the 'high win-rate' family). target_mode: 0 = VWAP, 1 = halfway to VWAP."""
    D, M = C.shape
    n = 0
    for t in range(D):
        if np.isnan(SIG[t, 0]):
            continue
        if regime_filter != 0 and regime[t] != regime_filter:
            continue
        hi_ref = max(day_open[t], prev_close[t])
        lo_ref = min(day_open[t], prev_close[t])
        pos = 0
        entry = stop = mae = mfe = 0.0
        emin = 0
        entries = 0
        last_exit = -10000
        for i in range(start_min, M):
            if pos != 0:
                if pos > 0:
                    mfe = max(mfe, H[t, i] - entry)
                    mae = max(mae, entry - L[t, i])
                else:
                    mfe = max(mfe, entry - L[t, i])
                    mae = max(mae, H[t, i] - entry)
                tgt = V[t, i - 1] if target_mode == 0 else 0.5 * (entry + V[t, i - 1])
                f, px, _r = _manage(pos, entry, stop, tgt, O[t, i], H[t, i], L[t, i])
                if not f and (i - emin >= time_stop or i >= exit_min):
                    f, px = True, C[t, i]
                if f:
                    n = _write(out, n, t, pos, emin, i, entry, px, stop, mae, mfe)
                    pos = 0
                    last_exit = i
                    if i >= exit_min:
                        break
                continue
            if entries >= max_entries or i > last_entry or i - last_exit < 15:
                continue
            sd = VSD[t, i]
            if sd < 0.25 * SIG[t, i] * day_open[t]:
                continue
            if inside_noise == 1:
                up = hi_ref * (1 + SIG[t, i])
                dn = lo_ref * (1 - SIG[t, i])
                if C[t, i] >= up or C[t, i] <= dn:
                    continue
            dev = C[t, i] - V[t, i]
            want = 0
            if dev <= -band_k * sd:
                want = 1
            elif dev >= band_k * sd:
                want = -1
            if want != 0:
                entry = C[t, i]
                stop = entry - want * stop_k * sd
                pos, emin, mae, mfe = want, i, 0.0, 0.0
                entries += 1
    return n


@njit(cache=True)
def late_momentum(O, H, L, C, prev_close, regime, signal_min, exit_min, lookback, z_min, stop_mult,
                  regime_filter, out):
    """F4 last-half-hour momentum (Gao et al. / Baltussen et al.)."""
    D, M = C.shape
    n = 0
    rod = np.empty(D)
    mv = np.empty(D)
    for t in range(D):
        rod[t] = C[t, signal_min] / prev_close[t] - 1.0
        mv[t] = C[t, exit_min] - C[t, signal_min]
    for t in range(lookback + 1, D):
        if regime_filter != 0 and regime[t] != regime_filter:
            continue
        sd = np.std(rod[t - lookback:t])
        if sd <= 0:
            continue
        z = rod[t] / sd
        if abs(z) < z_min:
            continue
        side = 1 if z > 0 else -1
        sdm = np.std(mv[t - lookback:t])
        entry = C[t, signal_min]
        stop = entry - side * stop_mult * sdm
        mae = mfe = 0.0
        done = False
        for i in range(signal_min + 1, exit_min + 1):
            if side > 0:
                mfe = max(mfe, H[t, i] - entry)
                mae = max(mae, entry - L[t, i])
            else:
                mfe = max(mfe, entry - L[t, i])
                mae = max(mae, H[t, i] - entry)
            f, px, _r = _manage(side, entry, stop, 0.0, O[t, i], H[t, i], L[t, i])
            if f:
                n = _write(out, n, t, side, signal_min, i, entry, px, stop, mae, mfe)
                done = True
                break
        if not done:
            n = _write(out, n, t, side, signal_min, exit_min, entry, C[t, exit_min], stop, mae, mfe)
    return n
