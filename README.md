# South African Economy Dashboard

A Power BI dashboard that tracks key South African economic indicators, supported by a Python data pipeline.

## About this project

This project pulls official South African economic data, cleans it with Python, and presents it in an interactive dashboard. It is built in stages, and this repo will grow as each stage is completed.
## Preview

![South African Economy Dashboard](images/dashboard-stage1.png)

## Stage 1 indicators

- Real GDP growth (year-on-year %)
- CPI inflation (year-on-year %)
- Unemployment rate
- Repo rate

## Data sources

- CPI inflation: Stats SA (monthly, from January 2000)
- Repo rate: South African Reserve Bank policy rate (monthly, from December 2001, when the SARB series begins)
- GDP growth: calculated from the SARB's seasonally adjusted real GDP at constant 2015 prices (quarterly, from Q4 2000)
- Unemployment: Stats SA Quarterly Labour Force Survey, via the BER Data Portal (quarterly, from Q1 2008, when the survey began)

Quarterly figures are repeated across the three months of their quarter so they line up with the monthly data.

## Tools

- Python (data collection and cleaning)
- Power BI (dashboard)

## Status

Stage 1 in progress: data pipeline complete for all four indicators. The dashboard currently shows inflation and the repo rate, with GDP growth and unemployment charts to follow.

## Author

Lesedi Motsomane

