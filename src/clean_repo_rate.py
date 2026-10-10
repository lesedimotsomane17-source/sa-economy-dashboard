"""
clean_repo_rate.py
------------------
Reads the SARB "policy rate" history PDF (daily values, newest first)
and turns it into a clean monthly CSV that lines up with the CPI data.

Usage:
    python src/clean_repo_rate.py data/raw/HistoricalRateDetail.pdf data/clean/repo_rate.csv

Optional: stop at a given month, e.g. to match the last CPI month:
    python src/clean_repo_rate.py data/raw/HistoricalRateDetail.pdf data/clean/repo_rate.csv 2026-08

Output columns:
    date       first day of the month (YYYY-MM-DD)
    repo_rate  the repo rate in force at the end of that month, in percent
"""

import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

# A data row looks like:  2026-09-25   7.25
ROW_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(-?\d+(?:\.\d+)?)$")


def read_daily_rates(pdf_path):
    """Read every 'date value' line from the PDF into a daily table."""
    records = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for line in (page.extract_text() or "").splitlines():
                match = ROW_PATTERN.match(line.strip())
                if match:  # skips the 'Date Value' header on each page
                    records.append((match.group(1), float(match.group(2))))

    if not records:
        raise ValueError("No data rows found. Is this the SARB policy rate PDF?")

    daily = pd.DataFrame(records, columns=["date", "repo_rate"])
    daily["date"] = pd.to_datetime(daily["date"])
    return daily.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def to_monthly(daily):
    """Take the last rate of each month = the rate in force at month end."""
    month_start = daily["date"].dt.to_period("M").dt.to_timestamp()
    monthly = daily.groupby(month_start)["repo_rate"].last().reset_index()
    monthly.columns = ["date", "repo_rate"]
    return monthly


def check_data(df):
    """Basic sanity checks so bad data does not slip through quietly."""
    assert not df.empty, "No rows were extracted."
    assert df["date"].is_unique, "Duplicate months found."

    expected = pd.date_range(df["date"].min(), df["date"].max(), freq="MS")
    missing = expected.difference(df["date"])
    assert len(missing) == 0, f"Missing months: {list(missing.strftime('%Y-%m'))}"

    assert df["repo_rate"].between(1, 20).all(), "Repo rate outside expected range."


def main():
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(1)

    pdf_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])

    monthly = to_monthly(read_daily_rates(pdf_path))

    if len(sys.argv) == 4:  # optional cut-off month, e.g. 2026-08
        cutoff = pd.Timestamp(sys.argv[3] + "-01")
        monthly = monthly[monthly["date"] <= cutoff]

    check_data(monthly)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(out_path, index=False)

    print(f"Saved {len(monthly)} monthly rows to {out_path}")
    print(f"Range: {monthly['date'].min():%Y-%m} to {monthly['date'].max():%Y-%m}")
    print(monthly.tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
