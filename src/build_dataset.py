"""
build_dataset.py
----------------
Combines the cleaned indicator files into ONE monthly table that
Power BI can read. Add a new indicator here as each one is cleaned.

Usage:
    python src/build_dataset.py

Reads:
    data/clean/cpi_inflation.csv
    data/clean/repo_rate.csv
Writes:
    data/clean/economy_monthly.csv

Months where one indicator has no data (for example the repo rate before
December 2001, or CPI for months not yet published) are left blank.
"""

from pathlib import Path

import pandas as pd

CLEAN_DIR = Path("data/clean")

INDICATOR_FILES = [
    "cpi_inflation.csv",
    "repo_rate.csv",
]


def load_indicator(filename):
    df = pd.read_csv(CLEAN_DIR / filename, parse_dates=["date"])
    assert df["date"].is_unique, f"Duplicate months in {filename}"
    return df


def main():
    merged = None
    for filename in INDICATOR_FILES:
        df = load_indicator(filename)
        merged = df if merged is None else merged.merge(df, on="date", how="outer")

    merged = merged.sort_values("date").reset_index(drop=True)

    # Every month from the first to the last date should be present.
    expected = pd.date_range(merged["date"].min(), merged["date"].max(), freq="MS")
    assert len(expected.difference(merged["date"])) == 0, "Missing months in merged table."

    out_path = CLEAN_DIR / "economy_monthly.csv"
    merged.to_csv(out_path, index=False)

    print(f"Saved {len(merged)} monthly rows to {out_path}")
    print(f"Range: {merged['date'].min():%Y-%m} to {merged['date'].max():%Y-%m}")
    print(merged.isna().sum().to_string())
    print(merged.tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
