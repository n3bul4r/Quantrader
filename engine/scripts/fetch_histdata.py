"""Download HistData.com free 1-minute bars (Generic ASCII), politely and resumably.

    python scripts/fetch_histdata.py [--start 2018] [--pairs SPXUSD NSXUSD WTIUSD XAUUSD EURUSD]

One request at a time with a pause between files; already-downloaded files are skipped.
Output: data/raw/histdata/*.zip  → then run scripts/import_histdata.py data/raw/histdata
"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pandas as pd
from histdata import download_hist_data as dl
from histdata.api import Platform as P
from histdata.api import TimeFrame as TF

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "histdata"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2018)
    ap.add_argument("--pairs", nargs="*", default=["SPXUSD", "NSXUSD", "WTIUSD", "XAUUSD", "EURUSD"])
    ap.add_argument("--pause", type=float, default=3.0)
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    now = pd.Timestamp.today()
    jobs = []
    for pair in a.pairs:
        for y in range(a.start, now.year):
            jobs.append((pair, str(y), None))
        for m in range(1, now.month + 1):          # current year is published month by month
            jobs.append((pair, str(now.year), str(m)))
    cwd = os.getcwd()
    os.chdir(RAW)
    try:
        for pair, y, m in jobs:
            name = f"DAT_ASCII_{pair}_M1_{y}{'' if m is None else f'{int(m):02d}'}.zip"
            if Path(name).exists() and Path(name).stat().st_size > 1000:
                continue
            for attempt in range(3):
                try:
                    dl(year=y, month=m, pair=pair.lower(), platform=P.GENERIC_ASCII, time_frame=TF.ONE_MINUTE)
                    print(f"ok   {name}", flush=True)
                    break
                except Exception as e:  # missing month, transient error
                    print(f"miss {name}: {type(e).__name__} {str(e)[:80]}", flush=True)
                    time.sleep(a.pause * (attempt + 2))
            time.sleep(a.pause)
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    main()
