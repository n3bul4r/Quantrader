REAL DATA FOR THE STRATEGY TEST — three ways to get it
=======================================================

A) HistData.com (free, manual download, no account)
   1. Open https://www.histdata.com/download-free-forex-data/?/ascii/1-minute-bar-quotes
   2. For each instrument: SPXUSD (S&P 500), NSXUSD (Nasdaq-100), WTIUSD (crude), XAUUSD (gold), EURUSD
      download the yearly files 2018 ... 2025 plus the monthly files of 2026 ("Generic ASCII", 1-minute).
      Start with SPXUSD and NSXUSD if you want results faster.
   3. Put all the .zip files in one folder, then:
        cd engine && python scripts/import_histdata.py <that folder>
      (or upload the zips to the Claude session and ask Claude to run it)

B) Databento ($125 free credit for new accounts)
        cd engine && export DATABENTO_API_KEY=db-...  &&  python scripts/fetch_databento.py --check && python scripts/fetch_databento.py

C) Any 1-minute OHLCV CSV/Parquet named MES / MNQ / M2K / MCL / MGC / M6E, placed in data/real/

Then run the full test + plan search:
        cd engine && python scripts/find_4k_plan.py --data-dir ../data/real
See docs/PLAN_4K.md, step 0.
