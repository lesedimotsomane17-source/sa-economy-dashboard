"""
clean_unemployment.py
---------------------
Reads the BER Data Portal download of South Africa's quarterly labour
statistics (built from the Stats SA Quarterly Labour Force Survey, QLFS)
and keeps only the OFFICIAL unemployment rate.

Usage:
    python src/clean_unemployment.py data/raw/ber-labour-official-lu3.csv data/clean/unemployment_rate.csv

The raw file looks like this:
    Quarter,Official unemployment,LU3
    Q2 2026,33.6,43.8
    Q1 2026,32.7,43.7
    ...

Only the "Official unemployment" column is used. LU3 is a broader measure
(it adds people who want work but are not actively searching) and is ignored.

Output columns:
    date               first day of the quarter (YYYY-MM-DD)
    quarter            label such as "2026 Q2"
    unemployment_rate  official unemployment rate, in percent

The quarterly series starts in Q1 2008, when Stats SA introduced the QLFS.
"""

import re
import sys
from pathlib import Path

import pandas as pd


def parse_quarter(label):
    """Turn 'Q2 2026' into the first day of that quarter (2026-04-01)."""
    match = re.fullmatch(r"Q([1-4])\s+(\d{4})", label.strip())
    if not match:
        raise ValueError(f"Unexpected quarter label: {label!r}")
    quarter, year = int(match.group(1)), int(match.group(2))
    return pd.Timestamp(year=year, month=(quarter - 1) * 3 + 1, day=1)


def read_unemployment(csv_path):
    raw = pd.read_csv(csv_path)
    if "Official unemployment" not in raw.columns:
        raise ValueError("Column 'Official unemployment' not found. Is this the right file?")

    df = pd.DataFrame({
        "date": raw["Quarter"].map(parse_quarter),
        "unemployment_rate": pd.to_numeric(raw["Official unemployment"], errors="raise"),
    })
    df["quarter"] = df["date"].dt.year.astype(str) + " Q" + df["date"].dt.quarter.astype(str)
    return df.sort_values("date").reset_index(drop=True)


def check_data(df):
    assert not df.empty, "No rows were extracted."
    assert df["date"].is_unique, "Duplicate quarters found."
    expected = pd.date_range(df["date"].min(), df["date"].max(), freq="QS-JAN")
    missing = expected.difference(df["date"])
    assert len(missing) == 0, f"Missing quarters: {list(missing.strftime('%Y-%m'))}"
    assert df["unemployment_rate"].between(10, 45).all(), "Rate outside expected range."


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    csv_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])

    df = read_unemployment(csv_path)
    check_data(df)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df[["date", "quarter", "unemployment_rate"]].to_csv(out_path, index=False)

    print(f"Saved {len(df)} quarterly rows to {out_path}")
    print(f"Range: {df['quarter'].iloc[0]} to {df['quarter'].iloc[-1]}")
    print(df.tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
