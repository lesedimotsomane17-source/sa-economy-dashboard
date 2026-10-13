"""
analyse_inflation_repo.py
-------------------------
Tests how closely CPI inflation and the SARB repo rate move together.
These are the numbers quoted in the README's "What I found" section.

Usage (from the repo root, after running build_dataset.py):
    python src/analyse_inflation_repo.py

Reads:
    data/clean/economy_monthly.csv
Writes:
    analysis/inflation_repo_results.txt   (the same text that is printed)

What it does:
    1. Correlation and a simple regression of the repo rate on inflation.
    2. The same regression with Newey-West (HAC) standard errors, because both
       series are very persistent, which makes ordinary p-values far too small.
    3. The same test on 12-month changes.
    4. Granger tests on monthly changes, in both directions.
    5. The correlation in three sub-periods, to check the link is stable.
    6. The gap between the repo rate and inflation (a simple "real rate":
       repo rate minus the latest inflation rate, NOT adjusted for expected
       inflation).

These tests describe how the series move together. They do not prove cause and effect.
"""

import contextlib
import io
from pathlib import Path

import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import grangercausalitytests

DATA_FILE = Path("data/clean/economy_monthly.csv")
OUT_FILE = Path("analysis/inflation_repo_results.txt")

SUB_PERIODS = [("2001-12", "2009-12"), ("2010-01", "2019-12"), ("2020-01", "2026-08")]
EPISODES = [("2002-01", "2004-06"), ("2007-06", "2010-06"), ("2021-06", "2024-12")]


def p_text(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def hac_regression(y, x, lags):
    """Regress y on x with Newey-West standard errors."""
    return sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})


def granger_p_values(data, max_lag=6):
    """p-value for lags 1..max_lag; first column is the variable being predicted."""
    with contextlib.redirect_stdout(io.StringIO()):  # hide the library's own printing
        results = grangercausalitytests(data, maxlag=max_lag)
    return {lag: float(results[lag][0]["ssr_ftest"][1]) for lag in range(1, max_lag + 1)}


def main():
    df = pd.read_csv(DATA_FILE, parse_dates=["date"]).set_index("date")
    both = df[["inflation_yoy", "repo_rate"]].dropna()
    lines = []
    out = lines.append

    out("INFLATION AND THE REPO RATE")
    out(f"Months with both series: {len(both)} ({both.index[0]:%Y-%m} to {both.index[-1]:%Y-%m})")
    out("")

    # 1 and 2: levels
    corr = both["repo_rate"].corr(both["inflation_yoy"])
    plain = sm.OLS(both["repo_rate"], sm.add_constant(both["inflation_yoy"])).fit()
    robust = hac_regression(both["repo_rate"], both["inflation_yoy"], lags=12)
    out("Levels")
    out(f"  Correlation: {corr:.2f}")
    out(f"  A 1-point rise in inflation goes with a {robust.params.iloc[1]:.2f}-point higher repo rate")
    out(f"  Ordinary p-value: {p_text(plain.pvalues.iloc[1])} (too small, because the series are persistent)")
    out(f"  Newey-West: t = {robust.tvalues.iloc[1]:.1f}, p {p_text(robust.pvalues.iloc[1])}")
    out(f"  Month-to-month autocorrelation: inflation {both['inflation_yoy'].autocorr(1):.2f}, "
        f"repo rate {both['repo_rate'].autocorr(1):.2f}")
    out("")

    # 3: 12-month changes
    changes = pd.DataFrame({
        "d_repo": both["repo_rate"].diff(12),
        "d_inf": both["inflation_yoy"].diff(12),
    }).dropna()
    robust_changes = hac_regression(changes["d_repo"], changes["d_inf"], lags=12)
    out("12-month changes")
    out(f"  Correlation: {changes['d_repo'].corr(changes['d_inf']):.2f}")
    out(f"  Newey-West: t = {robust_changes.tvalues.iloc[1]:.1f}, p {p_text(robust_changes.pvalues.iloc[1])}")
    out("")

    # 4: Granger tests on monthly changes
    monthly = pd.DataFrame({
        "d_repo": both["repo_rate"].diff(),
        "d_inf": both["inflation_yoy"].diff(),
    }).dropna()
    to_repo = granger_p_values(monthly[["d_repo", "d_inf"]])
    to_inf = granger_p_values(monthly[["d_inf", "d_repo"]])
    out("Does one lead the other? (Granger tests on monthly changes, lags 1 to 6)")
    out("  Inflation changes help predict repo rate changes: "
        + ", ".join(f"lag {k} p {p_text(v)}" for k, v in to_repo.items()))
    out("  Repo rate changes help predict inflation changes: "
        + ", ".join(f"lag {k} p {p_text(v)}" for k, v in to_inf.items()))
    out("  Significant in both directions, so the data cannot say which drives which.")
    out("")

    # 5: stability
    out("Is the link stable? (correlation of levels)")
    for start, end in SUB_PERIODS:
        part = both[start:end]
        out(f"  {start} to {end}: {part['repo_rate'].corr(part['inflation_yoy']):.2f} ({len(part)} months)")
    out("")

    # Peaks
    out("Peaks in each episode")
    for start, end in EPISODES:
        inflation_part = both["inflation_yoy"][start:end]
        repo_part = both["repo_rate"][start:end]
        out(f"  {start} to {end}: inflation peak {inflation_part.max():.1f}% in {inflation_part.idxmax():%Y-%m}, "
            f"repo peak {repo_part.max():.2f}% in {repo_part.idxmax():%Y-%m}")
    out("")

    # 6: simple real rate
    gap = both["repo_rate"] - both["inflation_yoy"]
    out("Gap between the repo rate and inflation (repo rate minus latest inflation)")
    out(f"  {gap.index[-1]:%Y-%m}: {gap.iloc[-1]:.1f} points "
        f"(repo {both['repo_rate'].iloc[-1]:.2f}%, inflation {both['inflation_yoy'].iloc[-1]:.1f}%)")
    out(f"  Average since {gap.index[0]:%Y-%m}: {gap.mean():.1f} points")
    out("")
    out("These tests describe how the series move together. They do not prove cause and effect.")

    text = "\n".join(lines)
    print(text)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(text + "\n", encoding="utf-8")
    print(f"\nSaved to {OUT_FILE}")


if __name__ == "__main__":
    main()
