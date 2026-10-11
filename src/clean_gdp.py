"""
clean_gdp.py
------------
Reads the SARB download "GDP at market prices (constant, sa)" and turns the
quarterly GDP LEVELS into year-on-year GROWTH rates.

Usage:
    python src/clean_gdp.py data/raw/SDDSDetail.csv data/clean/gdp_growth.csv

The raw file looks like this:
    GDP at market prices (constant, sa)
    Gross domestic product at market prices
    Constant 2015 prices. Seasonally adjusted at annual rate
    Date,Value
    Q2/26,4754800
    Q1/26,4766238
    ...

Output columns:
    date            first day of the quarter (YYYY-MM-DD)
    quarter         label such as "2026 Q2"
    gdp_level       real GDP, R million, constant 2015 prices, seasonally adjusted
    gdp_growth_yoy  growth versus the same quarter a year earlier, in percent

Growth = (GDP this quarter / GDP same quarter last year - 1) x 100
"""

import re
import sys
from pathlib import Path

import pandas as pd

HEADER_LINES_TO_SKIP = 3  # the three description lines above "Date,Value"


def parse_quarter(label):
    """Turn 'Q2/26' into the first day of that quarter (2026-04-01)."""
    match = re.fullmatch(r"Q([1-4])/(\d{2})", label.strip())
    if not match:
        raise ValueError(f"Unexpected quarter label: {label!r}")
    quarter, yy = int(match.group(1)), int(match.group(2))
    year = 1900 + yy if yy > 50 else 2000 + yy
    return pd.Timestamp(year=year, month=(quarter - 1) * 3 + 1, day=1)


def read_gdp_levels(csv_path):
    raw = pd.read_csv(csv_path, skiprows=HEADER_LINES_TO_SKIP)
    raw.columns = ["label", "gdp_level"]
    raw["date"] = raw["label"].map(parse_quarter)
    raw["gdp_level"] = pd.to_numeric(raw["gdp_level"], errors="raise")
    return raw[["date", "gdp_level"]].sort_values("date").reset_index(drop=True)


def add_growth(df):
    """Add year-on-year growth (compares each quarter with 4 quarters earlier)."""
    df = df.copy()
    df["quarter"] = df["date"].dt.year.astype(str) + " Q" + df["date"].dt.quarter.astype(str)
    df["gdp_growth_yoy"] = (df["gdp_level"] / df["gdp_level"].shift(4) - 1) * 100
    df["gdp_growth_yoy"] = df["gdp_growth_yoy"].round(2)
    # The first four quarters have no year-earlier figure, so drop them.
    return df.dropna(subset=["gdp_growth_yoy"]).reset_index(drop=True)


def check_data(df):
    assert not df.empty, "No rows were produced."
    assert df["date"].is_unique, "Duplicate quarters found."
    expected = pd.date_range(df["date"].min(), df["date"].max(), freq="QS-JAN")
    missing = expected.difference(df["date"])
    assert len(missing) == 0, f"Missing quarters: {list(missing.strftime('%Y-%m'))}"
    assert df["gdp_growth_yoy"].between(-25, 25).all(), "Growth outside expected range."


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    csv_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])

    levels = read_gdp_levels(csv_path)
    # Make sure no quarter is missing BEFORE we start comparing with 4 quarters back.
    full = pd.date_range(levels["date"].min(), levels["date"].max(), freq="QS-JAN")
    assert len(full.difference(levels["date"])) == 0, "Missing quarters in the raw file."

    growth = add_growth(levels)
    check_data(growth)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    growth[["date", "quarter", "gdp_level", "gdp_growth_yoy"]].to_csv(out_path, index=False)

    print(f"Saved {len(growth)} quarterly rows to {out_path}")
    print(f"Range: {growth['quarter'].iloc[0]} to {growth['quarter'].iloc[-1]}")
    print(growth.tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
