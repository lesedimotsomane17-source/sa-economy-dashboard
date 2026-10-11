"""
build_dataset.py
----------------
Combines the cleaned indicator files into ONE monthly table that
Power BI can read. Add a new indicator here as each one is cleaned.

Usage:
    python src/build_dataset.py

Reads:
    data/clean/cpi_inflation.csv   (monthly)
    data/clean/repo_rate.csv       (monthly)
    data/clean/gdp_growth.csv      (quarterly)
    data/clean/unemployment_rate.csv (quarterly)
Writes:
    data/clean/economy_monthly.csv

Quarterly indicators are spread across the three months of their quarter
(for example Q2 growth is shown for April, May and June), so they line up
with the monthly indicators. This is a display choice, not new data.

Months where an indicator has no data (for example the repo rate before
December 2001, or CPI for months not yet published) are left blank.
"""

from pathlib import Path

import pandas as pd

CLEAN_DIR = Path("data/clean")

MONTHLY_FILES = [
    "cpi_inflation.csv",
    "repo_rate.csv",
]

# (file, column to keep)
QUARTERLY_FILES = [
    ("gdp_growth.csv", "gdp_growth_yoy"),
    ("unemployment_rate.csv", "unemployment_rate"),
]


def load_monthly(filename):
    df = pd.read_csv(CLEAN_DIR / filename, parse_dates=["date"])
    assert df["date"].is_unique, f"Duplicate months in {filename}"
    return df


def load_quarterly_as_monthly(filename, column):
    """Repeat each quarter's value for its three months."""
    df = pd.read_csv(CLEAN_DIR / filename, parse_dates=["date"])
    assert df["date"].is_unique, f"Duplicate quarters in {filename}"

    rows = []
    for _, row in df.iterrows():
        for offset in range(3):
            rows.append({
                "date": row["date"] + pd.DateOffset(months=offset),
                column: row[column],
            })
    return pd.DataFrame(rows)


def main():
    tables = [load_monthly(f) for f in MONTHLY_FILES]
    tables += [load_quarterly_as_monthly(f, col) for f, col in QUARTERLY_FILES]

    merged = tables[0]
    for table in tables[1:]:
        merged = merged.merge(table, on="date", how="outer")

    merged = merged.sort_values("date").reset_index(drop=True)

    # Every month from the first to the last date should be present.
    expected = pd.date_range(merged["date"].min(), merged["date"].max(), freq="MS")
    assert len(expected.difference(merged["date"])) == 0, "Missing months in merged table."

    out_path = CLEAN_DIR / "economy_monthly.csv"
    merged.to_csv(out_path, index=False)

    print(f"Saved {len(merged)} monthly rows to {out_path}")
    print(f"Range: {merged['date'].min():%Y-%m} to {merged['date'].max():%Y-%m}")
    print("Blank months per column:")
    print(merged.isna().sum().to_string())
    print(merged.tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
