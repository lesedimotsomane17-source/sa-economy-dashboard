"""
clean_cpi.py
------------
Reads the Stats SA "CPI history" PDF and extracts Table B2
(CPI headline year-on-year inflation rates) into a clean CSV.

Usage:
    python src/clean_cpi.py data/raw/CPIHistory.pdf data/clean/cpi_inflation.csv

Output columns:
    date          first day of the month (YYYY-MM-DD)
    inflation_yoy year-on-year CPI inflation, in percent
"""

import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

START_YEAR = 2000
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# A data row looks like:  2024  5,3  5,6  ...  4,4
# i.e. a 4-digit year followed by numbers that use a comma as the decimal.
ROW_PATTERN = re.compile(r"^\s*(\d{4})((?:\s+-?\d+,\d)+)\s*$")


def read_pdf_text(pdf_path):
    """Return all text from the PDF as one string."""
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def get_table_b2(text):
    """Keep only the part of the text that belongs to Table B2."""
    start = text.find("Table B2")
    if start == -1:
        raise ValueError("Could not find 'Table B2' in the PDF. Is this the right file?")
    return text[start:]


def to_number(value):
    """Turn '4,4' into 4.4 (South African decimal comma -> decimal point)."""
    return float(value.replace(",", "."))


def parse_rows(table_text):
    """Turn each matching line into (date, inflation) records."""
    records = []
    for line in table_text.splitlines():
        match = ROW_PATTERN.match(line)
        if not match:
            continue  # skips headers, footnotes and page breaks

        year = int(match.group(1))
        if year < START_YEAR:
            continue

        numbers = [to_number(n) for n in match.group(2).split()]

        # Complete years have 12 months + 1 yearly average (13 numbers).
        # The current year has only the months published so far.
        monthly = numbers[:12]
        for month_index, value in enumerate(monthly, start=1):
            records.append({
                "date": pd.Timestamp(year=year, month=month_index, day=1),
                "inflation_yoy": value,
            })
    return pd.DataFrame(records)


def check_data(df):
    """Basic sanity checks so bad data does not slip through quietly."""
    assert not df.empty, "No rows were extracted."
    assert df["date"].is_unique, "Duplicate months found."

    expected = pd.date_range(df["date"].min(), df["date"].max(), freq="MS")
    missing = expected.difference(df["date"])
    assert len(missing) == 0, f"Missing months: {list(missing.strftime('%Y-%m'))}"

    assert df["inflation_yoy"].between(-5, 20).all(), "Inflation value outside expected range."


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    pdf_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])

    text = read_pdf_text(pdf_path)
    df = parse_rows(get_table_b2(text))
    df = df.sort_values("date").reset_index(drop=True)
    check_data(df)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"Saved {len(df)} monthly rows to {out_path}")
    print(f"Range: {df['date'].min():%Y-%m} to {df['date'].max():%Y-%m}")
    print(df.tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
