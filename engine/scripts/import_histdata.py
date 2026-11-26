"""Convert HistData.com free 1-minute files (as downloaded by hand) into data/real/<MICRO>.parquet.

HistData "Generic ASCII" 1-minute bars: lines like  20230103 093000;3853.250;3855.000;3851.750;3854.500;0
Timestamps are EST *without* daylight saving (fixed UTC−5). Volume is always 0 (CFD quotes), so the
engine's VWAP becomes a time-weighted average — fine for these strategies.

    python scripts/import_histdata.py <folder with the downloaded .zip/.csv files>

Files are matched by instrument name in the file name (e.g. HISTDATA_COM_ASCII_SPXUSD_M12023.zip).
Mapping: SPXUSD → MES, NSXUSD → MNQ, WTIUSD → MCL, XAUUSD → MGC, EURUSD → M6E.
"""
from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "real"
MAP = {"SPXUSD": "MES", "NSXUSD": "MNQ", "WTIUSD": "MCL", "XAUUSD": "MGC", "EURUSD": "M6E"}


def parse_ascii(text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text), sep=";", header=None, names=["dt", "open", "high", "low", "close", "volume"],
                     dtype={"dt": str})
    df = df[df["dt"].str.strip().str.match(r"^\d{8} \d{6}$", na=False)]      # skip status/copyright lines
    ts = pd.to_datetime(df["dt"].str.strip(), format="%Y%m%d %H%M%S")
    ts = ts.dt.tz_localize("Etc/GMT+5")          # fixed EST (POSIX sign convention: GMT+5 == UTC−5)
    out = df[["open", "high", "low", "close", "volume"]].astype(float)
    out.insert(0, "ts_event", ts.dt.tz_convert("UTC"))
    return out


def read_any(path: Path) -> list[pd.DataFrame]:
    frames = []
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.lower().endswith(".csv"):            # the .txt in each zip is a status report
                    frames.append(parse_ascii(z.read(name).decode("utf-8", errors="ignore")))
    elif path.suffix.lower() in (".csv", ".txt"):
        frames.append(parse_ascii(path.read_text(errors="ignore")))
    return frames


def main(folder: str):
    src = Path(folder)
    found: dict[str, list[pd.DataFrame]] = {}
    for f in sorted(src.rglob("*")):
        m = re.search("|".join(MAP), f.name.upper())
        if not m or not f.is_file():
            continue
        found.setdefault(MAP[m.group(0)], []).extend(read_any(f))
    if not found:
        sys.exit(f"no HistData files for {', '.join(MAP)} found in {src}")
    OUT.mkdir(parents=True, exist_ok=True)
    for micro, frames in found.items():
        df = pd.concat(frames).drop_duplicates("ts_event").sort_values("ts_event")
        path = OUT / f"{micro}.parquet"
        try:
            df.to_parquet(path, index=False)
        except ImportError:
            path = OUT / f"{micro}.csv"
            df.to_csv(path, index=False)
        print(f"{micro}: {len(df):,} bars  {df.ts_event.min()} → {df.ts_event.max()}  → {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
