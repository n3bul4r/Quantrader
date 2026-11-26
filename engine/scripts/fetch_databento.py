"""Download 1-minute futures bars from Databento (GLBX.MDP3) into data/real/<MICRO>.parquet.

    python scripts/fetch_databento.py --check          # cost estimate only (free call)
    python scripts/fetch_databento.py                  # download (refuses if cost > --max-cost)

Uses the REST API directly. Authentication is HTTP basic with the API key as username; in this
cloud environment the key is injected by the network proxy, so the script sends no key itself
(locally, set DATABENTO_API_KEY and it will be used). Full-size continuous contracts (volume roll)
are downloaded because they have a longer history and the same price moves as the micros traded.
Only each market's trading session (± 30 min) is kept, to keep files small.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "real"
BASE = "https://hist.databento.com/v0"
DATASET = "GLBX.MDP3"
SCHEMA = "ohlcv-1m"
# full-size continuous symbol -> micro file name (sets costs + session hours in the engine)
MARKETS = {"ES.v.0": "MES", "NQ.v.0": "MNQ", "RTY.v.0": "M2K", "CL.v.0": "MCL", "GC.v.0": "MGC", "6E.v.0": "M6E"}
KEEP = {"MES": ("09:00", "16:30"), "MNQ": ("09:00", "16:30"), "M2K": ("09:00", "16:30"),
        "MCL": ("08:30", "15:00"), "MGC": ("07:50", "14:00"), "M6E": ("07:50", "15:30")}


def session() -> requests.Session:
    s = requests.Session()
    key = os.environ.get("DATABENTO_API_KEY")
    if key and key != "proxy-injected":
        s.auth = (key, "")
    return s


def cost(s, symbol, start, end) -> float:
    r = s.get(f"{BASE}/metadata.get_cost", params={"dataset": DATASET, "symbols": symbol, "schema": SCHEMA,
                                                    "start": start, "end": end, "stype_in": "continuous"}, timeout=60)
    r.raise_for_status()
    return float(r.json())


def fetch_chunk(s, symbol, start, end) -> pd.DataFrame:
    params = {"dataset": DATASET, "symbols": symbol, "schema": SCHEMA, "start": start, "end": end,
              "stype_in": "continuous", "encoding": "csv", "pretty_px": "true", "pretty_ts": "true",
              "map_symbols": "true", "compression": "none"}
    with s.get(f"{BASE}/timeseries.get_range", params=params, timeout=600, stream=True) as r:
        r.raise_for_status()
        buf = io.BytesIO()
        for part in r.iter_content(chunk_size=1 << 20):
            buf.write(part)
    buf.seek(0)
    if buf.getbuffer().nbytes == 0:
        return pd.DataFrame()
    return pd.read_csv(buf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2013-01-01")
    ap.add_argument("--end", default=None, help="exclusive end date (default: yesterday)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--max-cost", type=float, default=100.0, help="refuse to download above this many USD")
    ap.add_argument("--only", nargs="*", default=None, help="subset of micro names, e.g. MES MNQ")
    a = ap.parse_args()
    end = a.end or str((pd.Timestamp.utcnow().normalize() - pd.Timedelta(days=1)).date())
    s = session()
    todo = {k: v for k, v in MARKETS.items() if not a.only or v in a.only}
    costs = {}
    for sym, micro in todo.items():
        costs[sym] = cost(s, sym, a.start, end)
        print(f"{sym:8s} -> {micro}: estimated ${costs[sym]:.2f}", flush=True)
    total = sum(costs.values())
    print(f"TOTAL estimated cost: ${total:.2f} (new accounts get $125 of free credit)", flush=True)
    if a.check:
        return
    if total > a.max_cost:
        sys.exit(f"refusing: ${total:.2f} > --max-cost ${a.max_cost:.2f}")
    OUT.mkdir(parents=True, exist_ok=True)
    years = pd.date_range(a.start, end, freq="YS").strftime("%Y-%m-%d").tolist() + [end]
    for sym, micro in todo.items():
        frames = []
        lo, hi = KEEP[micro]
        for y0, y1 in zip(years[:-1], years[1:]):
            df = fetch_chunk(s, sym, y0, y1)
            if df.empty:
                continue
            ts = pd.to_datetime(df["ts_event"], utc=True)
            df.index = pd.DatetimeIndex(ts).tz_convert("America/New_York")
            df = df.between_time(lo, hi)
            frames.append(df[["open", "high", "low", "close", "volume"] + (["symbol"] if "symbol" in df else [])])
            print(f"  {micro} {y0[:4]}: {len(df):,} session bars", flush=True)
        if not frames:
            print(f"  {micro}: no data", flush=True)
            continue
        out = pd.concat(frames)
        out = out[~out.index.duplicated(keep="last")]
        out.index = out.index.tz_convert("UTC")
        out = out.reset_index(names="ts_event")
        try:
            path = OUT / f"{micro}.parquet"
            out.to_parquet(path, index=False)
        except ImportError:            # no pyarrow installed: fall back to CSV (the engine reads both)
            path = OUT / f"{micro}.csv"
            out.to_csv(path, index=False)
        print(f"saved {path}: {len(out):,} rows, {out.ts_event.min()} → {out.ts_event.max()}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            sys.exit("Databento rejected the API key (401). Copy it again from https://databento.com/portal/keys "
                     "(no spaces), check that your account e-mail is verified, then:  "
                     "export DATABENTO_API_KEY=db-...  and re-run.")
        raise
